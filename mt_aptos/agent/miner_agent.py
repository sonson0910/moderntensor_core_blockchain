# File: sdk/agent/miner_agent.py
# Logic cho Miner để tự động lấy kết quả đồng thuận và cập nhật trạng thái on-chain.

import asyncio
import logging
import time
import httpx
import binascii  # <<<--- Import binascii
import json  # <<<--- Thêm import json
import os  # <<<--- Thêm import os
from pathlib import Path  # <<<--- Thêm Path
from typing import Optional, Dict, Tuple, List, Any
import hashlib

# Import từ SDK
from mt_aptos.config.settings import Settings
from mt_aptos.core.datatypes import MinerConsensusResult, CycleConsensusResults

# Import lớp Datum và các công thức cần thiết
from mt_aptos.metagraph.metagraph_datum import MinerData  # <<<--- Updated to MinerData
from mt_aptos.metagraph.hash.hash_datum import hash_data
from mt_aptos.metagraph.hash.verify_hash import verify_hash

# Import Aptos SDK
from mt_aptos.account import Account
from mt_aptos.async_client import RestClient
from mt_aptos.transactions import EntryFunction, TransactionArgument, TransactionPayload

# Import config và utilities
from mt_aptos.config.settings import settings
from mt_aptos.keymanager.decryption_utils import decode_hotkey_account

# Lấy logger đã cấu hình
logger = logging.getLogger(__name__)


class MinerAgent:
    """
    Agent chạy song song với Miner Server, chịu trách nhiệm:
    1. Fetch kết quả đồng thuận từ Validator API.
    2. Tương tác với Aptos smart contract để cập nhật trạng thái.
    3. Tính toán trạng thái mới (trust, reward, performance...).
    4. Gửi giao dịch self-update lên Aptos để cập nhật dữ liệu.
    """

    def __init__(
        self,
        miner_uid_hex: str,  # UID hex của miner này
        config: Optional[Dict[str, Any]] = None,
        miner_account: Optional[Account] = None,  # Aptos Account object
        aptos_node_url: Optional[str] = None,
        contract_address: Optional[str] = None,
    ):
        """
        Khởi tạo Miner Agent cho Aptos.

        Args:
            miner_uid_hex: UID hex của miner này (dạng string).
            config: Dictionary chứa các tham số cấu hình.
            miner_account: Aptos Account object để ký giao dịch.
            aptos_node_url: URL của Aptos node.
            contract_address: Địa chỉ smart contract ModernTensor trên Aptos.

        Raises:
            ValueError: Nếu miner_uid_hex không hợp lệ.
            RuntimeError: Nếu không thể khởi tạo Aptos client hoặc config.
        """
        if not miner_uid_hex or not isinstance(miner_uid_hex, str):
            raise ValueError("MinerAgent requires a valid miner_uid_hex (string).")

        self.miner_uid_hex: str = miner_uid_hex
        try:
            # Chuyển đổi và lưu trữ UID dạng bytes
            self.miner_uid_bytes: bytes = binascii.unhexlify(miner_uid_hex)
        except (binascii.Error, TypeError) as e:
            raise ValueError(
                f"Invalid miner_uid_hex format: {miner_uid_hex}. Error: {e}"
            ) from e

        self.config = config or {}
        self.miner_account = miner_account
        uid_prefix = f"[Init:{self.miner_uid_hex[:8]}...]"

        # --- Khởi tạo Aptos Client và Config ---
        logger.debug(f"{uid_prefix} Initializing Aptos client...")
        try:
            self.aptos_node_url = aptos_node_url or settings.APTOS_NODE_URL
            self.contract_address = contract_address or settings.APTOS_CONTRACT_ADDRESS
            
            if not self.aptos_node_url:
                raise RuntimeError("APTOS_NODE_URL not configured")
            if not self.contract_address:
                raise RuntimeError("APTOS_CONTRACT_ADDRESS not configured")
                
            self.client = RestClient(self.aptos_node_url)
            logger.debug(f"{uid_prefix} Aptos client initialized (Node: {self.aptos_node_url})")
            logger.debug(f"{uid_prefix} Contract address: {self.contract_address}")
        except Exception as e:
            logger.exception(f"{uid_prefix} Failed to initialize Aptos client.")
            raise RuntimeError(f"Failed to initialize Aptos client: {e}") from e

        # HTTP client cho API calls
        logger.debug(f"{uid_prefix} Initializing HTTP client...")
        self.http_client = httpx.AsyncClient(timeout=15.0)

        # State theo dõi
        self.last_processed_cycle = -1
        self.last_known_performance = 0.0

        # Thiết lập thư mục state
        state_dir_path = self.config.get("AGENT_STATE_DIR", ".miner_agent_state")
        self.state_dir = Path(state_dir_path)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.state_dir / f"history_{self.miner_uid_hex}.json"
        logger.debug(f"{uid_prefix} State directory: {self.state_dir}")
        logger.debug(f"{uid_prefix} History file: {self.history_file}")

        # Final init log
        logger.info(f"{uid_prefix} MinerAgent initialized.")
        logger.info(f"{uid_prefix} Miner UID: {self.miner_uid_hex}")
        logger.info(f"{uid_prefix} Contract Address: {self.contract_address}")
        if self.miner_account:
            logger.info(f"{uid_prefix} Miner Account: {self.miner_account.address()}")

    def _load_local_history(self) -> List[float]:
        """Tải danh sách lịch sử hiệu suất từ file cục bộ."""
        uid_prefix = f"[LoadHistory:{self.miner_uid_hex[:8]}...]"
        
        if self.history_file.exists():
            try:
                with open(self.history_file, "r") as f:
                    history = json.load(f)
                    if isinstance(history, list) and all(
                        isinstance(x, (int, float)) for x in history
                    ):
                        logger.debug(
                            f"{uid_prefix} Loaded {len(history)} performance scores from {self.history_file}"
                        )
                        return history
                    else:
                        logger.warning(
                            f"{uid_prefix} Invalid data format in {self.history_file}. Resetting history."
                        )
            except (json.JSONDecodeError, OSError) as e:
                logger.error(
                    f"{uid_prefix} Error reading history file {self.history_file}: {e}. Resetting history."
                )
        else:
            logger.debug(
                f"{uid_prefix} History file {self.history_file} not found. Starting new history."
            )
        return []

    def _save_local_history(self, history: List[float]):
        """Lưu danh sách lịch sử hiệu suất vào file cục bộ."""
        uid_prefix = f"[SaveHistory:{self.miner_uid_hex[:8]}...]"
        try:
            with open(self.history_file, "w") as f:
                json.dump(history, f)
            logger.debug(f"{uid_prefix} Saved {len(history)} performance scores to {self.history_file}")
        except OSError as e:
            logger.error(f"{uid_prefix} Failed to save history to {self.history_file}: {e}")

    async def fetch_consensus_result(
        self, cycle_num: int, validator_api_url: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch kết quả đồng thuận từ Validator API cho cycle cụ thể.

        Args:
            cycle_num: Số cycle muốn fetch.
            validator_api_url: URL API của validator.

        Returns:
            Dictionary chứa consensus result, hoặc None nếu lỗi.
        """
        uid_prefix = f"[FetchConsensus:{self.miner_uid_hex[:8]}...]"
        url = f"{validator_api_url.rstrip('/')}/consensus/results/{cycle_num}"
        
        try:
            logger.debug(f"{uid_prefix} Fetching consensus result from: {url}")
            response = await self.http_client.get(url)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"{uid_prefix} Successfully fetched consensus result for cycle {cycle_num}")
            return result
            
        except httpx.RequestError as e:
            logger.error(f"{uid_prefix} Network error fetching consensus result: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logger.warning(f"{uid_prefix} HTTP error {e.response.status_code} fetching consensus result")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"{uid_prefix} Invalid JSON in consensus result: {e}")
            return None

    async def get_miner_data_from_chain(self) -> Optional[Dict[str, Any]]:
        """
        Lấy dữ liệu miner hiện tại từ Aptos blockchain.

        Returns:
            Dictionary chứa miner data, hoặc None nếu không tìm thấy.
        """
        uid_prefix = f"[GetMinerData:{self.miner_uid_hex[:8]}...]"
        
        try:
            logger.debug(f"{uid_prefix} Fetching miner data from blockchain...")
            
            # Call view function để lấy miner data
            result = await self.client.view(
                f"{self.contract_address}::moderntensor::get_miner_info",
                [],
                [self.miner_uid_hex]
            )
            
            if result:
                logger.info(f"{uid_prefix} Successfully fetched miner data from blockchain")
                return result
            else:
                logger.warning(f"{uid_prefix} Miner not found on blockchain")
                return None
                
        except Exception as e:
            logger.exception(f"{uid_prefix} Failed to fetch miner data from blockchain: {e}")
            return None

    def calculate_new_performance(
        self,
        old_performance: float,
        consensus_result: Dict[str, Any],
        current_cycle: int,
    ) -> float:
        """
        Tính toán performance mới dựa trên kết quả đồng thuận.

        Args:
            old_performance: Performance hiện tại.
            consensus_result: Kết quả đồng thuận từ validator.
            current_cycle: Cycle hiện tại.

        Returns:
            Performance mới đã tính toán.
        """
        uid_prefix = f"[CalcPerf:{self.miner_uid_hex[:8]}...]"
        
        try:
            # Extract score từ consensus result
            score = consensus_result.get("score", 0.0)
            if not isinstance(score, (int, float)):
                score = 0.0
                
            # Simple exponential moving average
            alpha = 0.1  # Smoothing factor
            new_performance = alpha * score + (1 - alpha) * old_performance
            
            logger.debug(f"{uid_prefix} Performance update: {old_performance:.4f} -> {new_performance:.4f} (score: {score:.4f})")
            
            # Clamp giá trị trong khoảng [0, 1]
            new_performance = max(0.0, min(1.0, new_performance))
            
            return new_performance
            
        except Exception as e:
            logger.warning(f"{uid_prefix} Error calculating new performance: {e}. Using old value.")
            return old_performance

    async def update_miner_on_chain(
        self,
        new_performance: float,
        cycle_num: int,
    ) -> Optional[str]:
        """
        Gửi giao dịch cập nhật miner data lên Aptos blockchain.

        Args:
            new_performance: Performance mới.
            cycle_num: Cycle number.

        Returns:
            Transaction hash nếu thành công, None nếu lỗi.
        """
        uid_prefix = f"[UpdateChain:{self.miner_uid_hex[:8]}...]"
        
        if not self.miner_account:
            logger.error(f"{uid_prefix} No miner account available for transaction signing")
            return None
            
        try:
            logger.debug(f"{uid_prefix} Preparing transaction to update miner data...")
            
            # Tạo entry function cho update miner
            payload = EntryFunction.from_str(
                f"{self.contract_address}::moderntensor::update_miner",
                [],
                [
                    TransactionArgument(self.miner_uid_hex, "string"),
                    TransactionArgument(int(new_performance * 10000), "u64"),  # Convert to fixed point
                    TransactionArgument(cycle_num, "u64"),
                    TransactionArgument(int(time.time()), "u64"),  # timestamp
                ]
            )
            
            # Submit transaction
            transaction_payload = TransactionPayload(payload)
            signed_transaction = await self.client.create_single_signer_transaction(
                self.miner_account, transaction_payload
            )
            
            # Submit and wait
            tx_hash = await self.client.submit_transaction(signed_transaction)
            await self.client.wait_for_transaction(tx_hash)
            
            logger.info(f"{uid_prefix} Successfully updated miner data on chain. Tx: {tx_hash}")
            return tx_hash
            
        except Exception as e:
            logger.exception(f"{uid_prefix} Failed to update miner data on chain: {e}")
            return None

    async def run(self, validator_api_url: str, check_interval_seconds: int = 60):
        """
        Chạy agent loop chính.

        Args:
            validator_api_url: URL API của validator để fetch consensus results.
            check_interval_seconds: Khoảng thời gian giữa các lần check (giây).
        """
        uid_prefix = f"[Run:{self.miner_uid_hex[:8]}...]"
        logger.info(f"{uid_prefix} Starting MinerAgent main loop...")
        logger.info(f"{uid_prefix} Validator API: {validator_api_url}")
        logger.info(f"{uid_prefix} Check interval: {check_interval_seconds}s")
        
        while True:
            try:
                # Fetch dữ liệu miner hiện tại từ blockchain
                miner_data = await self.get_miner_data_from_chain()
                if not miner_data:
                    logger.warning(f"{uid_prefix} Could not fetch miner data. Retrying in {check_interval_seconds}s...")
                    await asyncio.sleep(check_interval_seconds)
                    continue
                
                current_cycle = miner_data.get("current_cycle", 0)
                current_performance = miner_data.get("last_performance", 0.0)
                
                # Check nếu có cycle mới để xử lý
                if current_cycle > self.last_processed_cycle:
                    logger.info(f"{uid_prefix} Processing new cycle: {current_cycle}")
                    
                    # Fetch consensus result cho cycle này
                    consensus_result = await self.fetch_consensus_result(
                        current_cycle, validator_api_url
                    )
                    
                    if consensus_result:
                        # Tính toán performance mới
                        new_performance = self.calculate_new_performance(
                            current_performance, consensus_result, current_cycle
                        )
                        
                        # Update performance history
                        history = self._load_local_history()
                        history.append(new_performance)
                        
                        # Giữ chỉ 100 records gần nhất
                        if len(history) > 100:
                            history = history[-100:]
                        
                        self._save_local_history(history)
                        
                        # Update lên blockchain
                        tx_hash = await self.update_miner_on_chain(
                            new_performance, current_cycle
                        )
                        
                        if tx_hash:
                            self.last_processed_cycle = current_cycle
                            self.last_known_performance = new_performance
                            logger.info(f"{uid_prefix} Cycle {current_cycle} processed successfully")
                        else:
                            logger.error(f"{uid_prefix} Failed to update blockchain for cycle {current_cycle}")
                    else:
                        logger.warning(f"{uid_prefix} No consensus result available for cycle {current_cycle}")
                
                else:
                    logger.debug(f"{uid_prefix} No new cycles to process (current: {current_cycle}, last: {self.last_processed_cycle})")
                
            except Exception as e:
                logger.exception(f"{uid_prefix} Error in main loop: {e}")
            
            # Wait before next iteration
            await asyncio.sleep(check_interval_seconds)

    async def close(self):
        """Đóng các resources và cleanup."""
        uid_prefix = f"[Close:{self.miner_uid_hex[:8]}...]"
        logger.info(f"{uid_prefix} Shutting down MinerAgent...")
        
        try:
            await self.http_client.aclose()
            logger.debug(f"{uid_prefix} HTTP client closed.")
        except Exception as e:
            logger.warning(f"{uid_prefix} Error closing HTTP client: {e}")
        
        logger.info(f"{uid_prefix} MinerAgent shutdown complete.")
