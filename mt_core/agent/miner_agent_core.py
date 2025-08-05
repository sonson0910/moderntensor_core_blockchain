# File: mt_core/agent/miner_agent_core.py
# Core Blockchain compatible Miner Agent using Web3 instead of Aptos SDK

import asyncio
import logging
import time
import httpx
import json
import os
from pathlib import Path
from typing import Optional, Dict, Tuple, List, Any
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

# Import từ SDK
from mt_core.config.settings import settings

# Import utilities
from mt_core.keymanager.wallet_utils import WalletUtils

logger = logging.getLogger(__name__)

# === SLOT SYNCHRONIZATION CONSTANTS ===
# Must match validator SlotCoordinator timing
EPOCH_START = int(time.time()) - 3600  # 1 hour before current time (same as validator)
SLOT_DURATION_MINUTES = 3.5  # Must match validator slot_config
SLOT_DURATION_SECONDS = SLOT_DURATION_MINUTES * 60


class CoreMinerAgent:
    """
    Core Blockchain compatible Miner Agent
    Manages miner performance tracking and blockchain interactions using Web3
    Now includes slot synchronization with validator consensus timing
    """

    def __init__(
        self,
        miner_uid_hex: str,
        config: Dict[str, Any],
        miner_account=None,
        core_node_url: str = None,
        contract_address: str = None,
        contract_abi: List = None,
        wallet_name: str = None,
        coldkey_name: str = None,
        hotkey_name: str = None,
    ):
        """
        Initialize Core Miner Agent

        Args:
            miner_uid_hex: Miner UID in hex format
            config: Configuration dictionary
            miner_account: Core blockchain account (Web3 account)
            core_node_url: Core blockchain RPC URL
            contract_address: Smart contract address
            contract_abi: Contract ABI for Web3 interactions
            wallet_name: HD wallet name (optional)
            coldkey_name: Coldkey name (optional)
            hotkey_name: Hotkey name (optional)
        """
        self.miner_uid_hex = miner_uid_hex
        self.config = config
        self.core_node_url = core_node_url or "https://rpc.test.btcs.network"
        self.contract_address = contract_address
        self.contract_abi = contract_abi

        # Performance tracking
        self.last_processed_cycle = 0
        self.last_known_performance = 0.5  # Default 50%

        # === SLOT SYNCHRONIZATION ===
        self.last_processed_slot = -1
        self.slot_sync_enabled = True

        # History file for persistence
        self.history_file = Path(f"miner_performance_{self.miner_uid_hex[:8]}.json")

        uid_prefix = f"[Init:{self.miner_uid_hex[:8]}...]"

        # --- Load miner account ---
        if miner_account:
            self.miner_account = miner_account
            logger.info(
                f"{uid_prefix} Using provided miner account: {self.miner_account.address}"
            )
        elif wallet_name and coldkey_name and hotkey_name:
            logger.debug(f"{uid_prefix} Loading miner account from HD wallet...")
            try:
                utils = WalletUtils()
                self.miner_account = utils.quick_load_account(
                    wallet_name, coldkey_name, hotkey_name
                )
                if self.miner_account:
                    logger.info(
                        f"{uid_prefix} Loaded miner account from HD wallet: {wallet_name}.{coldkey_name}.{hotkey_name}"
                    )
                    logger.info(
                        f"{uid_prefix} Miner account address: {self.miner_account.address}"
                    )
                else:
                    raise RuntimeError("Failed to load miner account from HD wallet")
            except Exception as e:
                logger.exception(
                    f"{uid_prefix} Failed to load miner account from HD wallet"
                )
                raise RuntimeError(
                    f"Failed to load miner account from HD wallet: {e}"
                ) from e
        else:
            logger.warning(
                f"{uid_prefix} No miner account provided - using simulation mode"
            )

        # --- Initialize Web3 client ---
        try:
            self.web3 = Web3(Web3.HTTPProvider(self.core_node_url))
            self.web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

            if self.web3.is_connected():
                logger.info(
                    f"{uid_prefix} Connected to Core blockchain: {self.core_node_url}"
                )
                logger.info(f"{uid_prefix} Current block: {self.web3.eth.block_number}")

                # Initialize contract if ABI provided
                if self.contract_address and self.contract_abi:
                    self.contract = self.web3.eth.contract(
                        address=self.contract_address, abi=self.contract_abi
                    )
                    logger.info(
                        f"{uid_prefix} Contract initialized: {self.contract_address}"
                    )
                else:
                    self.contract = None
                    logger.warning(
                        f"{uid_prefix} No contract ABI provided - using simulation mode"
                    )
            else:
                logger.warning(f"{uid_prefix} Failed to connect to Core blockchain")
                self.contract = None
        except Exception as e:
            logger.warning(f"{uid_prefix} Web3 initialization failed: {e}")
            self.contract = None

        # --- Load performance history ---
        self._load_history()

        logger.info(f"{uid_prefix} Core Miner Agent initialized successfully")
        logger.info(
            f"{uid_prefix} Slot synchronization: {'ENABLED' if self.slot_sync_enabled else 'DISABLED'}"
        )

    def _load_history(self):
        """Load performance history from file"""
        uid_prefix = f"[LoadHist:{self.miner_uid_hex[:8]}...]"
        try:
            if self.history_file.exists():
                with open(self.history_file, "r") as f:
                    history = json.load(f)
                    if history:
                        # Get most recent performance
                        latest = max(history, key=lambda x: x.get("timestamp", 0))
                        self.last_known_performance = latest.get("performance", 0.5)
                        self.last_processed_cycle = latest.get("cycle", 0)
                        logger.debug(
                            f"{uid_prefix} Loaded {len(history)} performance records"
                        )
                        logger.debug(
                            f"{uid_prefix} Last performance: {self.last_known_performance:.3f}"
                        )
        except Exception as e:
            logger.warning(f"{uid_prefix} Could not load history: {e}")

    def _save_history(self, slot_num: int, performance: float):
        """Save performance history to file"""
        uid_prefix = f"[SaveHist:{self.miner_uid_hex[:8]}...]"
        try:
            history = []
            if self.history_file.exists():
                with open(self.history_file, "r") as f:
                    history = json.load(f)

            # Add new record
            history.append(
                {
                    "slot": slot_num,
                    "performance": performance,
                    "timestamp": int(time.time()),
                }
            )

            # Keep only last 100 records
            history = history[-100:]

            with open(self.history_file, "w") as f:
                json.dump(history, f)
            logger.debug(
                f"{uid_prefix} Saved {len(history)} performance scores to {self.history_file}"
            )
        except OSError as e:
            logger.error(
                f"{uid_prefix} Failed to save history to {self.history_file}: {e}"
            )

    async def fetch_consensus_result(
        self, validator_api_url: str, slot_num: int
    ) -> Optional[Dict]:
        """
        Fetch consensus result from validator API
        """
        uid_prefix = f"[FetchConsensus:{self.miner_uid_hex[:8]}...]"

        try:
            url = f"{validator_api_url}/api/v1/consensus/result/{slot_num}"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()

            result = response.json()
            logger.info(
                f"{uid_prefix} Successfully fetched consensus result for slot {slot_num}"
            )
            return result

        except httpx.ConnectError as e:
            logger.warning(f"{uid_prefix} Could not connect to validator API: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logger.warning(
                f"{uid_prefix} HTTP error {e.response.status_code} fetching consensus result"
            )
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"{uid_prefix} Invalid JSON response: {e}")
            return None
        except Exception as e:
            logger.exception(
                f"{uid_prefix} Unexpected error fetching consensus result: {e}"
            )
            return None

    async def get_miner_data_from_chain(self) -> Optional[Dict]:
        """
        Get miner data from Core blockchain using Web3
        """
        uid_prefix = f"[GetMinerData:{self.miner_uid_hex[:8]}...]"

        if not self.contract:
            logger.warning(f"{uid_prefix} No contract instance available")
            return None

        try:
            logger.debug(f"{uid_prefix} Fetching miner data from blockchain...")

            # Call getMinerInfo function on the contract
            # Use miner_account.address as the ID (not UID hex)
            if not self.miner_account:
                logger.error(f"{uid_prefix} No miner account available")
                return None

            result = self.contract.functions.getMinerInfo(
                self.miner_account.address
            ).call()

            if (
                result
                and result[0]
                != "0x0000000000000000000000000000000000000000000000000000000000000000"
            ):  # Check if UID is not zero
                logger.info(
                    f"{uid_prefix} Successfully fetched miner data from blockchain"
                )
                return {
                    "uid": result[0],
                    "stake": result[1],
                    "trust_score": result[2],
                    "last_update": result[3],
                    "api_endpoint": result[7] if len(result) > 7 else "",
                }
            else:
                logger.warning(f"{uid_prefix} Miner not found on blockchain")
                return None

        except Exception as e:
            logger.exception(
                f"{uid_prefix} Failed to fetch miner data from blockchain: {e}"
            )
            return None

    def calculate_new_performance(
        self, old_performance: float, score: float, alpha: float = 0.3
    ) -> float:
        """
        Calculate new performance using exponential moving average
        """
        uid_prefix = f"[CalcPerf:{self.miner_uid_hex[:8]}...]"

        try:
            # Exponential moving average
            new_performance = alpha * score + (1 - alpha) * old_performance

            logger.debug(
                f"{uid_prefix} Performance update: {old_performance:.4f} -> {new_performance:.4f} (score: {score:.4f})"
            )

            # Clamp giá trị trong khoảng [0, 1]
            return max(0.0, min(1.0, new_performance))

        except Exception as e:
            logger.warning(
                f"{uid_prefix} Error calculating new performance: {e}. Using old value."
            )
            return old_performance

    async def update_miner_data_on_chain(
        self, new_performance: float, slot_num: int
    ) -> Optional[str]:
        """
        Update miner performance data on Core blockchain
        """
        uid_prefix = f"[UpdateChain:{self.miner_uid_hex[:8]}...]"

        logger.info(
            f"{uid_prefix} Updating miner data on chain (performance: {new_performance:.4f}, slot: {slot_num})"
        )

        # Check if we have contract and account
        if not self.contract or not self.miner_account:
            logger.warning(
                f"{uid_prefix} No contract or account available - using simulation mode"
            )
            self._save_history(slot_num, new_performance)
            return "simulated_tx_hash"

        try:
            # Convert performance to uint64 (0-1_000_000 scale)
            performance_scaled = int(new_performance * 1_000_000)
            performance_scaled = max(0, min(1_000_000, performance_scaled))

            # Use current trust score (or default to 500_000 = 50%)
            trust_score_scaled = 500_000  # Default 50% trust score

            logger.info(
                f"{uid_prefix} Calling updateMinerScores: performance={performance_scaled}, trust_score={trust_score_scaled}"
            )

            # Build transaction for ModernTensor.sol contract
            tx = self.contract.functions.updateMinerScores(
                self.miner_account.address,  # miner address
                performance_scaled,  # new performance
                trust_score_scaled,  # new trust score
            ).build_transaction(
                {
                    "from": self.miner_account.address,
                    "gas": 200000,
                    "gasPrice": self.web3.eth.gas_price,
                    "nonce": self.web3.eth.get_transaction_count(
                        self.miner_account.address
                    ),
                }
            )

            # Sign and send transaction
            signed_tx = self.web3.eth.account.sign_transaction(
                tx, self.miner_account.key
            )
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)

            # Wait for transaction receipt
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

            if receipt.status == 1:
                logger.info(f"{uid_prefix} Transaction successful: {tx_hash.hex()}")
                self._save_history(slot_num, new_performance)
                return f"0x{tx_hash.hex()}"
            else:
                logger.error(f"{uid_prefix} Transaction failed: {tx_hash.hex()}")
                return None

        except Exception as e:
            logger.error(f"{uid_prefix} Failed to update blockchain: {e}")
            # Fallback to simulation mode
            self._save_history(slot_num, new_performance)
            return "simulated_tx_hash"

    async def run(self, validator_api_url: str, check_interval_seconds: int = 30):
        """
        Main run loop for the Core Miner Agent with slot synchronization
        """
        uid_prefix = f"[Run:{self.miner_uid_hex[:8]}...]"

        logger.info(
            f"{uid_prefix} Starting Core Miner Agent main loop with slot sync..."
        )
        logger.info(f"{uid_prefix} Validator API: {validator_api_url}")
        logger.info(f"{uid_prefix} Check interval: {check_interval_seconds}s")
        logger.info(f"{uid_prefix} Slot duration: {SLOT_DURATION_MINUTES} minutes")

        while True:
            try:
                # === SLOT SYNCHRONIZATION ===
                current_slot = self.get_current_slot()
                current_phase = self.get_slot_phase(current_slot)

                logger.debug(
                    f"{uid_prefix} Current slot: {current_slot}, phase: {current_phase}"
                )

                # Check if miner is registered on blockchain
                miner_data = await self.get_miner_data_from_chain()
                if not miner_data:
                    logger.warning(
                        f"{uid_prefix} Could not fetch miner data. Retrying in {check_interval_seconds}s..."
                    )
                    await asyncio.sleep(check_interval_seconds)
                    continue

                # === SLOT-BASED PROCESSING ===
                if (
                    current_slot > self.last_processed_slot
                    and self.should_check_consensus(current_slot)
                ):
                    logger.info(
                        f"{uid_prefix} Processing slot {current_slot} (phase: {current_phase})..."
                    )

                    # Fetch consensus result for this slot
                    consensus_result = await self.fetch_consensus_result(
                        validator_api_url, current_slot
                    )

                    if consensus_result:
                        # Calculate new performance (simplified)
                        score = consensus_result.get("score", 0.5)
                        new_performance = self.calculate_new_performance(
                            self.last_known_performance, score
                        )

                        # Update blockchain
                        tx_hash = await self.update_miner_data_on_chain(
                            new_performance, current_slot
                        )

                        if tx_hash:
                            self.last_processed_slot = current_slot
                            self.last_known_performance = new_performance

                            # Check if this is a simulated transaction
                            if tx_hash.startswith("simulated_"):
                                logger.info(
                                    f"{uid_prefix} Slot {current_slot} processed successfully (simulated update)"
                                )
                            else:
                                logger.info(
                                    f"{uid_prefix} Slot {current_slot} processed successfully → TX Hash: {tx_hash}"
                                )
                        else:
                            logger.error(
                                f"{uid_prefix} Failed to update blockchain for slot {current_slot}"
                            )
                    else:
                        logger.debug(
                            f"{uid_prefix} No consensus result available for slot {current_slot} (phase: {current_phase})"
                        )

                else:
                    # Calculate time until next slot for better logging
                    time_until_next = self.get_time_until_next_slot()
                    logger.debug(
                        f"{uid_prefix} Slot {current_slot} (phase: {current_phase}) - {time_until_next}s until next slot"
                    )

            except Exception as e:
                logger.exception(f"{uid_prefix} Error in main loop: {e}")

            await asyncio.sleep(check_interval_seconds)

    async def close(self):
        """Close the miner agent and cleanup resources"""
        uid_prefix = f"[Close:{self.miner_uid_hex[:8]}...]"
        logger.info(f"{uid_prefix} Closing Core Miner Agent...")
        # No specific cleanup needed for Web3 client
        logger.info(f"{uid_prefix} Core Miner Agent closed.")

    # === SLOT SYNCHRONIZATION METHODS ===

    def get_current_slot(self) -> int:
        """Get current slot number synchronized with validator timing"""
        current_time = int(time.time())
        slot_num = (current_time - EPOCH_START) // SLOT_DURATION_SECONDS
        return slot_num

    def get_slot_phase(self, slot_number: int) -> str:
        """Get current phase within a slot (for logging)"""
        current_time = int(time.time())
        slot_start_time = EPOCH_START + (slot_number * SLOT_DURATION_SECONDS)
        seconds_into_slot = current_time - slot_start_time

        if seconds_into_slot < 120:  # 0-2min
            return "TASK_ASSIGNMENT"
        elif seconds_into_slot < 180:  # 2-3min
            return "CONSENSUS_SCORING"
        elif seconds_into_slot < 210:  # 3-3.5min
            return "METAGRAPH_UPDATE"
        else:
            return "SLOT_END"

    def should_check_consensus(self, slot_number: int) -> bool:
        """Check if we should look for consensus results for this slot"""
        # Only check during consensus phase or after slot ends
        phase = self.get_slot_phase(slot_number)
        return phase in ["CONSENSUS_SCORING", "METAGRAPH_UPDATE", "SLOT_END"]

    def get_time_until_next_slot(self) -> int:
        """Get seconds until next slot starts"""
        current_time = int(time.time())
        current_slot = self.get_current_slot()
        next_slot_start = EPOCH_START + ((current_slot + 1) * SLOT_DURATION_SECONDS)
        return max(0, next_slot_start - current_time)
