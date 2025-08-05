#!/usr/bin/env python3
"""
ValidatorNode Core Module

This module contains the core functionality for ValidatorNode including:
- Initialization and configuration
- State management (cycle tracking, file persistence)
- Metagraph data loading and processing
- Basic utility methods

The core module provides the foundation that other modules build upon.
"""

import asyncio
import json
import logging
import os
import psutil
import string
import time
from collections import defaultdict, OrderedDict
from typing import Dict, List, Optional, Any

from web3 import Web3
from eth_account import Account

from ..config.config_loader import get_config
from ..core.datatypes import (
    ValidatorInfo,
    MinerInfo,
    CycleConsensusResults,
    MinerConsensusResult,
)
from ..metagraph.hash.hash_datum import hash_data
from ..monitoring.circuit_breaker import CircuitBreaker
from ..monitoring.rate_limiter import RateLimiter
from ..monitoring.metrics import get_metrics_manager
from .slot_coordinator import SlotCoordinator, SlotPhase, SlotConfig

logger = logging.getLogger(__name__)

# Constants
DEFAULT_BATCH_WAIT_TIME = 30.0
DEFAULT_CONSENSUS_TIMEOUT = 60  # Reduced for 3.5 minute cycles
DEFAULT_RESULT_TIMEOUT = 60.0
HTTP_TIMEOUT = 10.0
MAX_RETRIES = 3


class ValidatorNodeCore:
    """
    Core functionality for ValidatorNode.

    This class handles:
    - Node initialization and configuration
    - State persistence and cycle management
    - Metagraph data loading and verification
    - Basic node operations and utilities
    """

    def __init__(
        self,
        validator_info: ValidatorInfo,
        core_client: Web3,
        account: Account,
        contract_address: str,
        state_file: str = "validator_state.json",
        consensus_mode: str = "continuous",
        batch_wait_time: float = DEFAULT_BATCH_WAIT_TIME,
        api_port: Optional[int] = None,
    ):
        """
        Initialize ValidatorNode core components.

        Args:
            validator_info: Information about this validator
            core_client: Core blockchain Web3 client
            account: Core blockchain account for transactions
            contract_address: ModernTensor contract address
            state_file: Path to state persistence file
            consensus_mode: "continuous" or "sequential"
            batch_wait_time: Wait time between batches
            api_port: Port for API server (optional)
        """
        # Core identifiers
        self.info = validator_info
        self.uid_prefix = f"[{self.info.uid}]"

        # Blockchain connection
        self.core_client = core_client
        self.client = core_client  # Alias for compatibility
        self.account = account
        self.contract_address = contract_address

        # Configuration
        self.state_file = state_file
        self.consensus_mode = consensus_mode
        self.batch_wait_time = batch_wait_time
        self.api_port = api_port  # Store API port for network module
        self.config = get_config()
        self.settings = self.config.consensus  # Access consensus settings directly

        # Debug logging to verify api_port is properly set
        logger.info(
            f"{self.uid_prefix} ValidatorNodeCore initialized with api_port: {self.api_port}"
        )

        # Metrics and monitoring
        self.metrics = get_metrics_manager()
        self.metrics.update_memory_usage(psutil.Process().memory_info().rss)

        # State management
        self._current_cycle = self._load_last_cycle()
        self.slot_length = self.settings.cycle_length
        self.miners_selected_for_cycle = set()

        # Slot-based consensus configuration
        self.slot_config = SlotConfig(
            slot_duration_minutes=self.settings.slot_duration_minutes,
            task_assignment_minutes=self.settings.task_assignment_minutes,
            task_execution_minutes=self.settings.task_execution_minutes,
            consensus_minutes=self.settings.consensus_minutes,
            metagraph_update_seconds=self.settings.metagraph_update_seconds,
        )
        self.current_slot_phase = SlotPhase.TASK_ASSIGNMENT
        self.slot_phase_start_time = time.time()

        # Slot coordinator for synchronized consensus
        self.slot_coordinator = SlotCoordinator(
            validator_uid=self.info.uid, slot_config=self.slot_config
        )

        # Network and P2P state
        self.miners_info = {}
        self.validators_info = {}
        self.http_client = None
        self.contract_client = None

        # Task management
        self.tasks_sent = {}
        self.miner_is_busy = set()
        self.results_buffer = {}
        self.results_buffer_lock = asyncio.Lock()

        # Scoring and consensus
        self.cycle_scores = defaultdict(list)
        self.validator_scores = defaultdict(list)
        self.slot_scores = defaultdict(list)  # For slot-based scoring
        self.slot_aggregated_scores = (
            {}
        )  # slot -> {miner_uid: {validator_uid: avg_score}}
        self.consensus_results_cache = OrderedDict()
        self.consensus_results_cache_lock = asyncio.Lock()
        self.received_validator_scores = {}
        self.received_scores_lock = asyncio.Lock()

        # Task tracking for continuous assignment
        self.active_task_assignments = {}  # task_id -> assignment info

        # Health and monitoring
        self.health_server = None
        self.api_server = None
        self.previous_cycle_results = {}

        # Circuit breakers and rate limiting
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, reset_timeout=60)
        self.rate_limiter = RateLimiter(max_requests=100, time_window=60)

        # Reference to subnet validator instance for scoring
        self.validator_instance = None

        logger.info(f"✅ {self.uid_prefix} ValidatorNodeCore initialized successfully")
        logger.debug(f"{self.uid_prefix} State file: {self.state_file}")
        logger.debug(f"{self.uid_prefix} Consensus mode: {self.consensus_mode}")
        logger.debug(f"{self.uid_prefix} Slot configuration: {self.slot_config}")

    # === State Management Methods ===

    def _load_last_cycle(self) -> int:
        """Load the last completed cycle number from the state file."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, "r") as f:
                    state_data = json.load(f)
                    last_completed_cycle = state_data.get("last_completed_cycle", -1)
                    next_cycle = last_completed_cycle + 1
                    logger.debug(
                        f"{self.uid_prefix} Loaded state: last_completed_cycle={last_completed_cycle}, next_cycle={next_cycle}"
                    )
                    return next_cycle
            else:
                logger.debug(
                    f"{self.uid_prefix} State file not found, starting from cycle 0"
                )
                return 0
        except Exception as e:
            logger.error(f"{self.uid_prefix} Error loading state: {e}")
            return 0

    def _save_current_cycle(self, completed_cycle: int):
        """Save the completed cycle number to the state file."""
        if completed_cycle < 0:
            logger.debug(
                f"{self.uid_prefix} No cycle completed yet ({completed_cycle}), skipping state save"
            )
            return

        state_data = {"last_completed_cycle": completed_cycle}
        try:
            # Ensure directory exists before writing
            os.makedirs(os.path.dirname(self.state_file) or ".", exist_ok=True)
            with open(self.state_file, "w") as f:
                json.dump(state_data, f, indent=2)
            logger.debug(
                f"{self.uid_prefix} Saved last completed cycle {completed_cycle} to {self.state_file}"
            )
        except Exception as e:
            logger.error(f"{self.uid_prefix} Error saving state: {e}")

    # === Cycle Management Methods ===

    def get_current_cycle_number(self) -> int:
        """Get the current cycle number."""
        return self._current_cycle

    @property
    def current_cycle(self) -> int:
        """Property to get the current cycle number."""
        return self._current_cycle

    def set_current_cycle(self, cycle: int):
        """Set the current cycle number."""
        self._current_cycle = cycle

    def advance_to_next_cycle(self):
        """Advance to the next cycle."""
        self._current_cycle += 1

    # === Consensus Results Cache Methods ===

    async def get_consensus_results_for_cycle(
        self, cycle_num: int
    ) -> Optional[CycleConsensusResults]:
        """Retrieve cached consensus results for a specific cycle."""
        async with self.consensus_results_cache_lock:
            return self.consensus_results_cache.get(cycle_num)

    async def _publish_consensus_results(
        self,
        cycle: int,
        final_miner_scores: Dict[str, float],
        calculated_rewards: Dict[str, float],
    ):
        """
        Cache consensus results for API access.

        Args:
            cycle: The cycle number these results belong to
            final_miner_scores: Final adjusted performance scores for miners
            calculated_rewards: Calculated incentive rewards for miners
        """
        logger.info(f"{self.uid_prefix} Caching consensus results for cycle {cycle}")
        results_for_miners: Dict[str, MinerConsensusResult] = {}

        # Get all miner IDs from final_scores or calculated_rewards
        all_miner_ids = set(final_miner_scores.keys()) | set(calculated_rewards.keys())

        for miner_uid_hex in all_miner_ids:
            p_adj = final_miner_scores.get(miner_uid_hex, 0.0)
            incentive = calculated_rewards.get(miner_uid_hex, 0.0)

            # Create result object for this miner
            miner_result = MinerConsensusResult(
                miner_uid=miner_uid_hex, p_adj=p_adj, calculated_incentive=incentive
            )
            results_for_miners[miner_uid_hex] = miner_result

        # Create cycle results object
        cycle_results = CycleConsensusResults(
            cycle=cycle,
            results=results_for_miners,
            publisher_uid=(
                self.info.uid.hex()
                if isinstance(self.info.uid, bytes)
                else self.info.uid
            ),
        )

        # Save to cache
        async with self.consensus_results_cache_lock:
            self.consensus_results_cache[cycle] = cycle_results
            # Keep cache within size limits
            max_cache_cycles = 10
            while len(self.consensus_results_cache) > max_cache_cycles:
                self.consensus_results_cache.popitem(last=False)

        logger.info(
            f"{self.uid_prefix} Consensus results for cycle {cycle} cached ({len(results_for_miners)} miners)"
        )

    # === Metagraph Data Loading Methods ===

    async def load_metagraph_data(self):
        """
        Load miner and validator data from the Core blockchain.

        Fetches all miner and validator information from the ModernTensor smart contract,
        verifies performance history against local state, and updates internal node state.

        Raises:
            RuntimeError: If critical errors occur during data fetching or processing.
        """
        logger.info(
            f"{self.uid_prefix} Loading metagraph data from Core blockchain for cycle {self._current_cycle}"
        )
        start_time = time.time()

        # Store previous state for comparison
        previous_miners_info = self.miners_info.copy()
        previous_validators_info = self.validators_info.copy()

        try:
            # Import Core blockchain client - use CoreMetagraphClient which works correctly
            from ..metagraph.core_metagraph_adapter import CoreMetagraphClient

            # Initialize Core client if not already done
            if (
                not hasattr(self, "core_contract_client")
                or not self.core_contract_client
            ):
                self.core_contract_client = CoreMetagraphClient()

            # Fetch miners and validators data from Core blockchain
            miners_addresses = self.core_contract_client.get_all_miners()
            validators_addresses = self.core_contract_client.get_all_validators()

            # Fetch detailed info for each miner and validator
            miners_data = {}
            validators_data = {}

            # Process miners
            for miner_address in miners_addresses:
                try:
                    miner_info = self.core_contract_client.get_miner_info(miner_address)
                    if miner_info:
                        miners_data[miner_address] = miner_info
                except Exception as e:
                    logger.warning(
                        f"{self.uid_prefix} Error fetching miner {miner_address}: {e}"
                    )

            # Process validators
            for validator_address in validators_addresses:
                try:
                    validator_info = self.core_contract_client.get_validator_info(
                        validator_address
                    )
                    if validator_info:
                        validators_data[validator_address] = validator_info
                except Exception as e:
                    logger.warning(
                        f"{self.uid_prefix} Error fetching validator {validator_address}: {e}"
                    )

            logger.info(
                f"{self.uid_prefix} Fetched {len(miners_data)} miners and {len(validators_data)} validators from Core blockchain"
            )

            # Process the data
            max_history_len = getattr(self.settings, "max_performance_history_len", 10)

            # Process miners and validators
            temp_miners_info = self._process_miners_data(
                miners_data, previous_miners_info, max_history_len
            )
            temp_validators_info = self._process_validators_data(
                validators_data, previous_validators_info, max_history_len
            )

            # Update node state
            self.miners_info = temp_miners_info
            self.validators_info = temp_validators_info

            # If no miners found and we're in flexible mode, create mock miners for testing
            if not self.miners_info and hasattr(self, 'flexible_mode_enabled') and self.flexible_mode_enabled:
                logger.info(f"{self.uid_prefix} No miners found on blockchain, creating mock miners for flexible mode testing")
                self._create_mock_miners_for_flexible_mode()

            # Update self validator info
            self._update_self_validator_info()

            # Log results
            duration = time.time() - start_time
            logger.info(
                f"{self.uid_prefix} Metagraph data loaded successfully from Core blockchain in {duration:.2f}s: "
                f"{len(self.miners_info)} miners, {len(self.validators_info)} validators"
            )

            # Debug: Log loaded validator details for troubleshooting
            logger.debug(f"{self.uid_prefix} Debug - Loaded validators:")
            for validator_uid, validator_info in self.validators_info.items():
                logger.debug(f"{self.uid_prefix} Debug - Validator {validator_uid}:")
                logger.debug(f"  - Type: {type(validator_info)}")
                logger.debug(f"  - UID: {getattr(validator_info, 'uid', 'N/A')}")
                logger.debug(
                    f"  - Address: {getattr(validator_info, 'address', 'N/A')}"
                )
                logger.debug(
                    f"  - API Endpoint: {getattr(validator_info, 'api_endpoint', 'N/A')}"
                )
                logger.debug(
                    f"  - Status: {getattr(validator_info, 'status', 'N/A')} (type: {type(getattr(validator_info, 'status', None))})"
                )
                logger.debug(f"  - Stake: {getattr(validator_info, 'stake', 'N/A')}")

            # Debug: Log loaded miner details
            logger.debug(f"{self.uid_prefix} Debug - Loaded miners:")
            for miner_uid, miner_info in self.miners_info.items():
                logger.debug(f"{self.uid_prefix} Debug - Miner {miner_uid}:")
                logger.debug(f"  - Type: {type(miner_info)}")
                logger.debug(f"  - UID: {getattr(miner_info, 'uid', 'N/A')}")
                logger.debug(f"  - Address: {getattr(miner_info, 'address', 'N/A')}")
                logger.debug(
                    f"  - API Endpoint: {getattr(miner_info, 'api_endpoint', 'N/A')}"
                )
                logger.debug(
                    f"  - Status: {getattr(miner_info, 'status', 'N/A')} (type: {type(getattr(miner_info, 'status', None))})"
                )

        except Exception as e:
            logger.error(
                f"{self.uid_prefix} Critical error during Core blockchain data loading: {e}"
            )
            self.miners_info = {}
            self.validators_info = {}
            raise RuntimeError(
                f"Failed to load and process metagraph data from Core blockchain: {e}"
            ) from e

    def _process_miners_data(
        self, miners_data: Dict, previous_miners_info: Dict, max_history_len: int
    ) -> Dict:
        """Process miners data with performance history verification."""
        temp_miners_info = {}

        for uid_hex, miner_data in miners_data.items():
            try:
                if not uid_hex:
                    continue

                # Convert dict to object-like access
                performance_history_hash = miner_data.get(
                    "performance_history_hash", ""
                )

                # Verify performance history
                verified_history = self._verify_performance_history(
                    performance_history_hash,
                    previous_miners_info.get(uid_hex),
                    max_history_len,
                    uid_hex,
                )

                # Create MinerInfo object with verified history
                from ..core.datatypes import MinerInfo

                miner_info = MinerInfo(
                    uid=miner_data.get("uid", ""),
                    address=miner_data.get("address", ""),
                    api_endpoint=miner_data.get("api_endpoint", ""),
                    trust_score=miner_data.get("scaled_trust_score", 0.0),
                    stake=miner_data.get("stake", 0.0),
                    status=miner_data.get("status", 0),
                    performance_history=verified_history,
                    subnet_uid=miner_data.get("subnet_uid", 0),
                    registration_time=miner_data.get("registration_time", 0),
                )
                temp_miners_info[uid_hex] = miner_info

            except Exception as e:
                logger.warning(
                    f"{self.uid_prefix} Error processing miner {uid_hex}: {e}"
                )

        return temp_miners_info

    def _process_validators_data(
        self,
        validators_data: Dict,
        previous_validators_info: Dict,
        max_history_len: int,
    ) -> Dict:
        """Process validators data with performance history verification and endpoint sanitization."""
        temp_validators_info = {}

        for uid_hex, validator_data in validators_data.items():
            try:
                if not uid_hex:
                    continue

                # Convert dict to object-like access
                performance_history_hash = validator_data.get(
                    "performance_history_hash", ""
                )
                api_endpoint = validator_data.get("api_endpoint", "")

                # Verify performance history
                verified_history = self._verify_performance_history(
                    performance_history_hash,
                    previous_validators_info.get(uid_hex),
                    max_history_len,
                    uid_hex,
                )

                # Sanitize API endpoint
                clean_endpoint = self._sanitize_api_endpoint(api_endpoint, uid_hex)

                # Create ValidatorInfo object with verified data
                from ..core.datatypes import ValidatorInfo

                validator_info = ValidatorInfo(
                    uid=validator_data.get("uid", ""),
                    address=validator_data.get("address", ""),
                    api_endpoint=clean_endpoint,
                    last_performance=validator_data.get("scaled_last_performance", 0.0),
                    trust_score=validator_data.get("scaled_trust_score", 0.0),
                    stake=validator_data.get("stake", 0.0),
                    status=validator_data.get("status", 0),
                    performance_history=verified_history,
                    subnet_uid=validator_data.get("subnet_uid", 0),
                    registration_time=validator_data.get("registration_time", 0),
                )
                temp_validators_info[uid_hex] = validator_info

            except Exception as e:
                logger.warning(
                    f"{self.uid_prefix} Error processing validator {uid_hex}: {e}"
                )

        return temp_validators_info

    def _verify_performance_history(
        self,
        on_chain_hash: bytes,
        previous_info: Any,
        max_history_len: int,
        uid_hex: str,
    ) -> List:
        """Verify performance history against on-chain hash."""
        current_local_history = []
        if previous_info and hasattr(previous_info, "performance_history"):
            current_local_history = previous_info.performance_history

        verified_history = []
        if on_chain_hash and current_local_history:
            try:
                local_history_hash = hash_data(current_local_history)
                if local_history_hash == on_chain_hash:
                    verified_history = current_local_history
                    logger.debug(f"{self.uid_prefix} {uid_hex}: Local history verified")
                else:
                    logger.warning(
                        f"{self.uid_prefix} {uid_hex}: History hash mismatch, resetting"
                    )
                    verified_history = []
            except Exception as e:
                logger.error(
                    f"{self.uid_prefix} {uid_hex}: Error hashing local history: {e}"
                )
                verified_history = []
        else:
            verified_history = current_local_history

        return verified_history[-max_history_len:]

    def _sanitize_api_endpoint(self, raw_endpoint: str, uid_hex: str) -> Optional[str]:
        """Sanitize API endpoint to ensure it's valid."""
        if isinstance(raw_endpoint, str):
            if raw_endpoint.startswith(("http://", "https://")) and all(
                c in string.printable for c in raw_endpoint
            ):
                return raw_endpoint
            else:
                logger.warning(
                    f"{self.uid_prefix} {uid_hex}: Invalid API endpoint format, setting to None"
                )
                return None
        elif raw_endpoint is not None:
            logger.warning(
                f"{self.uid_prefix} {uid_hex}: API endpoint is not a string, setting to None"
            )
            return None
        return None

    def _update_self_validator_info(self):
        """Update self validator information from metagraph."""
        self_uid_hex = (
            self.info.uid.hex() if isinstance(self.info.uid, bytes) else self.info.uid
        )

        if self_uid_hex in self.validators_info:
            loaded_info = self.validators_info[self_uid_hex]

            # CRITICAL FIX: Only update api_endpoint if we don't have explicit api_port
            if not hasattr(self, "api_port") or self.api_port is None:
                self.info.api_endpoint = loaded_info.api_endpoint
                logger.debug(
                    f"{self.uid_prefix} Updated api_endpoint from blockchain: {loaded_info.api_endpoint}"
                )
            else:
                logger.info(
                    f"{self.uid_prefix} Preserving configured api_port {self.api_port}, ignoring blockchain api_endpoint {loaded_info.api_endpoint}"
                )

            self.info.trust_score = loaded_info.trust_score
            self.info.weight = loaded_info.weight
            self.info.stake = loaded_info.stake
            logger.debug(
                f"{self.uid_prefix} Self validator info updated from metagraph"
            )
        elif self.info.uid:
            self.validators_info[self_uid_hex] = self.info
            logger.warning(
                f"{self.uid_prefix} Self validator not found in metagraph, added locally"
            )
        else:
            logger.error(f"{self.uid_prefix} Self validator UID is None!")

    # === Utility Methods ===

    def get_current_blockchain_slot(self) -> int:
        """Get current blockchain slot number based on timestamp."""
        return self.slot_coordinator.get_current_blockchain_slot()

    def get_slot_phase(self, slot_number: int) -> tuple[SlotPhase, int, int]:
        """Get current phase within a slot and time remaining."""
        return self.slot_coordinator.get_slot_phase(slot_number)

    async def cleanup_resources(self):
        """Clean up resources when shutting down."""
        try:
            if self.http_client:
                await self.http_client.aclose()

            # Clean up old coordination files
            current_slot = self.get_current_blockchain_slot()
            self.slot_coordinator.cleanup_old_coordination_files(current_slot)

            logger.info(f"{self.uid_prefix} Resources cleaned up successfully")
        except Exception as e:
            logger.warning(f"{self.uid_prefix} Error during resource cleanup: {e}")

    async def update_metagraph_with_consensus(self):
        """
        Update metagraph with consensus results for the current slot.

        This method is called during METAGRAPH_UPDATE phase to finalize
        consensus scores and update the on-chain state.
        """
        try:
            current_slot = self.get_current_blockchain_slot()

            logger.info(
                f"{self.uid_prefix} Updating metagraph with consensus for slot {current_slot}"
            )

            # Ensure aggregation has been done - fallback if needed
            if current_slot not in self.slot_aggregated_scores and hasattr(
                self, "consensus"
            ):
                logger.warning(
                    f"{self.uid_prefix} slot_aggregated_scores empty for slot {current_slot}, "
                    "triggering emergency aggregation"
                )
                await self.consensus._emergency_aggregate_scores(current_slot)

            # Get aggregated scores for this slot
            slot_scores = self.slot_aggregated_scores.get(current_slot, {})

            if slot_scores:
                logger.info(
                    f"{self.uid_prefix} Found {len(slot_scores)} miner score aggregations for slot {current_slot}"
                )

                # Calculate final consensus scores by averaging across validators
                final_consensus_scores = {}
                for miner_uid, validator_scores in slot_scores.items():
                    if validator_scores:
                        # Average scores from all validators for this miner
                        avg_score = sum(validator_scores.values()) / len(
                            validator_scores
                        )
                        final_consensus_scores[miner_uid] = avg_score

                        logger.debug(
                            f"{self.uid_prefix} Final consensus score for Miner {miner_uid[:8]}...: "
                            f"{avg_score:.4f} (from {len(validator_scores)} validators)"
                        )

                # Update smart contract with final consensus scores
                if final_consensus_scores and hasattr(self, "consensus"):
                    try:
                        await self.consensus.submit_consensus_to_blockchain(
                            final_consensus_scores
                        )
                        logger.info(
                            f"{self.uid_prefix} Successfully updated smart contract with {len(final_consensus_scores)} consensus scores"
                        )
                    except Exception as contract_error:
                        logger.error(
                            f"{self.uid_prefix} Failed to update smart contract: {contract_error}"
                        )

                # Clear processed scores to free memory
                if current_slot in self.slot_aggregated_scores:
                    del self.slot_aggregated_scores[current_slot]

                logger.info(
                    f"{self.uid_prefix} Metagraph update completed for slot {current_slot}"
                )
            else:
                logger.debug(
                    f"{self.uid_prefix} No consensus scores to update for slot {current_slot}"
                )

        except Exception as e:
            logger.error(
                f"{self.uid_prefix} Error updating metagraph with consensus: {e}"
            )

    def save_state(self):
        """
        Save validator state to persistent storage.
        This method saves the current validator state to a JSON file.
        """
        try:
            state_data = {
                "current_cycle": self._current_cycle,
                "last_metagraph_update": getattr(self, "last_metagraph_update", 0),
                "validators_info_count": (
                    len(self.validators_info) if self.validators_info else 0
                ),
                "miners_info_count": len(self.miners_info) if self.miners_info else 0,
                "consensus_mode": self.consensus_mode,
                "slot_aggregated_scores_count": len(self.slot_aggregated_scores),
                "timestamp": time.time(),
            }

            with open(self.state_file, "w") as f:
                json.dump(state_data, f, indent=2)

            logger.debug(f"{self.uid_prefix} State saved to {self.state_file}")

        except Exception as e:
            logger.warning(f"{self.uid_prefix} Failed to save state: {e}")
