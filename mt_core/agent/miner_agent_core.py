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


class CoreMinerAgent:
    """
    Core Blockchain compatible Miner Agent
    Manages miner performance tracking and blockchain interactions using Web3
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
                f"{uid_prefix} No miner account provided. Some operations may fail."
            )
            self.miner_account = None

        # --- Initialize Web3 client ---
        try:
            self.web3 = Web3(Web3.HTTPProvider(self.core_node_url))
            self.web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

            if not self.web3.is_connected():
                raise RuntimeError(
                    f"Failed to connect to Core blockchain at {self.core_node_url}"
                )

            logger.debug(
                f"{uid_prefix} Web3 client initialized (Node: {self.core_node_url})"
            )
            logger.debug(f"{uid_prefix} Contract address: {self.contract_address}")

            # Initialize contract if ABI provided
            if self.contract_address and self.contract_abi:
                self.contract = self.web3.eth.contract(
                    address=self.contract_address, abi=self.contract_abi
                )
                logger.debug(f"{uid_prefix} Contract instance created")
            else:
                self.contract = None
                logger.warning(
                    f"{uid_prefix} No contract ABI provided - some functions may not work"
                )

        except Exception as e:
            logger.exception(f"{uid_prefix} Failed to initialize Web3 client: {e}")
            raise

        # Load existing performance history
        self._load_history()

        logger.info(f"{uid_prefix} Core Miner Agent initialized successfully")

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

    def _save_history(self, cycle_num: int, performance: float):
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
                    "cycle": cycle_num,
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
        self, validator_api_url: str, cycle_num: int
    ) -> Optional[Dict]:
        """
        Fetch consensus result from validator API
        """
        uid_prefix = f"[FetchConsensus:{self.miner_uid_hex[:8]}...]"

        try:
            url = f"{validator_api_url}/api/v1/consensus/result/{cycle_num}"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()

            result = response.json()
            logger.info(
                f"{uid_prefix} Successfully fetched consensus result for cycle {cycle_num}"
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
        self, new_performance: float, cycle_num: int
    ) -> Optional[str]:
        """
        Update miner performance data on Core blockchain
        Note: This is a simplified version - actual implementation may vary based on contract design
        """
        uid_prefix = f"[UpdateChain:{self.miner_uid_hex[:8]}...]"

        logger.info(
            f"{uid_prefix} Updating miner data on chain (performance: {new_performance:.4f}, cycle: {cycle_num})"
        )

        # For now, just log the update (actual blockchain update would require specific contract functions)
        logger.info(
            f"{uid_prefix} Would update blockchain with performance: {new_performance:.4f}"
        )

        # Save to local history
        self._save_history(cycle_num, new_performance)

        return "simulated_tx_hash"

    async def run(self, validator_api_url: str, check_interval_seconds: int = 300):
        """
        Main run loop for the Core Miner Agent
        """
        uid_prefix = f"[Run:{self.miner_uid_hex[:8]}...]"

        logger.info(f"{uid_prefix} Starting Core Miner Agent main loop...")
        logger.info(f"{uid_prefix} Validator API: {validator_api_url}")
        logger.info(f"{uid_prefix} Check interval: {check_interval_seconds}s")

        while True:
            try:
                # Check if miner is registered on blockchain
                miner_data = await self.get_miner_data_from_chain()
                if not miner_data:
                    logger.warning(
                        f"{uid_prefix} Could not fetch miner data. Retrying in {check_interval_seconds}s..."
                    )
                    await asyncio.sleep(check_interval_seconds)
                    continue

                # For now, simulate cycle processing
                current_cycle = int(time.time()) // 300  # 5-minute cycles

                if current_cycle > self.last_processed_cycle:
                    logger.info(f"{uid_prefix} Processing cycle {current_cycle}...")

                    # Fetch consensus result
                    consensus_result = await self.fetch_consensus_result(
                        validator_api_url, current_cycle
                    )

                    if consensus_result:
                        # Calculate new performance (simplified)
                        score = consensus_result.get("score", 0.5)
                        new_performance = self.calculate_new_performance(
                            self.last_known_performance, score
                        )

                        # Update blockchain
                        tx_hash = await self.update_miner_data_on_chain(
                            new_performance, current_cycle
                        )

                        if tx_hash:
                            self.last_processed_cycle = current_cycle
                            self.last_known_performance = new_performance
                            logger.info(
                                f"{uid_prefix} Cycle {current_cycle} processed successfully"
                            )
                        else:
                            logger.error(
                                f"{uid_prefix} Failed to update blockchain for cycle {current_cycle}"
                            )
                    else:
                        logger.warning(
                            f"{uid_prefix} No consensus result available for cycle {current_cycle}"
                        )

                else:
                    logger.debug(
                        f"{uid_prefix} No new cycles to process (current: {current_cycle}, last: {self.last_processed_cycle})"
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
