# sdk/consensus/node.py
"""
ValidatorNode: Main coordination class for ModernTensor consensus protocol

This module implements the core consensus logic for validators in the ModernTensor network.
Key features:
- Synchronized slot-based consensus (similar to Cardano)
- P2P validator coordination
- Task assignment and result scoring
- Metagraph updates with consensus averaging
- Blockchain submission of final scores

The ValidatorNode coordinates with other validators to ensure synchronized:
- Task assignment cutoff times
- Consensus score calculation
- Metagraph updates
- Blockchain submissions
"""

import asyncio
import json
import logging
import math
import os
import psutil
import random
import string
import sys
import time
import uvicorn
from collections import defaultdict, OrderedDict
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set

import httpx

# --- Core Configuration ---
from ..config.settings import settings

# --- Monitoring & Metrics ---
from ..monitoring.health import app as health_app
from ..monitoring.circuit_breaker import CircuitBreaker
from ..monitoring.rate_limiter import RateLimiter
from ..monitoring.metrics import get_metrics_manager, reset_metrics

# --- Formulas ---
from ..formulas.incentive import calculate_miner_incentive, calculate_validator_incentive
from ..formulas.performance import calculate_adjusted_miner_performance, calculate_validator_performance
from ..formulas.trust_score import update_trust_score
from ..formulas.penalty import calculate_fraud_severity_value, calculate_slash_amount

# --- Core Data Types ---
from ..core.datatypes import (
    MinerInfo,
    ValidatorInfo,
    TaskAssignment,
    MinerResult,
    ValidatorScore,
    CycleConsensusResults,
    MinerConsensusResult,
)

# --- Metagraph & Data ---
from ..metagraph.metagraph_data import get_all_miner_data, get_all_validator_data
from ..metagraph import metagraph_data
from ..metagraph.metagraph_datum import (
    MinerData,
    ValidatorData,
    STATUS_ACTIVE,
    STATUS_JAILED,
    STATUS_INACTIVE,
)
from ..metagraph.hash.hash_datum import hash_data

# --- Aptos SDK ---
from aptos_sdk.account import Account
from aptos_sdk.async_client import RestClient, EntryFunction, TransactionArgument, TransactionPayload, TypeTag, StructTag
try:
    from aptos_sdk.bcs import Serializer
except ImportError:
    from aptos_sdk.async_client import Serializer

# --- Aptos Integration ---
from ..aptos_core.contract_client import AptosContractClient, create_aptos_client
from ..aptos_core.context import get_aptos_context
from ..aptos_core.account_service import check_account_exists, get_account_balance
from ..aptos_core.validator_helper import get_validator_info, get_all_validators, get_all_miners

# --- Network & Communication ---
from ..network.server import TaskModel, ResultModel

# --- Consensus Components ---
from .selection import select_miners_logic
from .scoring import score_results_logic, broadcast_scores_logic
from .state import (
    run_consensus_logic,
    verify_and_penalize_logic,
    prepare_miner_updates_logic,
    prepare_validator_updates_logic,
    commit_updates_logic,
)
from .slot_coordinator import SlotCoordinator, SlotPhase, SlotConfig

# --- Logging ---
logger = logging.getLogger(__name__)

# --- Constants ---
DEFAULT_BATCH_WAIT_TIME = 30.0
DEFAULT_CONSENSUS_TIMEOUT = 120
DEFAULT_RESULT_TIMEOUT = 60.0
HTTP_TIMEOUT = 10.0
MAX_RETRIES = 3


# --- Utility Functions ---
async def decode_history_from_hash(hash_str):
    """Mock function for history decoding (to be implemented later)"""
    await asyncio.sleep(0)
    return []


class ValidatorNode:
    """
    Main coordinating class for a Validator Node in the ModernTensor consensus protocol.
    
    This class manages the complete consensus lifecycle:
    1. Task Assignment Phase: Synchronized task distribution to miners
    2. Task Execution Phase: Waiting for miner results
    3. Consensus Phase: P2P score coordination between validators
    4. Metagraph Update Phase: Synchronized metagraph updates
    
    The node coordinates with other validators using file-based coordination
    to ensure synchronized phase transitions and consensus calculations.
    """

    def __init__(
        self,
        validator_info: ValidatorInfo,
        aptos_client: RestClient,
        account: Account,
        contract_address: str,
        state_file: str = "validator_state.json",
        consensus_mode: str = "continuous",
        batch_wait_time: float = DEFAULT_BATCH_WAIT_TIME,
    ):
        """
        Initialize ValidatorNode with all required components.
        
        Args:
            validator_info: Information about this validator
            aptos_client: Aptos blockchain client
            account: Aptos account for transactions
            contract_address: ModernTensor contract address
            state_file: Path to state persistence file
            consensus_mode: "continuous" or "sequential"
            batch_wait_time: Wait time between batches
        """
        # Core identifiers
        self.info = validator_info
        self.uid_prefix = f"[{self.info.uid}]"
        
        # Blockchain connection
        self.aptos_client = aptos_client
        self.client = aptos_client  # Alias for compatibility
        self.account = account
        self.contract_address = contract_address
        
        # Configuration
        self.state_file = state_file
        self.consensus_mode = consensus_mode
        self.batch_wait_time = batch_wait_time
        self.settings = settings
        
        # Metrics and monitoring
        self.metrics = get_metrics_manager()
        self.metrics.update_memory_usage(psutil.Process().memory_info().rss)
        
        # State management
        self._current_cycle = self._load_last_cycle()
        self.slot_length = self.settings.CONSENSUS_CYCLE_LENGTH
        self.miners_selected_for_cycle = set()
        
        # Slot-based consensus configuration
        self.slot_config = SlotConfig(
            slot_duration_minutes=settings.SLOT_DURATION_MINUTES,
            task_assignment_minutes=settings.TASK_ASSIGNMENT_MINUTES,
            task_execution_minutes=settings.TASK_EXECUTION_MINUTES,
            consensus_minutes=settings.CONSENSUS_MINUTES
        )
        self.current_slot_phase = SlotPhase.TASK_ASSIGNMENT
        self.slot_phase_start_time = time.time()
        
        # Slot coordinator for synchronized consensus
        self.slot_coordinator = SlotCoordinator(validator_uid=self.info.uid)
        
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
        self.consensus_results_cache = OrderedDict()
        self.consensus_results_cache_lock = asyncio.Lock()
        self.received_validator_scores = {}
        self.received_scores_lock = asyncio.Lock()
        
        # Health and monitoring
        self.health_server = None
        self.api_server = None
        self.previous_cycle_results = {}
        
        # Circuit breakers and rate limiting
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=Exception
        )
        self.rate_limiter = RateLimiter(max_requests=100, time_window=60)
        
        logger.info(f"✅ {self.uid_prefix} ValidatorNode initialized successfully")
        logger.debug(f"{self.uid_prefix} State file: {self.state_file}")
        logger.debug(f"{self.uid_prefix} Consensus mode: {self.consensus_mode}")
        logger.debug(f"{self.uid_prefix} Slot configuration: {self.slot_config}")

    def _load_last_cycle(self) -> int:
        """Loads the last completed cycle number from the state file."""
        # Use self.uid_prefix if self.info is already set, otherwise default
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, "r") as f:
                    state_data = json.load(f)
                    last_completed_cycle = state_data.get("last_completed_cycle", -1)
                    next_cycle = last_completed_cycle + 1
                    logger.debug(f"{self.uid_prefix} Loaded state: last_completed_cycle={last_completed_cycle}, next_cycle={next_cycle}")
                    return next_cycle
            else:
                logger.debug(f"{self.uid_prefix} State file not found, starting from cycle 0")
                return 0
        except Exception as e:
            logger.error(f"{self.uid_prefix} Error loading state: {e}")
            return 0

    def _save_current_cycle(self, completed_cycle: int):
        """Save the completed cycle number to the state file."""
        if completed_cycle < 0:
            logger.debug(f"{self.uid_prefix} No cycle completed yet ({completed_cycle}), skipping state save")
            return

        state_data = {"last_completed_cycle": completed_cycle}
        try:
            # Ensure directory exists before writing
            os.makedirs(os.path.dirname(self.state_file) or ".", exist_ok=True)
            with open(self.state_file, "w") as f:
                json.dump(state_data, f, indent=2)
            logger.debug(f"{self.uid_prefix} Saved last completed cycle {completed_cycle} to {self.state_file}")
        except Exception as e:
            logger.error(f"{self.uid_prefix} Error saving state: {e}")

    # --- Thêm phương thức mới để lấy kết quả từ cache ---
    async def get_consensus_results_for_cycle(
        self, cycle_num: int
    ) -> Optional[CycleConsensusResults]:
        """Retrieves cached consensus results for a specific cycle."""
        async with self.consensus_results_cache_lock:
            return self.consensus_results_cache.get(cycle_num)

    # --- Thêm phương thức mới để công bố/lưu kết quả ---
    async def _publish_consensus_results(
        self,
        cycle: int,
        final_miner_scores: Dict[str, float],
        calculated_rewards: Dict[str, float],
    ):
        """
        Caches the consensus results for API access.
        (Placeholder: Future extensions could include signing, IPFS upload, or on-chain hash commit).

        Args:
            cycle (int): The cycle number these results belong to.
            final_miner_scores (Dict[str, float]): Final adjusted performance scores for miners.
            calculated_rewards (Dict[str, float]): Calculated incentive rewards for miners.
        """
        logger.info(
            f"[V:{self.info.uid}] Caching consensus results for cycle {cycle}..."
        )
        results_for_miners: Dict[str, MinerConsensusResult] = {}

        # Lấy tất cả miner IDs từ final_scores hoặc calculated_rewards
        all_miner_ids = set(final_miner_scores.keys()) | set(calculated_rewards.keys())

        for miner_uid_hex in all_miner_ids:
            p_adj = final_miner_scores.get(
                miner_uid_hex, 0.0
            )  # Mặc định 0 nếu không có điểm
            incentive = calculated_rewards.get(
                miner_uid_hex, 0.0
            )  # Mặc định 0 nếu không có thưởng

            # Tạo đối tượng kết quả cho miner này
            # Note: hiện tại chưa tính sẵn trust_score mới cho miner ở đây
            # vì việc đó miner sẽ tự làm khi cập nhật.
            miner_result = MinerConsensusResult(
                miner_uid=miner_uid_hex, p_adj=p_adj, calculated_incentive=incentive
            )
            results_for_miners[miner_uid_hex] = miner_result

        # Tạo đối tượng kết quả cho cả chu kỳ
        cycle_results = CycleConsensusResults(
            cycle=cycle,
            results=results_for_miners,
            publisher_uid=(
                self.info.uid.hex()
                if isinstance(self.info.uid, bytes)
                else self.info.uid
            ),  # Đã bỏ comment và thêm uid
            # signature=... # Thêm chữ ký sau
        )

        # Lưu vào cache (dùng OrderedDict để giới hạn kích thước)
        async with self.consensus_results_cache_lock:
            self.consensus_results_cache[cycle] = cycle_results
            # Giữ cache trong giới hạn kích thước
            while len(self.consensus_results_cache) > self.max_cache_cycles:
                self.consensus_results_cache.popitem(last=False)  # Xóa item cũ nhất

        logger.info(
            f"Consensus results for cycle {cycle} cached ({len(results_for_miners)} miners). Ready for API access."
        )
        # TODO (Future): Implement actual publication (IPFS, On-chain hash, Signed API)

    # --- Tương tác Metagraph ---
    async def load_metagraph_data(self):
        """
        Load miner and validator data from the Aptos blockchain.
        
        Fetches all miner and validator information from the ModernTensor smart contract,
        verifies performance history against local state, and updates internal node state.
        
        Raises:
            RuntimeError: If critical errors occur during data fetching or processing.
        """
        logger.info(f"{self.uid_prefix} Loading metagraph data from Aptos blockchain for cycle {self._current_cycle}")
        start_time = time.time()

        # Store previous state for comparison
        previous_miners_info = self.miners_info.copy()
        previous_validators_info = self.validators_info.copy()

        try:
            # Fetch miners and validators data in parallel
            from mt_aptos.aptos_core.validator_helper import get_all_validators, get_all_miners
            
            miners_data, validators_data = await asyncio.gather(
                get_all_miners(client=self.client, contract_address=self.contract_address),
                get_all_validators(client=self.client, contract_address=self.contract_address),
                return_exceptions=True
            )

            # Handle fetch errors
            if isinstance(miners_data, Exception):
                logger.error(f"{self.uid_prefix} Error fetching miners data: {miners_data}")
                miners_data = {}
            if isinstance(validators_data, Exception):
                logger.error(f"{self.uid_prefix} Error fetching validators data: {validators_data}")
                validators_data = {}

            logger.info(f"{self.uid_prefix} Fetched {len(miners_data)} miners and {len(validators_data)} validators")
            
            # Process the data
            max_history_len = getattr(settings, 'CONSENSUS_MAX_PERFORMANCE_HISTORY_LEN', 10)
            
            # Process miners and validators
            temp_miners_info = self._process_miners_data(miners_data, previous_miners_info, max_history_len)
            temp_validators_info = self._process_validators_data(validators_data, previous_validators_info, max_history_len)

            # --- Chuyển đổi dữ liệu miners thành MinerInfo ---
            # miners_data is a dict mapping uid -> MinerInfo objects
            for uid_hex, miner_data in miners_data.items():
                try:
                    if not uid_hex:
                        continue

                    # Lấy history hash từ dữ liệu (nếu có)
                    on_chain_history_hash_bytes = miner_data.performance_history_hash

                    # Lấy lịch sử hiệu suất từ thông tin cũ (nếu có)
                    current_local_history = []  # Mặc định là rỗng
                    previous_info = previous_miners_info.get(uid_hex)
                    if previous_info:
                        current_local_history = previous_info.performance_history  # Lấy lịch sử cũ từ bộ nhớ

                    # Xác minh lịch sử hiệu suất
                    verified_history = []  # Lịch sử sẽ được lưu vào MinerInfo mới
                    if on_chain_history_hash_bytes:
                        # Nếu có hash on-chain, thử xác minh lịch sử cục bộ
                        if current_local_history:
                            try:
                                local_history_hash = hash_data(current_local_history)
                                if local_history_hash == on_chain_history_hash_bytes:
                                    verified_history = current_local_history  # Hash khớp, giữ lại lịch sử cục bộ
                                    logger.debug(
                                        f"Miner {uid_hex}: Local history verified against on-chain hash."
                                    )
                                else:
                                    logger.warning(
                                        f"Miner {uid_hex}: Local history hash mismatch! Resetting history."
                                    )
                                    verified_history = []  # Hash không khớp, reset
                            except Exception as hash_err:
                                logger.error(
                                    f"Miner {uid_hex}: Error hashing local history: {hash_err}. Resetting history."
                                )
                                verified_history = []
                        else:
                            logger.warning(
                                f"Miner {uid_hex}: On-chain history hash found, but no local history available. Resetting history."
                            )
                            verified_history = []
                    else:
                        logger.debug(
                            f"Miner {uid_hex}: No on-chain history hash found. Using current local history."
                        )
                        verified_history = current_local_history  # Giữ lại lịch sử cục bộ (thường là rỗng)

                    # Đảm bảo giới hạn độ dài lịch sử
                    verified_history = verified_history[-max_history_len:]

                    # Lấy wallet_addr_hash nếu có
                    wallet_addr_hash_bytes = miner_data.wallet_addr_hash

                    # Use the existing MinerInfo object but update with verified history
                    miner_data.performance_history = verified_history
                    temp_miners_info[uid_hex] = miner_data

                except Exception as e:
                    logger.warning(
                        f"Lỗi khi phân tích dữ liệu Miner cho UID {uid_hex}: {e}",
                        exc_info=False,
                    )
                    logger.debug(f"Dữ liệu miner gặp vấn đề: {miner_data}")

            # --- Tương tự, chuyển đổi dữ liệu validator thành ValidatorInfo ---
            # validators_data is a dict mapping uid -> ValidatorInfo objects
            for uid_hex, validator_data in validators_data.items():
                try:
                    if not uid_hex:
                        continue

                    # Xử lý tương tự như với miners để lấy và xác minh history
                    on_chain_history_hash_bytes = validator_data.performance_history_hash

                    current_local_history = []
                    previous_info = previous_validators_info.get(uid_hex)
                    if previous_info and hasattr(previous_info, "performance_history"):
                        current_local_history = previous_info.performance_history

                    verified_history = []
                    # Xác minh history tương tự như với miners
                    if on_chain_history_hash_bytes:
                        if current_local_history:
                            try:
                                local_history_hash = hash_data(current_local_history)
                                if local_history_hash == on_chain_history_hash_bytes:
                                    verified_history = current_local_history
                                    logger.debug(
                                        f"Validator {uid_hex}: Local history verified."
                                    )
                                else:
                                    logger.warning(
                                        f"Validator {uid_hex}: History hash mismatch! Resetting."
                                    )
                                    verified_history = []
                            except Exception as hash_err:
                                logger.error(
                                    f"Validator {uid_hex}: Error hashing local history: {hash_err}. Resetting."
                                )
                                verified_history = []
                        else:
                            logger.warning(
                                f"Validator {uid_hex}: On-chain hash found, no local history. Resetting."
                            )
                            verified_history = []
                    else:
                        logger.debug(
                            f"Validator {uid_hex}: No on-chain history hash. Using current local."
                        )
                        verified_history = current_local_history

                    verified_history = verified_history[-max_history_len:]

                    # --- Lấy address bytes từ datum và decode ---
                    # Lấy các hash khác
                    wallet_addr_hash_bytes = validator_data.wallet_addr_hash
                    # ------------------------------------------

                    # <<< ADDED: Sanitize api_endpoint >>>
                    raw_endpoint = validator_data.api_endpoint
                    clean_endpoint: Optional[str] = None
                    if isinstance(raw_endpoint, str):
                        # Basic check for common protocols and printable chars
                        if raw_endpoint.startswith(("http://", "https://")) and all(
                            c in string.printable for c in raw_endpoint
                        ):
                            clean_endpoint = raw_endpoint
                        else:
                            logger.warning(
                                f"Validator {uid_hex}: Invalid format or characters in api_endpoint: '{raw_endpoint}'. Setting to None."
                            )
                    elif raw_endpoint is not None:
                        logger.warning(
                            f"Validator {uid_hex}: api_endpoint is not a string (type: {type(raw_endpoint)}). Setting to None."
                        )
                    # <<< END ADDED >>>

                    # Use the existing ValidatorInfo object but update with verified history and clean endpoint
                    validator_data.performance_history = verified_history
                    validator_data.api_endpoint = clean_endpoint  # Use sanitized endpoint
                    temp_validators_info[uid_hex] = validator_data
                    logger.debug(
                        f"  Loaded Validator Peer: UID={uid_hex}, Status={validator_data.status}, Endpoint='{validator_data.api_endpoint}'"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to parse Validator data dict for UID {uid_hex}: {e}",
                        exc_info=False,
                    )
                    logger.debug(f"Problematic validator data dict: {validator_data}")

            # --- Cập nhật trạng thái node ---
            self.miners_info = temp_miners_info
            self.validators_info = temp_validators_info

            # Cập nhật thông tin của chính mình
            self_uid_hex = (
                self.info.uid.hex()
                if isinstance(self.info.uid, bytes)
                else self.info.uid
            )
            if self_uid_hex in self.validators_info:
                loaded_info = self.validators_info[self_uid_hex]
                #  self.info.address = loaded_info.address
                self.info.api_endpoint = loaded_info.api_endpoint
                self.info.trust_score = loaded_info.trust_score
                self.info.weight = loaded_info.weight
                self.info.stake = loaded_info.stake
                # Cập nhật thêm các trường khác nếu cần
                logger.info(
                    f"Self validator info ({self_uid_hex}) updated from metagraph."
                )
            elif self.info.uid:
                self.validators_info[self_uid_hex] = self.info
                logger.warning(
                    f"Self validator ({self_uid_hex}) not found in metagraph, added locally. Ensure initial state is correct."
                )
            else:
                logger.error(
                    "Current validator info UID is invalid after loading metagraph."
                )

            # TODO: Load và xử lý dữ liệu Subnet/Foundation nếu cần

            load_duration = time.time() - start_time
            logger.info(
                f"Processed info for {len(self.miners_info)} miners and {len(self.validators_info)} validators in {load_duration:.2f}s."
            )

        except Exception as e:
            logger.exception(
                f"Critical error during metagraph data loading/processing: {e}. Cannot proceed this cycle."
            )
            logger.error(f"DETAILED ERROR TRACE:")
            import traceback
            logger.error(f"{traceback.format_exc()}")
            logger.error(f"Current miners_info before reset: {list(self.miners_info.keys()) if self.miners_info else 'None'}")
            logger.error(f"Current validators_info before reset: {list(self.validators_info.keys()) if self.validators_info else 'None'}")
            
            # Initialize empty objects on error
            self.miners_info = {}
            self.validators_info = {}
            logger.error(f"⚠️ MINERS_INFO RESET TO EMPTY DUE TO EXCEPTION! ⚠️")
            raise RuntimeError(f"Failed to load and process metagraph data: {e}") from e

    # --- Lựa chọn Miner ---
    def select_miners(self) -> List[MinerInfo]:
        """Selects miners for task assignment based on configured logic."""
        logger.info(
            f"[V:{self.info.uid}] Selecting miners for cycle {self._current_cycle}..."
        )
        num_to_select = self.settings.CONSENSUS_NUM_MINERS_TO_SELECT
        beta = self.settings.CONSENSUS_PARAM_BETA
        max_time_bonus = self.settings.CONSENSUS_PARAM_MAX_TIME_BONUS
        # Gọi hàm logic từ selection.py
        return select_miners_logic(
            miners_info=self.miners_info,
            current_cycle=self._current_cycle,
            num_to_select=num_to_select,  # Truyền số lượng cần chọn
            beta=beta,  # Truyền hệ số beta
            max_time_bonus=max_time_bonus,  # Truyền giới hạn bonus thời gian
        )

    def _select_available_miners_for_batch(self, num_to_select: int) -> List[MinerInfo]:
        """
        Selects a batch of available (not busy) and active miners using the main selection logic.

        Args:
            num_to_select (int): Desired number of miners for the batch (N).

        Returns:
            List[MinerInfo]: A list of selected available miners, up to num_to_select.
                             Returns an empty list if no suitable miners are found.
        """
        # 1. Lọc các miner đang hoạt động (active)
        active_miners_all = [
            m
            for m in self.miners_info.values()
            if getattr(m, "status", STATUS_ACTIVE) == STATUS_ACTIVE
        ]
        if not active_miners_all:
            logger.debug("Mini-batch selection: No active miners found.")
            return []

        # 2. Lọc tiếp các miner không bận (uid không có trong self.miner_is_busy)
        available_miners = [
            m for m in active_miners_all if m.uid not in self.miner_is_busy
        ]

        if not available_miners:
            # Không log warning vì đây là trường hợp bình thường khi chờ miner xử lý xong
            logger.debug(
                "Mini-batch selection: No available (not busy) active miners found at the moment."
            )
            return []

        logger.debug(
            f"Mini-batch selection: {len(available_miners)} available miners to choose from."
        )

        # 3. Chuẩn bị đầu vào cho logic lựa chọn chính (cần một dict)
        available_miners_dict = {m.uid: m for m in available_miners}

        # 4. Lấy các tham số lựa chọn từ settings
        beta = self.settings.CONSENSUS_PARAM_BETA
        max_time_bonus = self.settings.CONSENSUS_PARAM_MAX_TIME_BONUS

        # 5. Gọi logic lựa chọn hiện có (select_miners_logic) trên nhóm miner khả dụng
        #    Giới hạn số lượng chọn bằng số lượng thực tế khả dụng
        actual_num_to_select = min(num_to_select, len(available_miners))
        if actual_num_to_select <= 0:
            return []  # Không có ai để chọn

        # Gọi hàm logic từ selection.py
        selected_miners_for_batch = select_miners_logic(
            miners_info=available_miners_dict,
            current_cycle=self._current_cycle,  # Sử dụng cycle hiện tại để tính bonus time
            num_to_select=actual_num_to_select,  # Chọn tối đa N
            beta=beta,
            max_time_bonus=max_time_bonus,
        )

        logger.debug(
            f"Mini-batch selection: Selected {len(selected_miners_for_batch)} miners for this batch: {[m.uid for m in selected_miners_for_batch]}"
        )
        return selected_miners_for_batch

    # --- Giao Task ---
    # --- 1. Đánh dấu _create_task_data ---
    def _create_task_data(self, miner_uid: str) -> Any:
        """
        (Abstract/Needs Override) Creates specific task data for a miner.

        Inheriting Validator classes for each Subnet MUST override this method
        to define the task content and format appropriate for the AI problem.

        Args:
            miner_uid (str): The UID of the miner receiving the task.

        Returns:
            Any: The task data (should be JSON-serializable).

        Raises:
            NotImplementedError: If not overridden by the subclass.
        """
        logger.error(
            f"'_create_task_data' must be implemented by the inheriting Validator class for miner {miner_uid}."
        )
        raise NotImplementedError(
            "Subnet Validator must implement task creation logic."
        )

    async def _send_task_batch(
        self, miners_for_batch: List[MinerInfo], batch_num: int
    ) -> Dict[str, TaskAssignment]:
        """
        Creates and sends tasks to a specific batch of miners asynchronously.
        Marks miners as busy and tracks successfully sent tasks.

        Args:
            miners_for_batch: List of MinerInfo objects selected for this batch.
            batch_num: The sequence number of this mini-batch within the cycle.

        Returns:
            A dictionary {task_id: TaskAssignment} for tasks successfully sent
            in this batch. Returns an empty dict if no tasks could be sent.
        """
        if not miners_for_batch:
            logger.info(f"Batch {batch_num}: No miners provided for task sending.")
            return {}

        logger.info(
            f"Batch {batch_num}: Preparing to send tasks to {len(miners_for_batch)} miners..."
        )

        tasks_to_send_coroutines = []
        # Temporary dict to track assignments only for THIS batch before sending
        batch_assignments: Dict[str, TaskAssignment] = {}
        # Keep track of miner UIDs we actually attempt to send to in this batch
        miners_sent_attempted_uids = []

        for miner_info in miners_for_batch:
            miner_uid = miner_info.uid
            # Basic check (already done in selection, but good for safety)
            if not miner_info.api_endpoint or not miner_info.api_endpoint.startswith(
                ("http://", "https://")
            ):
                logger.warning(
                    f"Batch {batch_num}: Miner {miner_uid} has invalid API endpoint ('{miner_info.api_endpoint}'). Skipping."
                )
                continue

            # Create unique task ID including batch number
            # Ensure validator UID is hex string
            self_uid_hex = (
                self.info.uid.hex()
                if isinstance(self.info.uid, bytes)
                else self.info.uid
            )
            task_id = f"task_{self._current_cycle}_{self_uid_hex}_{miner_uid}_b{batch_num}_{random.randint(1000,9999)}"

            try:
                # Create task data using the overridable method
                task_data = self._create_task_data(miner_uid)
                if task_data is None:  # Ensure task data was created
                    raise ValueError("_create_task_data returned None")
                # Assume TaskModel can take task_id and unpack task_data dict
                task = TaskModel(task_id=task_id, **task_data)
            except NotImplementedError:
                logger.error(
                    f"CRITICAL: _create_task_data not implemented by subclass for miner {miner_uid}! Cannot send task."
                )
                continue  # Skip this miner
            except Exception as e:
                logger.exception(
                    f"Batch {batch_num}: Failed to create task for miner {miner_uid}: {e}"
                )
                continue  # Skip this miner

            # Create TaskAssignment
            assignment = TaskAssignment(
                task_id=task_id,
                task_data=task_data,
                miner_uid=miner_uid,
                validator_uid=self_uid_hex,  # Use hex UID
                timestamp_sent=time.time(),
                expected_result_format={},  # TODO: Define actual expected format if needed
            )

            # --- State Updates Before Sending ---
            self.miner_is_busy.add(miner_uid)  # Mark as busy immediately
            self.tasks_sent[task_id] = assignment  # Add to overall tracking
            batch_assignments[task_id] = assignment  # Add to this batch's tracking
            miners_sent_attempted_uids.append(
                miner_uid
            )  # Track UID for result processing
            # ------------------------------------

            # Prepare the coroutine for sending
            tasks_to_send_coroutines.append(
                self._send_task_via_network_async(miner_info.api_endpoint, task)
            )
            logger.debug(
                f"Batch {batch_num}: Prepared task {task_id} for miner {miner_uid}."
            )

        # --- Send Tasks Concurrently ---
        if not tasks_to_send_coroutines:
            logger.warning(
                f"Batch {batch_num}: No valid tasks could be prepared for sending."
            )
            return {}  # Return empty dict if nothing was prepared

        logger.info(
            f"Batch {batch_num}: Sending {len(tasks_to_send_coroutines)} tasks concurrently..."
        )
        # Gather results (True for success, False/Exception for failure)
        send_results = await asyncio.gather(
            *tasks_to_send_coroutines, return_exceptions=True
        )

        # --- Process Send Results ---
        successful_sends_in_batch = 0
        failed_assignment_keys_in_batch = []

        # Iterate through results, matching them back to miners sent in this batch
        for i, send_result in enumerate(send_results):
            # Ensure index is valid
            if i >= len(miners_sent_attempted_uids):
                logger.error(
                    f"Batch {batch_num}: Result index {i} mismatch with attempted miners."
                )
                continue

            miner_uid_sent = miners_sent_attempted_uids[i]
            # Find the corresponding task_id in this batch
            task_id_for_miner = None
            for tid, assign in batch_assignments.items():
                if assign.miner_uid == miner_uid_sent:
                    task_id_for_miner = tid
                    break

            if not task_id_for_miner:
                logger.error(
                    f"Batch {batch_num}: Could not find assignment for miner {miner_uid_sent} in this batch's tracking."
                )
                continue

            # Check if sending was successful
            if isinstance(send_result, bool) and send_result:
                successful_sends_in_batch += 1
                logger.debug(
                    f"Batch {batch_num}: Successfully sent task {task_id_for_miner} to miner {miner_uid_sent}."
                )
            else:
                # Sending failed
                logger.warning(
                    f"Batch {batch_num}: Failed sending task {task_id_for_miner} to miner {miner_uid_sent}. Error: {send_result}"
                )
                # --- Revert State Updates for Failed Send ---
                self.miner_is_busy.discard(miner_uid_sent)  # Mark as not busy anymore
                if task_id_for_miner in self.tasks_sent:
                    del self.tasks_sent[
                        task_id_for_miner
                    ]  # Remove from overall tracking
                # Mark for removal from the batch's successful assignments
                failed_assignment_keys_in_batch.append(task_id_for_miner)
                # -------------------------------------------

        # Remove failed assignments from the dictionary to be returned
        for task_id_to_remove in failed_assignment_keys_in_batch:
            if task_id_to_remove in batch_assignments:
                del batch_assignments[task_id_to_remove]

        logger.info(
            f"Batch {batch_num}: Sending attempt finished. Successful sends in this batch: {successful_sends_in_batch}/{len(tasks_to_send_coroutines)}."
        )

        # Return only the assignments for tasks successfully sent in this batch
        return batch_assignments

    # --- Phương thức chấm điểm lô mới ---
    # def _score_batch_results(self, tasks_in_batch: Dict[str, TaskAssignment]): # Commented out older version
    #     """
    #     Chấm điểm các kết quả trong buffer tương ứng với các task trong lô này.
    #     Gán điểm 0 cho các task không có kết quả trong buffer (timeout).
    #     Cập nhật self.cycle_scores và giải phóng miner khỏi self.miner_is_busy.
    #     Xóa task đã xử lý khỏi self.tasks_sent.
    #     """
    #     ...

    #     # --- Thêm phương thức này vào class ValidatorNode ---

    # def _score_individual_result(self, task_data: Any, result_data: Any) -> float: # Commented out older version
    #     """
    #     Placeholder cho logic chấm điểm của Subnet cụ thể.
    #     Phương thức này BẮT BUỘC phải được override bởi lớp Validator kế thừa.
    #     """
    #     ...

    #     # --- Add this scoring method specific to mini-batches ---

    async def _score_current_batch(self, batch_assignments: Dict[str, TaskAssignment]):
        """
        Scores results for a completed mini-batch, handling timeouts.

        Retrieves results from the buffer, calls the subnet-specific
        `_score_individual_result` logic, appends scores (including 0.0 for timeouts)
        to `self.cycle_scores`, releases miners from the busy set, and removes
        processed tasks from `self.tasks_sent`.

        Args:
            batch_assignments: Dict {task_id: TaskAssignment} for the batch just finished.

        Raises:
            NotImplementedError: If `_score_individual_result` is not implemented by the subclass.
            Exception: If errors occur during the scoring logic itself.
        """
        batch_num_str = (
            ""  # Try to extract batch number for logging if available in task_id
        )
        if batch_assignments:
            first_task_id = next(iter(batch_assignments.keys()))
            parts = first_task_id.split("_b")
            if len(parts) > 1:
                num_part = parts[-1].split("_")[0]
                if num_part.isdigit():
                    batch_num_str = f" (Batch ~{num_part})"

        logger.info(
            f"Scoring results for {len(batch_assignments)} tasks{batch_num_str}..."
        )
        scores_added_count = 0
        timeouts_count = 0

        # Atomically get and clear the current results buffer
        # NOTE: This assumes add_miner_result uses the same lock. If not, acquire lock here.
        # If add_miner_result is sync and called from API thread, this might be okay without async lock.
        # Let's add the lock for safety assuming potential concurrency.
        # This method itself runs synchronously within the main async run_cycle loop.
        # The lock is needed because add_miner_result (called by API) might run concurrently.
        async with self.results_buffer_lock:  # Use the sync version of the lock
            buffered_results_copy = self.results_buffer.copy()
            self.results_buffer.clear()
            logger.debug(
                f"Copied and cleared results buffer. Size was: {len(buffered_results_copy)}"
            )

        # Get validator UID (should be hex string already)
        self_uid_hex = (
            self.info.uid.hex() if isinstance(self.info.uid, bytes) else self.info.uid
        )

        # Iterate through the tasks EXPECTED in this batch
        for task_id, assignment in batch_assignments.items():
            miner_uid = assignment.miner_uid
            score = 0.0
            result_found = False

            # Check if a result for this task_id arrived in the buffer
            if task_id in buffered_results_copy:
                result = buffered_results_copy[task_id]
                result_found = True

                # Double-check miner UID (should be correct if add_miner_result checked)
                if result.miner_uid == miner_uid:
                    try:
                        # ===>>> CALL THE SUBNET-SPECIFIC SCORING LOGIC HERE <<<===
                        # This method MUST be overridden by the specific Validator subclass
                        # (e.g., Subnet1Validator needs to implement this or ensure its
                        # scoring logic is accessible via this call).
                        score = self._score_individual_result(
                            assignment.task_data, result.result_data
                        )
                        logger.info(
                            f"  Task {task_id}: Raw score calculated = {score:.4f} for Miner {miner_uid}"
                        )

                        # Clamp score
                        score = max(0.0, min(1.0, score))
                        scores_added_count += 1
                        logger.debug(
                            f"  Task {task_id}: Scored result from miner {miner_uid}. Score: {score:.4f}"
                        )

                    except NotImplementedError:
                        logger.error(
                            f"CRITICAL: Scoring logic '_score_individual_result' not implemented in {self.__class__.__name__} for task {task_id}! Assigning score 0."
                        )
                        score = 0.0  # Assign 0 if scoring is not implemented
                    except Exception as e:
                        logger.exception(
                            f"  Task {task_id}: Error scoring result from miner {miner_uid}: {e}. Assigning score 0."
                        )
                        score = 0.0  # Assign 0 on scoring error
                else:
                    # This case indicates a potential logic error in how results are buffered/matched
                    logger.error(
                        f"  Task {task_id}: Result in buffer from unexpected miner {result.miner_uid} (expected {miner_uid}). Assigning score 0."
                    )
                    score = 0.0
            else:
                # Timeout for this batch
                timeouts_count += 1
                score = 0.0  # Assign score 0 for timeout
                logger.warning(
                    f"  Task {task_id}: Timeout - No result received from miner {miner_uid} within batch wait time. Assigning score 0."
                )

            # Create ValidatorScore object
            val_score = ValidatorScore(
                task_id=task_id,
                miner_uid=miner_uid,
                validator_uid=self_uid_hex,
                score=score,
                timestamp=time.time(),  # Timestamp of scoring
            )

            # Append score to the main cycle accumulator
            # Use defaultdict initialized in __init__
            self.cycle_scores[task_id].append(val_score)

            # --- Release Miner and Task Tracking ---
            self.miner_is_busy.discard(miner_uid)  # Mark miner as available
            if task_id in self.tasks_sent:
                del self.tasks_sent[task_id]  # Remove from overall pending tasks
            # ---------------------------------------

        logger.info(
            f"Batch scoring complete{batch_num_str}. Scores added: {scores_added_count}. Timeouts (Score 0): {timeouts_count}."
        )

    # --- Add this placeholder scoring method (IMPORTANT) ---
    # This NEEDS to be overridden by Subnet1Validator
    def _score_individual_result(self, task_data: Any, result_data: Any) -> float:
        """
        (Placeholder/Needs Override) Calculates the score for a single miner result.

        *** This method MUST be implemented by the specific Validator subclass ***
        (e.g., Subnet1Validator) to contain the actual scoring logic based on the
        task and the received result (e.g., calling calculate_clip_score).

        Args:
            task_data (Any): Data originally sent in the task.
            result_data (Any): Data received from the miner.

        Returns:
            float: Score between 0.0 and 1.0.

        Raises:
            NotImplementedError: By default, if not overridden.
        """
        logger.error(
            f"CRITICAL: Validator {getattr(self, 'info', {}).get('uid', 'UNKNOWN')} is using the base "
            f"'_score_individual_result'. Subnet scoring logic is missing! Returning score 0.0."
        )
        # In a real scenario, either raise NotImplementedError or implement base logic
        raise NotImplementedError("Subclasses must implement _score_individual_result")
        # return 0.0 # Unreachable after raise

    # --- Tương tác với Aptos chain ---
    async def _get_current_slot(self) -> Optional[int]:
        """
        Lấy giá trị slot hiện tại dựa trên timestamp của block Aptos mới nhất.
        
        Returns:
            Optional[int]: Giá trị slot tương đương, None nếu có lỗi.
        """
        try:
            timestamp = await self._get_current_block_timestamp()
            if timestamp is None:
                return None
                
            # Tính slot giả lập dựa trên timestamp (1 slot = 1 giây)
            slot_length = self.settings.CONSENSUS_CYCLE_SLOT_LENGTH or 1  # seconds per slot
            estimated_slot = timestamp // slot_length
            
            return estimated_slot
        except Exception as e:
            logger.error(f"Lỗi khi tính toán giá trị slot hiện tại: {e}")
            return None

    async def wait_until_slot(self, target_slot: int):
        """
        Đợi cho đến khi slot hiện tại (tính từ timestamp) đạt đến hoặc vượt qua target_slot.
        
        Args:
            target_slot (int): Giá trị slot đích cần đợi.
        """
        if target_slot <= 0:
            logger.warning(
                f"wait_until_slot được gọi với giá trị target_slot không hợp lệ: {target_slot}"
            )
            return

        logger.debug(f"Đợi cho đến slot {target_slot}...")
        
        slot_length = self.settings.CONSENSUS_CYCLE_SLOT_LENGTH or 1  # seconds per slot
        target_timestamp = target_slot * slot_length
        
        current_time = int(time.time())
        if current_time >= target_timestamp:
            logger.info(f"Đã đạt hoặc vượt qua timestamp đích. Tiếp tục.")
            return
            
        # Đợi cho đến khi đạt được timestamp/slot đích
        while True:
            current_slot = await self._get_current_slot()
            if current_slot is None:
                logger.warning(
                    "Không lấy được giá trị slot hiện tại, thử lại sau 5 giây..."
                )
                await asyncio.sleep(5)
                continue

            if current_slot >= target_slot:
                logger.info(
                    f"Đã đạt slot đích {target_slot} (Hiện tại: {current_slot}). Tiếp tục."
                )
                break

            wait_interval = self.settings.CONSENSUS_SLOT_QUERY_INTERVAL_SECONDS
            logger.debug(
                f"Slot hiện tại: {current_slot}, Đích: {target_slot}. Đợi {wait_interval:.1f}s..."
            )
            await asyncio.sleep(wait_interval)
    
    def get_current_blockchain_slot(self) -> int:
        """Get current blockchain slot number based on timestamp"""
        epoch_start = 1735689600  # Jan 1, 2025 00:00:00 UTC
        current_time = int(time.time())
        slot_duration_seconds = self.slot_config.slot_duration_minutes * 60
        return (current_time - epoch_start) // slot_duration_seconds
    
    def get_slot_phase(self, slot_number: int) -> tuple[SlotPhase, int, int]:
        """
        Get current phase within a slot and time remaining
        Returns: (phase, minutes_into_slot, minutes_remaining_in_phase)
        """
        current_time = int(time.time())
        epoch_start = 1735689600
        slot_duration_seconds = self.slot_config.slot_duration_minutes * 60
        
        slot_start_time = epoch_start + (slot_number * slot_duration_seconds)
        minutes_into_slot = (current_time - slot_start_time) // 60
        
        boundaries = self.slot_config.get_phase_boundaries()
        
        for phase, (start_min, end_min) in boundaries.items():
            if start_min <= minutes_into_slot < end_min:
                minutes_remaining = end_min - minutes_into_slot
                return phase, minutes_into_slot, minutes_remaining
        
        # Default to task assignment if outside boundaries
        return SlotPhase.TASK_ASSIGNMENT, minutes_into_slot, 0
    
    async def handle_task_assignment_phase(self, slot: int, minutes_remaining: int):
        """Phase 1: Synchronized Cardano task assignment with cutoff coordination"""
        logger.info(f"📋 [V:{self.info.uid}] Synchronized Task Assignment - Slot {slot} ({minutes_remaining}min remaining)")
        
        # Register entry to task assignment phase
        await self.slot_coordinator.register_phase_entry(slot, SlotPhase.TASK_ASSIGNMENT)
        
        # Clean up old slot tracking and coordination files
        old_slots = [s for s in self.slot_tasks_sent if s < slot - 10]
        for old_slot in old_slots:
            self.slot_tasks_sent.discard(old_slot)
        old_scores = [s for s in self.slot_scored if s < slot - 10]
        for old_slot in old_scores:
            self.slot_scored.discard(old_slot)
        self.slot_coordinator.cleanup_old_coordination_files(slot)
        
        # SYNCHRONIZED TASK ASSIGNMENT: Only send if cutoff hasn't been reached
        current_phase, _, _ = self.slot_coordinator.get_slot_phase(slot)
        
        if current_phase == SlotPhase.TASK_ASSIGNMENT:
            # Check if we've already sent tasks for this slot
            if slot not in self.slot_tasks_sent:
                logger.info(f"🔄 [V:{self.info.uid}] NEW SLOT {slot} - First time, will send tasks")
                try:
                    # First time in this slot - update metagraph and send tasks
                    logger.info(f"🔄 [V:{self.info.uid}] First time in slot {slot} - updating metagraph...")
                    await self._update_metagraph()
                    logger.info(f"✅ [V:{self.info.uid}] Metagraph updated. Miners: {len(self.miners_info) if self.miners_info else 0}")
                    
                    # Select miners (Cardano style - deterministic selection)
                    selected_miners = self.cardano_select_miners(slot)
                    
                    if selected_miners:
                        logger.info(f"🎯 [V:{self.info.uid}] Selected {len(selected_miners)} miners: {[m.uid for m in selected_miners]}")
                        
                        # Send tasks immediately (Cardano pattern)
                        await self.cardano_send_tasks(slot, selected_miners)
                        
                        # Mark that we've sent tasks for this slot
                        self.slot_tasks_sent.add(slot)
                        
                    else:
                        logger.warning(f"⚠️ [V:{self.info.uid}] No miners available for assignment")
                        
                except Exception as e:
                    logger.error(f"❌ [V:{self.info.uid}] Task assignment error: {e}")
            else:
                logger.info(f"📋 [V:{self.info.uid}] SLOT {slot} already processed - monitoring only")
                # Continue monitoring during assignment phase - check for new miners or retry failed tasks
                try:
                    # Check if any miners finished and can take new tasks
                    if minutes_remaining > 5:  # Only in first part of assignment phase
                        available_miners = self.cardano_select_miners(slot)
                        busy_miners = len(self.miner_is_busy)
                        logger.debug(f"📊 [V:{self.info.uid}] Assignment status: {busy_miners} busy miners, {len(available_miners)} available")
                        
                        # Look for miners that failed initial task assignment
                        failed_miners = []
                        for miner in available_miners:
                            if miner.uid not in self.miner_is_busy:
                                # Check if this miner should have been assigned but wasn't
                                expected_task_id = f"slot_{slot}_{miner.uid}"
                                if expected_task_id not in self.tasks_sent:
                                    failed_miners.append(miner)
                        
                        if failed_miners:
                            logger.info(f"🔄 [V:{self.info.uid}] Retrying failed assignments for {len(failed_miners)} miners")
                            await self.cardano_send_tasks(slot, failed_miners)
                            
                except Exception as e:
                    logger.debug(f"Assignment monitoring error: {e}")
        
        # SYNCHRONIZED CUTOFF: Enforce task assignment deadline
        if minutes_remaining <= 1:  # Near end of assignment phase
            logger.info(f"🛑 [V:{self.info.uid}] Approaching task assignment cutoff")
            await self.slot_coordinator.enforce_task_assignment_cutoff(slot)
    
    def cardano_select_miners(self, slot: int) -> List[MinerInfo]:
        """Select miners using Cardano ModernTensor pattern - simple and effective"""
        logger.debug(f"🔍 [V:{self.info.uid}] Miners available: {len(self.miners_info) if self.miners_info else 0}")
        if self.miners_info:
            logger.debug(f"🔍 [V:{self.info.uid}] Miner UIDs: {list(self.miners_info.keys())}")
        
        if not self.miners_info:
            logger.warning(f"⚠️ [V:{self.info.uid}] No miners_info available!")
            return []
        
        # Get active miners (Cardano pattern)
        active_miners = [
            m for m in self.miners_info.values()
            if getattr(m, "status", STATUS_ACTIVE) == STATUS_ACTIVE and m.uid not in self.miner_is_busy
        ]
        
        if not active_miners:
            return []
        
        # Cardano uses simple round-robin or random selection
        num_to_select = min(
            getattr(self.settings, 'CONSENSUS_NUM_MINERS_TO_SELECT', 2),
            len(active_miners)
        )
        
        # Sort for deterministic selection
        sorted_miners = sorted(active_miners, key=lambda m: m.uid)
        
        # Simple selection based on slot (Cardano pattern)
        start_idx = slot % len(sorted_miners)
        selected = []
        
        for i in range(num_to_select):
            idx = (start_idx + i) % len(sorted_miners)
            selected.append(sorted_miners[idx])
        
        return selected
    
    async def cardano_send_tasks(self, slot: int, miners: List[MinerInfo]):
        """Send tasks using Cardano ModernTensor pattern - parallel like original SDK"""
        logger.info(f"🚀 [V:{self.info.uid}] Cardano sending tasks to {len(miners)} miners (parallel)")
        
        # First, check health of all miners
        logger.info(f"🔍 [V:{self.info.uid}] Checking health of {len(miners)} miners...")
        healthy_miners = []
        
        health_checks = []
        for miner in miners:
            health_checks.append(self._check_miner_health(miner.api_endpoint))
        
        health_results = await asyncio.gather(*health_checks, return_exceptions=True)
        
        for miner, is_healthy in zip(miners, health_results):
            if is_healthy is True:
                healthy_miners.append(miner)
                logger.info(f"✅ [V:{self.info.uid}] Miner {miner.uid} is healthy")
            else:
                logger.warning(f"⚠️ [V:{self.info.uid}] Miner {miner.uid} is not healthy - skipping task send")
        
        if not healthy_miners:
            logger.warning(f"❌ [V:{self.info.uid}] No healthy miners available for slot {slot}")
            return
        
        logger.info(f"🎯 [V:{self.info.uid}] Sending tasks to {len(healthy_miners)}/{len(miners)} healthy miners")
        
        # Prepare all tasks first (Cardano pattern)
        task_assignments = []
        task_sends = []
        
        for miner in healthy_miners:
            try:
                # Simple task ID (Cardano pattern)
                task_id = f"slot_{slot}_{miner.uid}"
                
                # Create task (Cardano style - simple prompt)
                task_data = self.cardano_create_task(slot, miner.uid)
                
                # Create assignment
                assignment = TaskAssignment(
                    task_id=task_id,
                    task_data=task_data,
                    miner_uid=miner.uid,
                    validator_uid=self.info.uid,
                    timestamp_sent=time.time(),
                    expected_result_format={},
                )
                
                # Store assignment for tracking
                task_assignments.append((task_id, assignment, miner))
                
                # Prepare task for sending
                from mt_aptos.network.server import TaskModel
                task = TaskModel(task_id=task_id, **task_data)
                
                # Add to parallel send list
                task_sends.append(self._cardano_send_single_task(task_id, assignment, miner, task))
                
            except Exception as e:
                logger.error(f"❌ [V:{self.info.uid}] Cardano task prep error for {miner.uid}: {e}")
        
        # Send all tasks in parallel (Cardano ModernTensor SDK pattern)
        if task_sends:
            logger.info(f"📡 [V:{self.info.uid}] Sending {len(task_sends)} tasks in parallel...")
            results = await asyncio.gather(*task_sends, return_exceptions=True)
            
            # Process results
            success_count = 0
            for i, (result, (task_id, assignment, miner)) in enumerate(zip(results, task_assignments)):
                if result is True:
                    # Success - store assignment and mark miner busy
                    self.tasks_sent[task_id] = assignment
                    self.miner_is_busy.add(miner.uid)
                    success_count += 1
                    logger.info(f"✅ [V:{self.info.uid}] Cardano task sent to {miner.uid}")
                else:
                    # Failed - log error
                    logger.warning(f"❌ [V:{self.info.uid}] Failed Cardano task to {miner.uid}: {result if isinstance(result, Exception) else 'Unknown error'}")
            
            logger.info(f"🎯 [V:{self.info.uid}] Cardano parallel send complete: {success_count}/{len(task_sends)} successful")
    
    async def _cardano_send_single_task(self, task_id: str, assignment: TaskAssignment, miner: MinerInfo, task) -> bool:
        """Send a single task to miner (used in parallel sends)"""
        try:
            logger.debug(f"🚀 Sending task {task_id} to miner {miner.uid} at {miner.api_endpoint}")
            success = await self._send_task_via_network_async(miner.api_endpoint, task)
            if not success:
                logger.warning(f"❌ Task send returned False for {miner.uid}")
            return success
        except Exception as e:
            logger.error(f"❌ Task send exception to {miner.uid}: {e}")
            import traceback
            logger.error(f"Task send traceback: {traceback.format_exc()}")
            return False
    
    def cardano_create_task(self, slot: int, miner_uid: str) -> Dict[str, Any]:
        """Create task using Cardano ModernTensor pattern - simple and consistent"""
        # Deadline as ISO string (TaskModel requirement)
        deadline_timestamp = time.time() + (self.slot_config.task_execution_minutes * 60)
        deadline_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(deadline_timestamp))
        
        # TaskModel compatible format
        task_data = {
            "description": f"Generate a beautiful landscape image for slot {slot}",  # Required field
            "deadline": deadline_str,  # String format required
            "priority": 3,  # Medium priority
            "validator_endpoint": getattr(self.info, 'api_endpoint', 'http://localhost:8001'),
            "task_data": {  # Actual task payload
                "type": "image_generation",
                "prompt": f"A beautiful landscape for slot {slot}",
                "slot": slot,
                "miner_uid": miner_uid,
                "expected_format": "base64_image"
            }
        }
        
        return task_data
    
    def select_miners_for_slot(self, slot: int) -> List[MinerInfo]:
        """
        Deterministic miner selection based on slot number.
        All validators should select the same miners for the same slot.
        """
        if not self.miners_info:
            return []
        
        # Get active miners
        active_miners = [
            m for m in self.miners_info.values()
            if getattr(m, "status", STATUS_ACTIVE) == STATUS_ACTIVE
        ]
        
        if not active_miners:
            return []
        
        # Deterministic selection based on slot number
        # Use slot as seed for consistent selection across validators
        import random
        slot_random = random.Random(slot)  # Deterministic seed
        
        # Select miners based on weighted probability
        num_to_select = min(
            self.settings.CONSENSUS_NUM_MINERS_TO_SELECT,
            len(active_miners)
        )
        
        # Sort miners by UID for deterministic ordering
        sorted_miners = sorted(active_miners, key=lambda m: m.uid)
        
        # Select miners using slot-based deterministic shuffle
        slot_random.shuffle(sorted_miners)
        selected = sorted_miners[:num_to_select]
        
        return selected
    
    async def assign_tasks_for_slot(self, slot: int, miners: List[MinerInfo]):
        """
        Assign deterministic tasks to miners for this slot.
        Tasks are consistent across all validators for the same slot.
        """
        logger.info(f"🎯 [V:{self.info.uid}] Assigning tasks for slot {slot} to {len(miners)} miners")
        
        for miner in miners:
            try:
                # Create deterministic task ID based on slot and miner
                task_id = f"slot_{slot}_{miner.uid}_{self.info.uid}"
                
                # Create task data (this should be deterministic too)
                task_data = self.create_slot_task_data(slot, miner.uid)
                
                # Create task assignment
                assignment = TaskAssignment(
                    task_id=task_id,
                    task_data=task_data,
                    miner_uid=miner.uid,
                    validator_uid=self.info.uid,
                    timestamp_sent=time.time(),
                    expected_result_format={},
                )
                
                # Add to tasks sent
                self.tasks_sent[task_id] = assignment
                
                # Send task to miner
                from mt_aptos.network.server import TaskModel
                task = TaskModel(task_id=task_id, **task_data)
                
                success = await self._send_task_via_network_async(miner.api_endpoint, task)
                
                if success:
                    logger.info(f"✅ [V:{self.info.uid}] Task {task_id} sent to miner {miner.uid}")
                    # Mark miner as busy
                    self.miner_is_busy.add(miner.uid)
                else:
                    logger.warning(f"❌ [V:{self.info.uid}] Failed to send task {task_id} to miner {miner.uid}")
                    # Remove from tasks sent
                    del self.tasks_sent[task_id]
                    
            except Exception as e:
                logger.error(f"❌ [V:{self.info.uid}] Error assigning task to miner {miner.uid}: {e}")
    
    def create_slot_task_data(self, slot: int, miner_uid: str) -> Dict[str, Any]:
        """
        Create deterministic task data for a slot and miner.
        This ensures all validators create the same task for the same slot/miner combination.
        """
        # Use slot number to create deterministic task parameters
        import hashlib
        
        # Create deterministic seed from slot and miner
        seed_string = f"slot_{slot}_miner_{miner_uid}"
        seed_hash = hashlib.md5(seed_string.encode()).hexdigest()
        
        # Create task based on subnet type (override in subnet-specific validators)
        task_data = {
            "type": "image_generation",
            "prompt": f"Generate an image for slot {slot} with seed {seed_hash[:8]}",
            "seed": seed_hash,
            "slot": slot,
            "deadline": time.time() + (self.slot_config.task_execution_minutes * 60),
            "expected_format": "base64_image"
        }
        
        return task_data
    
    async def handle_task_execution_phase(self, slot: int, minutes_remaining: int):
        """Phase 2: Monitor task execution and wait for results"""
        logger.info(f"⚙️ [V:{self.info.uid}] Synchronized Task Execution Phase - Slot {slot} ({minutes_remaining}min remaining)")
        
        # Register entry to task execution phase
        await self.slot_coordinator.register_phase_entry(slot, SlotPhase.TASK_EXECUTION)
        
        # Monitor task progress continuously during this phase
        # Results are received via API endpoints, so we wait and monitor
        logger.info(f"⏳ [V:{self.info.uid}] Waiting for task results during execution phase...")
        
        # Check results periodically during execution phase
        wait_interval = min(30, minutes_remaining * 60 // 2)  # Check at least twice during phase
        if wait_interval > 0:
            await asyncio.sleep(wait_interval)
            
        # Log received results so far
        slot_results = [task_id for task_id in self.tasks_sent.keys() if task_id.startswith(f"slot_{slot}_")]
        received_results = len([r for r in self.results_received.values() if any(task_id.startswith(f"slot_{slot}_") for task_id in r)])
        logger.info(f"📊 [V:{self.info.uid}] Task execution progress: {received_results}/{len(slot_results)} results received")
    
    async def handle_consensus_phase(self, slot: int, minutes_remaining: int):
        """Phase 3: Synchronized consensus with coordinator"""
        logger.info(f"🤝 [V:{self.info.uid}] Synchronized Consensus Phase - Slot {slot} ({minutes_remaining}min remaining)")
        
        # Register entry to consensus phase
        await self.slot_coordinator.register_phase_entry(slot, SlotPhase.CONSENSUS_SCORING)
        
        # Check if we've already scored for this slot
        if slot not in self.slot_scored:
            try:
                # First time in consensus phase - score immediately
                logger.info(f"📊 [V:{self.info.uid}] Starting local scoring for slot {slot}")
                
                # Score all received results locally
                await self.cardano_score_results(slot)
                
                # Mark scoring as complete
                self.slot_scored.add(slot)
                logger.info(f"✅ [V:{self.info.uid}] Local scoring completed for slot {slot}")
                
            except Exception as e:
                logger.error(f"❌ [V:{self.info.uid}] Error in local scoring: {e}")
        
        # SYNCHRONIZED CONSENSUS: Coordinate with other validators
        try:
            # Collect local scores
            local_scores = await self._collect_local_scores_for_consensus(slot)
            
            if local_scores:
                logger.info(f"📊 [V:{self.info.uid}] Collected {len(local_scores)} local scores for consensus")
                
                # Use coordinator for synchronized consensus round
                consensus_scores = await self.slot_coordinator.coordinate_consensus_round(slot, local_scores)
                
                if consensus_scores:
                    logger.info(f"✅ [V:{self.info.uid}] Synchronized consensus completed: {len(consensus_scores)} final scores")
                    # Store consensus results for metagraph update
                    self.slot_consensus_results[slot] = consensus_scores
                else:
                    logger.warning(f"⚠️ [V:{self.info.uid}] No consensus scores received")
            else:
                logger.warning(f"⚠️ [V:{self.info.uid}] No local scores available for consensus")
                
        except Exception as e:
            logger.error(f"❌ [V:{self.info.uid}] Error in synchronized consensus: {e}")
    
    async def cardano_score_results(self, slot: int):
        """Score results using Cardano ModernTensor pattern"""
        logger.info(f"📊 [V:{self.info.uid}] Cardano scoring pattern for slot {slot}")
        
        scored_tasks = []
        
        # Process all tasks for this slot
        for task_id, assignment in list(self.tasks_sent.items()):
            if task_id.startswith(f"slot_{slot}_"):
                miner_uid = assignment.miner_uid
                
                # Check if we have result
                if task_id in self.results_buffer:
                    try:
                        result = self.results_buffer[task_id]
                        
                        # Score using subnet-specific logic (CLIP scoring for Subnet1)
                        score = self._score_individual_result(assignment.task_data, result.result_data)
                        
                        # Create score record (Cardano pattern)
                        score_record = {
                            "task_id": task_id,
                            "miner_uid": miner_uid,
                            "score": score,
                            "validator_uid": self.info.uid,
                            "slot": slot,
                            "timestamp": time.time()
                        }
                        
                        scored_tasks.append(score_record)
                        logger.info(f"✅ [V:{self.info.uid}] Scored {miner_uid}: {score:.4f}")
                        
                    except Exception as e:
                        logger.error(f"❌ Scoring error for {task_id}: {e}")
                        # Zero score on error (Cardano pattern)
                        score_record = {
                            "task_id": task_id,
                            "miner_uid": miner_uid,
                            "score": 0.0,
                            "validator_uid": self.info.uid,
                            "slot": slot,
                            "timestamp": time.time()
                        }
                        scored_tasks.append(score_record)
                else:
                    # No result = timeout score (Cardano pattern)
                    logger.warning(f"⏰ [V:{self.info.uid}] Timeout for {miner_uid}")
                    score_record = {
                        "task_id": task_id,
                        "miner_uid": miner_uid,
                        "score": 0.0,
                        "validator_uid": self.info.uid,
                        "slot": slot,
                        "timestamp": time.time()
                    }
                    scored_tasks.append(score_record)
                
                # Release miner (Cardano pattern)
                self.miner_is_busy.discard(miner_uid)
                
                # Clean up task
                del self.tasks_sent[task_id]
                if task_id in self.results_buffer:
                    del self.results_buffer[task_id]
        
        # Store scores for this slot
        self.slot_scores = {slot: scored_tasks}
        logger.info(f"📊 [V:{self.info.uid}] Cardano scoring complete: {len(scored_tasks)} tasks")
    
    def cardano_calculate_score(self, task_data: Dict, result_data: Dict) -> float:
        """
        Calculate score using Cardano ModernTensor pattern.
        Real scoring based on task completion and result quality.
        """
        try:
            # Check if result exists and is valid
            if not result_data:
                logger.warning("No result data provided for scoring")
                return 0.0
            
            # Base score for completing the task
            base_score = 0.1  # 10% for just submitting
            
            # Check result format and content
            if isinstance(result_data, dict):
                score = base_score
                
                # Score based on result completeness
                if "result" in result_data:
                    score += 0.3  # 30% for having result field
                    
                    result_content = result_data["result"]
                    if result_content and str(result_content).strip():
                        score += 0.3  # 30% for non-empty result
                        
                        # Score based on result length/quality
                        result_str = str(result_content)
                        if len(result_str) > 10:  # Reasonable length
                            score += 0.2  # 20% for substantial result
                        
                        # Check if it looks like image data (base64 or image reference)
                        if any(keyword in result_str.lower() for keyword in ['base64', 'image', 'png', 'jpg', 'jpeg']):
                            score += 0.1  # 10% bonus for image-related content
                
                # Check timestamp (recent submissions get bonus)
                if "timestamp" in result_data:
                    try:
                        result_time = float(result_data["timestamp"])
                        task_time = task_data.get("timestamp", time.time())
                        response_time = result_time - task_time
                        
                        if response_time < 30:  # Fast response (under 30s)
                            score += 0.1  # 10% speed bonus
                    except (ValueError, TypeError):
                        pass  # Ignore timestamp parsing errors
                
                # Ensure score is within valid range
                final_score = max(0.0, min(1.0, score))
                
                logger.info(f"📊 Calculated real score: {final_score:.3f} for result type: {type(result_data).__name__}")
                return final_score
            
            else:
                # Non-dict results get lower scores but not zero
                if result_data:
                    result_str = str(result_data).strip()
                    if result_str and result_str != "null" and result_str != "None":
                        score = base_score + 0.2  # 30% total for simple non-empty result
                        logger.info(f"📊 Calculated score for simple result: {score:.3f}")
                        return score
                
                logger.warning("Invalid or empty result data")
                return 0.0
            
        except Exception as e:
            logger.error(f"❌ Score calculation error: {e}")
            return 0.0
    
    async def cardano_broadcast_scores(self, slot: int):
        """Broadcast scores using Cardano ModernTensor P2P pattern"""
        if slot not in self.slot_scores or not self.slot_scores[slot]:
            logger.warning(f"⚠️ [V:{self.info.uid}] No scores to broadcast for slot {slot}")
            return
        
        try:
            # Get active validators
            active_validators = await self._get_active_validators()
            
            if len(active_validators) <= 1:  # Only self
                logger.info(f"📡 [V:{self.info.uid}] Single validator - no broadcast needed")
                return
            
            # Prepare Cardano-style broadcast payload
            broadcast_payload = {
                "type": "validator_scores",
                "slot": slot,
                "validator_uid": self.info.uid,
                "scores": self.slot_scores[slot],
                "timestamp": time.time()
            }
            
            logger.info(f"📡 [V:{self.info.uid}] Broadcasting {len(self.slot_scores[slot])} scores to {len(active_validators)-1} validators")
            
            # Send to all other validators (Cardano P2P pattern)
            broadcast_tasks = []
            for validator in active_validators:
                if validator.uid != self.info.uid:
                    broadcast_tasks.append(
                        self.cardano_send_scores(validator, broadcast_payload)
                    )
            
            if broadcast_tasks:
                results = await asyncio.gather(*broadcast_tasks, return_exceptions=True)
                success_count = sum(1 for r in results if r is True)
                logger.info(f"📡 [V:{self.info.uid}] Cardano broadcast: {success_count}/{len(broadcast_tasks)} successful")
            
        except Exception as e:
            logger.error(f"❌ [V:{self.info.uid}] Cardano broadcast error: {e}")
    
    async def cardano_send_scores(self, validator: ValidatorInfo, payload: Dict) -> bool:
        """Send scores to validator using Cardano pattern"""
        try:
            if not validator.api_endpoint:
                return False
            
            url = f"{validator.api_endpoint}/v1/consensus/receive-scores"
            response = await self.http_client.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return True
            
        except Exception as e:
            logger.debug(f"Failed to send scores to {validator.uid}: {e}")
            return False
    
    async def cardano_finalize_consensus(self, slot: int):
        """Finalize consensus using Cardano ModernTensor aggregation"""
        logger.info(f"🎯 [V:{self.info.uid}] Cardano consensus finalization for slot {slot}")
        
        try:
            # Collect all scores (own + received from other validators)
            all_validator_scores = defaultdict(list)  # miner_uid -> list of scores
            
            # Add our own scores
            if slot in self.slot_scores:
                for score_record in self.slot_scores[slot]:
                    miner_uid = score_record["miner_uid"]
                    score = score_record["score"]
                    all_validator_scores[miner_uid].append(score)
            
            # Add scores from other validators (received via P2P)
            if slot in self.received_validator_scores:
                for validator_uid, scores_dict in self.received_validator_scores[slot].items():
                    for score_record in scores_dict.values():
                        if isinstance(score_record, dict):
                            miner_uid = score_record.get("miner_uid")
                            score = score_record.get("score", 0.0)
                            if miner_uid:
                                all_validator_scores[miner_uid].append(score)
            
            # Calculate final consensus scores (Cardano aggregation)
            final_scores = {}
            for miner_uid, score_list in all_validator_scores.items():
                if score_list:
                    # Cardano uses median or weighted average
                    consensus_score = sum(score_list) / len(score_list)  # Average
                    final_scores[miner_uid] = consensus_score
                    
                    logger.info(f"🎯 [V:{self.info.uid}] Final: {miner_uid} = {consensus_score:.4f} (from {len(score_list)} validators)")
            
            # Store final results (Cardano pattern)
            self.slot_consensus_results[slot] = final_scores
            
            logger.info(f"✅ [V:{self.info.uid}] Cardano consensus complete: {len(final_scores)} miners scored")
            
        except Exception as e:
            logger.error(f"❌ [V:{self.info.uid}] Cardano consensus error: {e}")
    
    def score_slot_results(self, slot: int):
        """Score all results received for this slot"""
        logger.info(f"📊 [V:{self.info.uid}] Scoring results for slot {slot}")
        
        slot_task_count = 0
        scored_count = 0
        
        # Score tasks for this slot
        for task_id, assignment in self.tasks_sent.items():
            if task_id.startswith(f"slot_{slot}_"):
                slot_task_count += 1
                
                # Check if we have results for this task
                if task_id in self.results_buffer:
                    try:
                        result = self.results_buffer[task_id]
                        score = self._score_individual_result(assignment.task_data, result.result_data)
                        
                        # Create validator score
                        validator_score = ValidatorScore(
                            task_id=task_id,
                            miner_uid=assignment.miner_uid,
                            score=score,
                            validator_uid=self.info.uid,
                            timestamp=time.time()
                        )
                        
                        # Add to validator scores for this slot
                        self.validator_scores[slot].append(validator_score)
                        scored_count += 1
                        
                        logger.debug(f"📊 Scored task {task_id}: {score}")
                        
                        # Release miner
                        self.miner_is_busy.discard(assignment.miner_uid)
                        
                    except Exception as e:
                        logger.error(f"❌ Error scoring task {task_id}: {e}")
                        # Give 0 score on error
                        validator_score = ValidatorScore(
                            task_id=task_id,
                            miner_uid=assignment.miner_uid,
                            score=0.0,
                            validator_uid=self.info.uid,
                            timestamp=time.time()
                        )
                        self.validator_scores[slot].append(validator_score)
                        self.miner_is_busy.discard(assignment.miner_uid)
                else:
                    # No result received - timeout score
                    logger.warning(f"⏰ No result received for task {task_id} - timeout")
                    validator_score = ValidatorScore(
                        task_id=task_id,
                        miner_uid=assignment.miner_uid,
                        score=0.0,
                        validator_uid=self.info.uid,
                        timestamp=time.time()
                    )
                    self.validator_scores[slot].append(validator_score)
                    self.miner_is_busy.discard(assignment.miner_uid)
        
        logger.info(f"📊 [V:{self.info.uid}] Slot {slot} scoring complete: {scored_count}/{slot_task_count} tasks scored")
    
    def prepare_slot_scores_for_broadcast(self, slot: int) -> List[ValidatorScore]:
        """Prepare scores for this slot to broadcast to other validators"""
        if slot not in self.validator_scores:
            return []
        
        slot_scores = self.validator_scores[slot]
        logger.info(f"📡 [V:{self.info.uid}] Prepared {len(slot_scores)} scores for broadcast")
        return slot_scores
    
    async def broadcast_slot_scores(self, slot: int, scores: List[ValidatorScore]):
        """Broadcast scores for this slot to other validators"""
        try:
            # Get active validators
            active_validators = await self._get_active_validators()
            
            if not active_validators:
                logger.warning(f"⚠️ No active validators found for score broadcast")
                return
            
            logger.info(f"📡 [V:{self.info.uid}] Broadcasting slot {slot} scores to {len(active_validators)} validators")
            
            # Prepare broadcast data
            broadcast_data = {
                "slot": slot,
                "validator_uid": self.info.uid,
                "scores": [
                    {
                        "task_id": score.task_id,
                        "miner_uid": score.miner_uid,
                        "score": score.score,
                        "timestamp": score.timestamp
                    }
                    for score in scores
                ]
            }
            
            # Send to all other validators
            broadcast_tasks = []
            for validator in active_validators:
                if validator.uid != self.info.uid:  # Don't send to self
                    broadcast_tasks.append(
                        self.send_scores_to_validator(validator, broadcast_data)
                    )
            
            if broadcast_tasks:
                results = await asyncio.gather(*broadcast_tasks, return_exceptions=True)
                success_count = sum(1 for r in results if r is True)
                logger.info(f"📡 [V:{self.info.uid}] Score broadcast results: {success_count}/{len(broadcast_tasks)} successful")
            
        except Exception as e:
            logger.error(f"❌ [V:{self.info.uid}] Error broadcasting slot scores: {e}")
    
    async def send_scores_to_validator(self, validator: ValidatorInfo, broadcast_data: Dict) -> bool:
        """Send scores to a specific validator"""
        try:
            if not validator.api_endpoint:
                return False
            
            url = f"{validator.api_endpoint}/receive-scores"
            response = await self.http_client.post(url, json=broadcast_data, timeout=10)
            response.raise_for_status()
            return True
            
        except Exception as e:
            logger.debug(f"Failed to send scores to {validator.uid}: {e}")
            return False
    
    async def finalize_slot_consensus(self, slot: int) -> Dict[str, float]:
        """
        Finalize consensus for the slot by aggregating scores from all validators.
        Similar to Cardano ModernTensor's consensus mechanism.
        """
        logger.info(f"🎯 [V:{self.info.uid}] Finalizing consensus for slot {slot}")
        
        try:
            # Collect all scores for this slot from all validators
            all_scores = defaultdict(list)  # task_id -> list of scores from different validators
            
            # Add our own scores
            if slot in self.validator_scores:
                for score in self.validator_scores[slot]:
                    all_scores[score.task_id].append(score.score)
            
            # Add scores from other validators (received via P2P)
            if slot in self.received_validator_scores:
                for validator_uid, validator_slot_scores in self.received_validator_scores[slot].items():
                    for task_id, score_obj in validator_slot_scores.items():
                        all_scores[task_id].append(score_obj.score)
            
            # Calculate consensus scores (average across validators)
            consensus_scores = {}
            for task_id, score_list in all_scores.items():
                if score_list:
                    # Use median or average for consensus
                    consensus_score = sum(score_list) / len(score_list)
                    consensus_scores[task_id] = consensus_score
                    logger.debug(f"🎯 Task {task_id}: consensus score {consensus_score:.4f} from {len(score_list)} validators")
            
            logger.info(f"✅ [V:{self.info.uid}] Slot {slot} consensus: {len(consensus_scores)} tasks finalized")
            return consensus_scores
            
        except Exception as e:
            logger.error(f"❌ [V:{self.info.uid}] Error finalizing slot consensus: {e}")
            return {}
    
    async def handle_metagraph_update_phase(self, slot: int, minutes_remaining: int):
        """Phase 4: Synchronized metagraph update and blockchain submission"""
        logger.info(f"📊 [V:{self.info.uid}] Synchronized Metagraph Update Phase - Slot {slot} ({minutes_remaining}min remaining)")
        
        # Register entry to metagraph update phase
        await self.slot_coordinator.register_phase_entry(slot, SlotPhase.METAGRAPH_UPDATE)
        
        # SYNCHRONIZED METAGRAPH UPDATE: Wait for all validators to be ready
        try:
            # Wait for other validators to enter metagraph update phase
            ready_validators = await self.slot_coordinator.wait_for_phase_consensus(slot, SlotPhase.METAGRAPH_UPDATE)
            
            if len(ready_validators) >= 2:
                logger.info(f"✅ [V:{self.info.uid}] Validators ready for synchronized update: {ready_validators}")
                
                # Use consensus scores from previous phase
                if slot in self.slot_consensus_results:
                    consensus_scores = self.slot_consensus_results[slot]
                    logger.info(f"📊 [V:{self.info.uid}] Applying consensus scores to metagraph: {len(consensus_scores)} scores")
                    
                    # Apply consensus scores to metagraph
                    await self._apply_consensus_scores_to_metagraph(slot, consensus_scores)
                    
                    # Submit to blockchain (synchronized)
                    logger.info(f"🔗 [V:{self.info.uid}] Submitting consensus scores to blockchain")
                    await self.cardano_submit_consensus_to_blockchain(consensus_scores)
                    
                    logger.info(f"✅ [V:{self.info.uid}] Synchronized metagraph update and blockchain submission completed")
                else:
                    logger.warning(f"⚠️ [V:{self.info.uid}] No consensus scores available, updating metagraph only")
                    await self._update_metagraph()
            else:
                logger.warning(f"⚠️ [V:{self.info.uid}] Insufficient validators for synchronized update, proceeding individually")
                await self._update_metagraph()
                
        except Exception as e:
            logger.error(f"❌ [V:{self.info.uid}] Error in synchronized metagraph update: {e}")
            # Fallback to individual update
            await self._update_metagraph()
        
        # Save slot state and cleanup
        self._save_current_cycle(slot)
        logger.info(f"✅ [V:{self.info.uid}] Slot {slot} completed and saved")

    async def _send_task_via_network_async(self, miner_endpoint: str, task: TaskModel) -> bool:
        """Send task via network asynchronously with circuit breaker and rate limiting"""
        start_time = time.time()
        
        # Check rate limit
        if not await self.rate_limiter.acquire():
            logger.warning(f"Rate limit exceeded for sending task to {miner_endpoint}")
            return False
            
        try:
            # Use circuit breaker for network call
            result = await self.circuit_breaker.execute(
                self._send_task_implementation,
                miner_endpoint,
                task
            )
            
            self.metrics.record_task_send(True)
            self.metrics.record_network_latency(time.time() - start_time)
            return result
            
        except Exception as e:
            self.metrics.record_task_send(False)
            self.metrics.record_error('network')
            raise

    async def _send_task_implementation(self, miner_endpoint: str, task: TaskModel) -> bool:
        """Actual implementation of task sending"""
        if not miner_endpoint or not miner_endpoint.startswith(("http://", "https://")):
            logger.warning(
                f"Invalid or missing API endpoint for miner: {miner_endpoint} in task {getattr(task, 'task_id', 'N/A')}"
            )
            return False

        target_url = f"{miner_endpoint}/receive-task"
        timeout = self.settings.HTTP_CLIENT_TIMEOUT or 30.0

        task_payload = (
            task.model_dump(mode="json")
            if hasattr(task, "model_dump")
            else task.dict()
        )

        logger.debug(f"Sending task {task.task_id} to {target_url} with timeout {timeout}s")
        response = await self.http_client.post(
            target_url, 
            json=task_payload,
            timeout=timeout
        )

        response.raise_for_status()
        return True

    async def send_task_and_track(self, miners: List[MinerInfo]):
        """
        Creates and sends tasks asynchronously to the selected list of miners,
        tracking the successfully sent tasks.

        Args:
            miners (List[MinerInfo]): The list of miners selected for tasking.

        Raises:
            NotImplementedError: If `_create_task_data` is not implemented.
            Exception: For unexpected errors during task creation or sending.
        """
        if not miners:
            logger.warning("send_task_and_track called with empty miner list.")
            self.tasks_sent = {}
            return

        logger.info(
            f"[V:{self.info.uid}] Attempting to send tasks to {len(miners)} selected miners..."
        )
        self.tasks_sent = {}  # Xóa danh sách task đã gửi của chu kỳ trước
        tasks_to_send = []
        # Tạm lưu assignment để chỉ thêm vào self.tasks_sent nếu gửi thành công
        task_assignments: Dict[str, TaskAssignment] = {}  # {miner_uid: TaskAssignment}

        for miner in miners:
            # Kiểm tra xem miner có endpoint hợp lệ không
            if not miner.api_endpoint or not miner.api_endpoint.startswith(
                ("http://", "https://")
            ):
                logger.warning(
                    f"Miner {miner.uid} has invalid or missing API endpoint ('{miner.api_endpoint}'). Skipping task assignment."
                )
                continue

            if miner.uid == self.info.uid:
                logger.debug(f"Skipping sending task to self (UID: {miner.uid}).")
                continue

            task_id = f"task_{self._current_cycle}_{self.info.uid}_{miner.uid}_{random.randint(1000,9999)}"
            try:
                task_data = self._create_task_data(miner.uid)
                # Giả sử TaskModel có thể tạo từ dict hoặc có constructor phù hợp
                # Cần đảm bảo TaskModel được import đúng
                task = TaskModel(task_id=task_id, **task_data)
            except Exception as e:
                logger.exception(f"Failed to create task for miner {miner.uid}: {e}")
                continue  # Bỏ qua miner này nếu không tạo được task

            # Tạo đối tượng TaskAssignment trước khi gửi
            assignment = TaskAssignment(
                task_id=task_id,
                task_data=task_data,
                miner_uid=miner.uid,  # Lưu UID dạng hex string
                validator_uid=self.info.uid,  # Lưu UID dạng hex string
                timestamp_sent=time.time(),
                expected_result_format={"output": "tensor", "loss": "float"},  # Ví dụ
            )
            task_assignments[miner.uid] = assignment  # Lưu tạm
            self.tasks_sent[task_id] = assignment
            logger.debug(
                f"Added task {task_id} to self.tasks_sent for miner {miner.uid}"
            )
            # Tạo coroutine để gửi task và thêm vào danh sách chờ
            tasks_to_send.append(
                self._send_task_via_network_async(miner.api_endpoint, task)
            )

        # --- Phần await asyncio.gather và xử lý results ---
        if not tasks_to_send:
            logger.warning("No valid tasks could be prepared for sending.")
            # Cập nhật lại tasks_sent nếu không có task nào được gửi đi? Có thể không cần.
            return  # Thoát nếu không có task nào để gửi

        logger.info(f"Sending {len(tasks_to_send)} tasks concurrently...")
        # Gửi đồng thời tất cả các task
        results = await asyncio.gather(*tasks_to_send, return_exceptions=True)

        successful_sends = 0
        # Xử lý kết quả gửi task
        # Lấy danh sách miners tương ứng với results (những miner thực sự được gửi task)
        miners_with_tasks = [m for m in miners if m.uid in task_assignments]
        for i, result in enumerate(results):
            # Lấy miner tương ứng với kết quả này
            if i < len(miners_with_tasks):
                miner = miners_with_tasks[i]
                assignment = task_assignments.get(miner.uid)
                assignment_check = self.tasks_sent.get(
                    f"task_{self._current_cycle}_{self.info.uid}_{miner.uid}"
                )  # Tìm lại task_id theo cấu trúc
                # Tìm task_id tương ứng với miner trong lần gửi này
                for tid, assign in self.tasks_sent.items():
                    # Kiểm tra cycle và miner uid để đảm bảo đúng task
                    if (
                        tid.startswith(f"task_{self._current_cycle}_")
                        and assign.miner_uid == miner.uid
                    ):
                        current_task_id = tid
                        break

                if current_task_id and isinstance(result, bool) and result:
                    # Gửi thành công, cập nhật last_selected_time
                    if miner.uid in self.miners_info:
                        self.miners_info[miner.uid].last_selected_time = (
                            self._current_cycle
                        )
                        logger.debug(
                            f"Updated last_selected_time for miner {miner.uid} to cycle {self._current_cycle}"
                        )
                    successful_sends += 1
                elif current_task_id:
                    # Gửi thất bại, xóa task khỏi self.tasks_sent? Hoặc đánh dấu là thất bại?
                    # Tạm thời chỉ log lỗi
                    logger.warning(
                        f"Failed to send task {current_task_id} to Miner {miner.uid}. Error/Result: {result}"
                    )
                    # Cân nhắc xóa khỏi tasks_sent để tránh validator chờ kết quả không bao giờ đến
                    # del self.tasks_sent[current_task_id]
                else:
                    logger.error(
                        f"Could not map result index {i} back to a sent task for miner {miner.uid}"
                    )

            else:
                logger.error(
                    f"Result index {i} out of bounds for miners_with_tasks list during task sending result processing."
                )

        logger.info(
            f"Finished sending tasks attempt. Successful sends: {successful_sends}/{len(tasks_to_send)}. Tasks currently tracked: {len(self.tasks_sent)}"
        )

    # --- Nhận và Chấm điểm Kết quả ---
    # --- 2. Sửa receive_results và bỏ _listen_for_results_async ---
    async def _listen_for_results_async(self, timeout: float):
        # <<<--- Bỏ hoàn toàn logic mock này ---<<<
        # Thay vào đó, hàm receive_results sẽ chỉ đơn giản là chờ một khoảng thời gian
        # trong khi kết quả được thêm vào self.results_received thông qua API endpoint.
        pass  # Removed method body as it was mock logic

    async def receive_results(self, timeout: Optional[float] = None):
        """
        Waits for miner results to arrive via the API endpoint.

        This method simply waits for the specified timeout duration.
        Actual results are received asynchronously by the API endpoint handler
        (`/v1/miner/submit_result`) which calls `add_miner_result` to buffer them.

        Args:
            timeout (Optional[float]): Duration in seconds to wait. If None, a default
                                     based on settings is used.
        """
        if timeout is None:
            # Giảm timeout xuống 30 giây để nhanh hơn
            timeout = 30  # Cố định 30 giây thay vì tính từ settings

        logger.info(
            f"[V:{self.info.uid}] Waiting {timeout:.1f}s for miner results via API endpoint..."
        )

        # Đơn giản là đợi hết timeout. Kết quả sẽ được tích lũy trong self.results_received.
        await asyncio.sleep(timeout)

        # Không cần xóa self.results_received ở đây, vì nó được tích lũy qua API.
        # Có thể xóa ở đầu chu kỳ mới hoặc trước khi bắt đầu chờ.
        # => Nên xóa ở đầu hàm này để chỉ xử lý kết quả của chu kỳ hiện tại
        # Tuy nhiên, nếu API nhận kết quả chậm, có thể kết quả chu kỳ trước bị xử lý ở chu kỳ sau?
        # => Cần cơ chế quản lý kết quả theo chu kỳ trong add_miner_result.

        # Chuyển kết quả từ buffer sang results_received để xử lý
        async with self.results_buffer_lock:
            # Chuyển tất cả kết quả từ buffer sang results_received
            for task_id, result in self.results_buffer.items():
                self.results_received[task_id].append(result)
            
            # Đếm tổng số kết quả
            received_count = sum(
                len(res_list) for res_list in self.results_received.values()
            )
            task_ids_with_results = list(self.results_received.keys())
            
            # Xóa buffer sau khi chuyển
            self.results_buffer.clear()

        logger.info(
            f"Finished waiting period. Total results accumulated: {received_count} for tasks: {task_ids_with_results}"
        )
        # Logic xử lý kết quả sẽ diễn ra ở bước score_miner_results

    # -----------------------------------------------------------

    # --- Cập nhật add_miner_result ---
    async def add_miner_result(self, result: MinerResult) -> bool:
        """
        (API Call Handler) Receives a miner result, performs basic validation,
        and stores it in the results buffer.

        Args:
            result (MinerResult): The result object submitted by the miner.

        Returns:
            bool: True if the result was valid and buffered, False otherwise.
        """
        if not result or not result.task_id or not result.miner_uid:
            logger.warning("API: Received invalid miner result (missing fields).")
            return False

        # Kiểm tra task ID có đang được mong đợi không (có trong tasks_sent)
        # Dùng get() để tránh lỗi nếu task_id không có (ví dụ đến quá muộn)
        assignment = self.tasks_sent.get(result.task_id)
        if not assignment:
            logger.warning(
                f"API: Received result for unknown/already processed/timed out task_id: {result.task_id} from miner {result.miner_uid}. Ignoring."
            )
            return False  # Từ chối nếu task ID không hợp lệ hoặc đã xử lý xong/timeout

        # Kiểm tra miner gửi có đúng không
        if assignment.miner_uid != result.miner_uid:
            logger.warning(
                f"API: Received result for task {result.task_id} from wrong miner {result.miner_uid}. Expected {assignment.miner_uid}. Ignoring."
            )
            return False

        # --- Lưu vào buffer ---
        async with self.results_buffer_lock:
            if result.task_id in self.results_buffer:
                logger.warning(
                    f"API: Overwriting previous buffered result for task {result.task_id}."
                )
            self.results_buffer[result.task_id] = result
            logger.info(
                f"API: Received and buffered result for task {result.task_id} from miner {result.miner_uid}."
            )
        # --------------------
        return True  # Báo thành công cho API

    # -----------------------------------------

    def score_miner_results(self):
        """Scores the miner results received during the waiting period."""
        # --- Xóa điểm cũ trước khi chấm ---
        self.validator_scores = {}
        # ---------------------------------

        # --- Lock khi đọc self.results_received ---
        # Tạo bản copy để tránh giữ lock quá lâu nếu scoring chậm
        results_to_score = {}
        # Dùng asyncio.run_coroutine_threadsafe nếu gọi từ thread khác?
        # Hoặc đảm bảo score_miner_results chạy trong cùng event loop
        # Giả sử chạy trong cùng event loop, chỉ cần lock async
        # async with self.results_received_lock: # Không cần lock nếu chỉ đọc sau khi wait xong
        #     results_to_score = self.results_received.copy()
        # => Không cần lock nếu receive_results đợi xong mới gọi score

        # Lấy bản copy để xử lý
        results_to_score = self.results_received.copy()
        # Reset lại dict nhận kết quả cho chu kỳ sau
        self.results_received = defaultdict(list)

        # Gọi hàm logic từ scoring.py (truyền bản copy và validator instance)
        self.validator_scores = score_results_logic(
            results_received=results_to_score,  # <<<--- Dùng bản copy  
            tasks_sent=self.tasks_sent,
            validator_uid=self.info.uid,
            validator_instance=self,  # Truyền self để gọi _score_individual_result
        )
        # Hàm score_results_logic sẽ gọi validator_instance._score_individual_result

    async def add_received_score(
        self, submitter_uid: str, cycle: int, scores: List[ValidatorScore]
    ):
        """Adds scores received from another validator to memory (async safe)."""
        # Logic này quản lý state nội bộ nên giữ lại trong Node
        # TODO: Thêm validation cho scores và submitter_uid
        async with self.received_scores_lock:
            if cycle not in self.received_validator_scores:
                # Chỉ lưu điểm cho chu kỳ hiện tại hoặc tương lai gần? Tránh lưu trữ quá nhiều.
                if cycle < self._current_cycle - 1:  # Ví dụ: chỉ giữ lại chu kỳ trước đó
                    logger.warning(
                        f"Received scores for outdated cycle {cycle} from {submitter_uid}. Ignoring."
                    )
                    return
                self.received_validator_scores[cycle] = defaultdict(dict)

            valid_scores_added = 0
            for score in scores:
                if not (
                    isinstance(score, ValidatorScore)
                    and isinstance(score.score, (int, float))
                    and 0.0 <= score.score <= 1.0
                    and isinstance(score.task_id, str)
                    and score.task_id
                    and isinstance(score.miner_uid, str)
                    and score.miner_uid
                    and score.validator_uid == submitter_uid
                ):  # Đảm bảo validator_uid khớp người gửi
                    logger.warning(
                        f"Ignoring invalid score object received from {submitter_uid}: {score}"
                    )
                    continue

                if score.task_id not in self.received_validator_scores[cycle]:
                    self.received_validator_scores[cycle][score.task_id] = {}
                # Ghi đè điểm nếu validator gửi lại?
                self.received_validator_scores[cycle][score.task_id][
                    score.validator_uid
                ] = score
                valid_scores_added += 1
                # else:
                #     logger.debug(f"Ignoring score for irrelevant task {score.task_id} from {submitter_uid}")

            logger.debug(
                f"Added {valid_scores_added} scores from {submitter_uid} for cycle {cycle}"
            )

    async def broadcast_scores(
        self, scores_to_broadcast: Dict[str, List[ValidatorScore]]
    ):
        """Broadcasts accumulated local scores to other active validators."""
        # Kiểm tra trạng thái validator (giữ nguyên)
        if self.info.status != STATUS_ACTIVE:
            logger.info(
                f"[V:{self.info.uid}] Skipping score broadcast (status: {self.info.status})."
            )
            return

        # Tính tổng số điểm sẽ gửi
        total_scores = sum(len(v) for v in scores_to_broadcast.values())
        logger.info(
            f"[V:{self.info.uid}] Broadcasting {total_scores} accumulated local scores for cycle {self._current_cycle}..."
        )

        # --- Chuẩn bị danh sách điểm phẳng để gửi ---
        # Hàm broadcast_scores_logic mong đợi một List[ValidatorScore]
        flat_scores_list: List[ValidatorScore] = []
        for task_scores_list in scores_to_broadcast.values():
            flat_scores_list.extend(task_scores_list)
        # ------------------------------------------

        if not flat_scores_list:
            logger.info("No accumulated local scores to broadcast for this cycle.")
            return

        # Gọi hàm logic P2P với danh sách điểm đã làm phẳng
        try:
            await broadcast_scores_logic(
                validator_node=self,  # Truyền self để lấy config, keys...
                cycle_scores_dict=self.cycle_scores,  # <<< Pass the original dict with the correct parameter name
            )
        except Exception as e:
            logger.exception(f"Error during broadcast_scores_logic: {e}")

    async def _get_active_validators(self) -> List[ValidatorInfo]:
        """Gets the list of currently active validators."""
        # TODO: Implement actual metagraph query or use a reliable cache.
        logger.debug("Getting active validators...")
        # Tạm thời lọc từ danh sách đã load, cần đảm bảo danh sách này được cập nhật thường xuyên
        active_vals = [
            v
            for v in self.validators_info.values()
            if v.api_endpoint and getattr(v, "status", STATUS_ACTIVE) == STATUS_ACTIVE
        ]
        logger.debug(f"Found {len(active_vals)} active validators with API endpoints.")
        return active_vals

    def _has_sufficient_scores(
        self, task_id: str, total_active_validators: int
    ) -> bool:
        """
        Checks if enough scores have been received for a specific task
        to proceed with consensus calculation.

        Args:
            task_id (str): The task ID to check scores for.
            total_active_validators (int): The total number of active validators.

        Returns:
            bool: True if sufficient scores are present, False otherwise.
        """
        # Logic này quản lý state nội bộ nên giữ lại trong Node
        current_cycle_scores = self.received_validator_scores.get(
            self._current_cycle, {}
        )
        task_scores = current_cycle_scores.get(task_id, {})
        received_validators_for_task = set(
            task_scores.keys()
        )  # Dùng set để tránh đếm trùng

        # Đếm cả điểm của chính mình (nếu đã chấm)
        # Kiểm tra xem điểm của chính mình đã có trong validator_scores chưa và validator_uid khớp không
        if task_id in self.validator_scores:
            # Kiểm tra xem có score nào trong list của task_id này là của mình không
            if any(
                s.validator_uid == self.info.uid for s in self.validator_scores[task_id]
            ):
                received_validators_for_task.add(
                    self.info.uid
                )  # Thêm UID của mình vào set

        received_count = len(received_validators_for_task)

        # Tính số lượng cần thiết
        min_validators = self.settings.CONSENSUS_MIN_VALIDATORS_FOR_CONSENSUS
        # Lấy tỉ lệ phần trăm yêu cầu từ settings (thêm nếu chưa có)
        # required_percentage = self.settings.get('CONSENSUS_REQUIRED_PERCENTAGE', 0.6) # Ví dụ
        required_percentage = 0.6  # Giả định 60%

        # Yêu cầu số lượng tối thiểu HOẶC phần trăm nhất định
        required_count_by_percentage = math.ceil(
            total_active_validators * required_percentage
        )
        required_count = max(min_validators, required_count_by_percentage)

        # Đảm bảo required_count không lớn hơn tổng số validator hoạt động
        required_count = min(required_count, total_active_validators)

        logger.debug(
            f"Scores check for task {task_id}: Received from {received_count}/{required_count} validators (Total active: {total_active_validators}, Min: {min_validators}, %: {required_percentage*100:.0f})"
        )
        return received_count >= required_count

    async def wait_for_consensus_scores(self, wait_timeout_seconds: float) -> bool:
        """
        Waits for a limited time to receive sufficient scores from peer validators.

        Args:
            wait_timeout_seconds (float): Maximum time to wait in seconds.

        Returns:
            bool: True if sufficient scores were received for all locally scored tasks
                  within the timeout, False otherwise.
        """
        logger.info(
            f"Waiting up to {wait_timeout_seconds:.1f}s for consensus scores for cycle {self._current_cycle}..."
        )
        start_wait = time.time()
        active_validators = await self._get_active_validators()
        total_active = len(active_validators)
        min_consensus_validators = self.settings.CONSENSUS_MIN_VALIDATORS_FOR_CONSENSUS

        if total_active == 0:
            logger.warning(
                "No active validators found. Skipping wait for consensus scores."
            )
            return False  # Không thể đồng thuận nếu không có ai hoạt động
        elif total_active < min_consensus_validators:
            logger.warning(
                f"Not enough active validators ({total_active}) for minimum consensus ({min_consensus_validators}). Proceeding with available data, but consensus might be weak."
            )
            # Vẫn trả về True để cho phép tính toán, nhưng log cảnh báo
            return True

        # Chỉ kiểm tra các task mà validator này đã chấm điểm (và có thể đã broadcast)
        tasks_to_check = set(self.validator_scores.keys())
        if not tasks_to_check:
            logger.info(
                "No local scores generated, skipping wait for consensus scores."
            )
            return True  # Không có gì để chờ

        logger.debug(f"Waiting for consensus on tasks: {list(tasks_to_check)}")
        processed_task_ids = set()  # Các task đã đủ điểm

        while time.time() - start_wait < wait_timeout_seconds:
            all_relevant_tasks_sufficient = True  # Kiểm tra cho các task cần check
            tasks_still_needing_check = tasks_to_check - processed_task_ids

            if not tasks_still_needing_check:
                logger.info("Sufficient scores received for all relevant tasks.")
                return True  # Đã đủ hết

            async with self.received_scores_lock:  # Lock khi kiểm tra
                # Tạo copy của set để tránh lỗi thay đổi kích thước khi lặp
                for task_id in list(tasks_still_needing_check):
                    if self._has_sufficient_scores(task_id, total_active):
                        logger.debug(f"Task {task_id} now has sufficient scores.")
                        processed_task_ids.add(task_id)
                    else:
                        # Chỉ cần một task chưa đủ là chưa xong
                        all_relevant_tasks_sufficient = False
                        # Vẫn tiếp tục kiểm tra các task khác trong lần lặp này

    async def _get_current_block_timestamp(self) -> Optional[int]:
        """Get current block timestamp with circuit breaker protection"""
        try:
            return await self.circuit_breaker.execute(
                self._get_block_timestamp_implementation
            )
        except Exception as e:
            logger.error(f"Failed to get block timestamp: {e}")
            return None

    async def _get_block_timestamp_implementation(self) -> Optional[int]:
        """Actual implementation of getting block timestamp"""
        max_retries = self.settings.CONSENSUS_MAX_RETRIES or 3
        retry_delay = self.settings.CONSENSUS_RETRY_DELAY_SECONDS or 2

        for attempt in range(max_retries):
            try:
                logger.debug(f"Attempt {attempt + 1}/{max_retries} to fetch latest block timestamp")
                ledger_info = await self.client.info()
                
                if ledger_info and "ledger_timestamp" in ledger_info:
                    # Convert from microseconds to seconds
                    timestamp = int(ledger_info["ledger_timestamp"]) // 1000000
                    logger.debug(f"Successfully fetched block timestamp: {timestamp}")
                    return timestamp
                    
                logger.warning(f"Attempt {attempt + 1}: Invalid ledger info format: {ledger_info}")
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}: Error fetching latest block info: {e}")
                
            if attempt < max_retries - 1:
                wait_time = retry_delay * (attempt + 1)
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                
        logger.error(f"Failed to fetch block timestamp after {max_retries} attempts")
        return None

    async def _process_task(self, task):
        """Process received task with improved error handling and metrics"""
        start_time = time.time()
        try:
            # Validate task
            if not self._validate_task(task):
                raise ValueError("Invalid task format")
                
            # Process task with timeout
            async with asyncio.timeout(self.settings.TASK_PROCESSING_TIMEOUT):
                result = await self._process_task_logic(task)
                
            # Record metrics
            processing_time = time.time() - start_time
            self.metrics.record_task_processing('validation', processing_time)
            
            return result
            
        except asyncio.TimeoutError:
            self.metrics.record_error('timeout')
            raise
        except Exception as e:
            self.metrics.record_error('validation')
            raise

    def _validate_task(self, task) -> bool:
        """Validate task format and content"""
        try:
            if not hasattr(task, 'task_id') or not task.task_id:
                return False
                
            if not hasattr(task, 'task_data') or not task.task_data:
                return False
                
            # Add more validation as needed
            return True
            
        except Exception:
            return False

    async def _receive_task_via_network_async(self):
        """Receive task via network asynchronously"""
        start_time = time.time()
        try:
            # Get task from network
            task = await self._get_task_from_network()  # Implement this method based on your network protocol
            self.metrics.record_task_receive('success')
            self.metrics.record_network_latency('task_receive', time.time() - start_time)
            return task
        except TimeoutError:
            self.metrics.record_task_receive('timeout')
            self.metrics.record_error('network')
            raise
        except Exception as e:
            self.metrics.record_task_receive('invalid')
            self.metrics.record_error('network')
            raise

    async def _update_metagraph(self):
        """Update metagraph data"""
        try:
            # Load latest metagraph data
            await self.load_metagraph_data()
            
            # Update active nodes count
            active_miners = len([m for m in self.miners_info.values() if m.status == STATUS_ACTIVE])
            active_validators = len([v for v in self.validators_info.values() if v.status == STATUS_ACTIVE])
            
            self.metrics.update_active_nodes(active_miners + active_validators)
            logger.info(f"Updated metagraph: {active_miners} active miners, {active_validators} active validators")
        except Exception as e:
            logger.error(f"⚠️ Failed to update metagraph: {e}")
            self.metrics.record_error('consensus')
            # Don't raise - continue with existing miners_info to avoid breaking the batch
            logger.warning(f"Continuing with existing miners_info: {len(self.miners_info) if self.miners_info else 0} miners")
            
            # If completely empty, try to force reload once more
            if not self.miners_info:
                logger.warning("🔄 No existing miners_info, attempting one more metagraph load...")
                try:
                    await self.load_metagraph_data()
                    logger.info(f"✅ Fallback metagraph load successful: {len(self.miners_info) if self.miners_info else 0} miners")
                except Exception as fallback_e:
                    logger.error(f"❌ Fallback metagraph load also failed: {fallback_e}")
                    # Continue with empty - let the main loop handle the "No miners available" case
                    
    async def _collect_local_scores_for_consensus(self, slot: int) -> Dict[str, float]:
        """Collect local scores for consensus coordination"""
        local_scores = {}
        
        try:
            # Get scores from slot_scores (primary source from cardano_score_results)
            if hasattr(self, 'slot_scores') and slot in self.slot_scores:
                for score_record in self.slot_scores[slot]:
                    if isinstance(score_record, dict):
                        miner_uid = score_record.get('miner_uid')
                        score = score_record.get('score', 0.0)
                        if miner_uid:
                            local_scores[miner_uid] = score
                            
            # Get scores from current cycle (backup source)
            if hasattr(self, 'cycle_scores') and slot in self.cycle_scores:
                for score_record in self.cycle_scores[slot]:
                    if isinstance(score_record, dict):
                        miner_uid = score_record.get('miner_uid')
                        score = score_record.get('score', 0.0)
                        if miner_uid:
                            local_scores[miner_uid] = score
                            
            # Also check validator_scores (alternative storage)
            if hasattr(self, 'validator_scores'):
                for task_id, scores_list in self.validator_scores.items():
                    for score_obj in scores_list:
                        if hasattr(score_obj, 'miner_uid') and hasattr(score_obj, 'score'):
                            if score_obj.validator_uid == self.info.uid:
                                local_scores[score_obj.miner_uid] = score_obj.score
                                
            logger.info(f"📊 [V:{self.info.uid}] Collected {len(local_scores)} local scores for slot {slot}")
            for miner_uid, score in local_scores.items():
                logger.info(f"   {miner_uid}: {score:.4f}")
                
        except Exception as e:
            logger.error(f"❌ [V:{self.info.uid}] Error collecting local scores: {e}")
            
        return local_scores
        
    async def _coordinate_synchronized_metagraph_update(self, slot: int, local_scores: Dict[str, float]) -> bool:
        """Coordinate synchronized metagraph update with other validators"""
        try:
            # Get consensus window timing
            epoch_start = 1735689600  # Jan 1, 2025 00:00:00 UTC
            slot_duration_seconds = 15 * 60  # 15 minutes
            slot_start = epoch_start + (slot * slot_duration_seconds)
            
            # Consensus window: minutes 11-15 of the slot
            consensus_start = slot_start + (11 * 60)
            consensus_end = slot_start + (15 * 60)
            current_time = int(time.time())
            
            # Check if we're in consensus window
            if current_time < consensus_start:
                wait_time = consensus_start - current_time
                logger.info(f"⏰ [V:{self.info.uid}] Waiting {wait_time}s for consensus window of slot {slot}")
                await asyncio.sleep(wait_time)
                
            current_time = int(time.time())
            if current_time >= consensus_end:
                logger.warning(f"⚠️ [V:{self.info.uid}] Missed consensus window for slot {slot}")
                return False
                
            # Register this validator as ready for consensus
            await self._register_validator_ready_for_consensus(slot, local_scores)
            
            # Wait for other validators to be ready
            participating_validators = await self._wait_for_validator_consensus(slot)
            
            if len(participating_validators) < 2:
                logger.warning(f"⚠️ [V:{self.info.uid}] Insufficient validators for consensus: {len(participating_validators)}")
                return False
                
            # Calculate consensus scores
            consensus_scores = await self._calculate_consensus_scores(slot, participating_validators)
            
            if not consensus_scores:
                logger.warning(f"⚠️ [V:{self.info.uid}] No consensus scores calculated")
                return False
                
            # Apply consensus scores to metagraph
            await self._apply_consensus_scores_to_metagraph(slot, consensus_scores)
            
            logger.info(f"✅ [V:{self.info.uid}] Synchronized consensus completed for slot {slot}")
            return True
            
        except Exception as e:
            logger.error(f"❌ [V:{self.info.uid}] Error in synchronized consensus: {e}")
            return False
            
    async def _register_validator_ready_for_consensus(self, slot: int, local_scores: Dict[str, float]):
        """Register this validator as ready for consensus"""
        # Use a simple file-based coordination mechanism
        consensus_dir = Path("consensus_coordination")
        consensus_dir.mkdir(exist_ok=True)
        
        validator_file = consensus_dir / f"validator_{self.info.uid}_slot_{slot}.json"
        
        consensus_data = {
            'validator_uid': str(self.info.uid),
            'slot': slot,
            'scores': local_scores,
            'timestamp': time.time(),
            'ready': True
        }
        
        import json
        with open(validator_file, 'w') as f:
            json.dump(consensus_data, f)
            
        logger.info(f"✅ [V:{self.info.uid}] Registered for consensus on slot {slot}")
        
    async def _wait_for_validator_consensus(self, slot: int, timeout: int = 120) -> List[str]:
        """Wait for other validators to be ready for consensus"""
        start_time = time.time()
        consensus_dir = Path("consensus_coordination")
        required_validators = ['validator_1', 'validator_2', 'validator_3']
        
        logger.info(f"🤝 [V:{self.info.uid}] Waiting for validators to be ready for consensus on slot {slot}")
        
        while time.time() - start_time < timeout:
            ready_validators = []
            
            for validator_uid in required_validators:
                validator_file = consensus_dir / f"validator_{validator_uid}_slot_{slot}.json"
                if validator_file.exists():
                    try:
                        import json
                        with open(validator_file, 'r') as f:
                            data = json.load(f)
                            if data.get('ready', False) and data.get('slot') == slot:
                                ready_validators.append(validator_uid)
                    except Exception as e:
                        logger.debug(f"Error reading validator file {validator_file}: {e}")
                        
            logger.info(f"🔍 [V:{self.info.uid}] Slot {slot}: {len(ready_validators)}/{len(required_validators)} validators ready: {ready_validators}")
            
            # Need at least 2 validators for consensus (majority of 3)
            if len(ready_validators) >= 2:
                logger.info(f"✅ [V:{self.info.uid}] Sufficient validators ready for consensus: {ready_validators}")
                return ready_validators
                
            await asyncio.sleep(5)  # Check every 5 seconds
            
        logger.warning(f"⚠️ [V:{self.info.uid}] Timeout waiting for validators. Only {len(ready_validators)} ready")
        return ready_validators
        
    async def _calculate_consensus_scores(self, slot: int, participating_validators: List[str]) -> Dict[str, float]:
        """Calculate consensus scores from all participating validators"""
        try:
            consensus_dir = Path("consensus_coordination")
            all_scores = {}
            validator_scores = {}
            
            logger.info(f"🧮 [V:{self.info.uid}] Calculating consensus for slot {slot} with validators: {participating_validators}")
            
            # Collect scores from all participating validators
            for validator_uid in participating_validators:
                validator_file = consensus_dir / f"validator_{validator_uid}_slot_{slot}.json"
                if validator_file.exists():
                    try:
                        import json
                        with open(validator_file, 'r') as f:
                            data = json.load(f)
                            if data.get('slot') == slot:
                                scores = data.get('scores', {})
                                validator_scores[validator_uid] = scores
                                
                                # Aggregate scores per miner
                                for miner_uid, score in scores.items():
                                    if miner_uid not in all_scores:
                                        all_scores[miner_uid] = []
                                    all_scores[miner_uid].append(score)
                                    
                    except Exception as e:
                        logger.error(f"Error reading validator {validator_uid} scores: {e}")
                        
            logger.info(f"📊 [V:{self.info.uid}] Collected scores from {len(validator_scores)} validators")
            logger.info(f"📈 [V:{self.info.uid}] Scores for {len(all_scores)} miners")
            
            # Calculate consensus (simple average)
            consensus_scores = {}
            for miner_uid, score_list in all_scores.items():
                if score_list:
                    consensus_score = sum(score_list) / len(score_list)
                    consensus_scores[miner_uid] = consensus_score
                    logger.info(f"   {miner_uid}: {score_list} → {consensus_score:.4f}")
                    
            logger.info(f"✅ [V:{self.info.uid}] Consensus calculated for slot {slot}: {len(consensus_scores)} miner scores")
            return consensus_scores
            
        except Exception as e:
            logger.error(f"❌ [V:{self.info.uid}] Error calculating consensus: {e}")
            return {}
            
    async def _apply_consensus_scores_to_metagraph(self, slot: int, consensus_scores: Dict[str, float]):
        """Apply consensus scores to metagraph"""
        try:
            logger.info(f"🔄 [V:{self.info.uid}] Applying consensus scores to metagraph for slot {slot}")
            
            # Load current metagraph
            await self.load_metagraph_data()
            
            # Update miner scores with consensus results
            for miner_uid, consensus_score in consensus_scores.items():
                if miner_uid in self.miners_info:
                    old_score = self.miners_info[miner_uid].trust_score
                    # Update with exponential moving average
                    new_score = old_score * 0.8 + consensus_score * 0.2
                    self.miners_info[miner_uid].trust_score = new_score
                    
                    logger.info(f"📊 [V:{self.info.uid}] Updated {miner_uid}: {old_score:.4f} → {new_score:.4f}")
                    
            logger.info(f"✅ [V:{self.info.uid}] Applied consensus scores to metagraph")
            
        except Exception as e:
            logger.error(f"❌ [V:{self.info.uid}] Error applying consensus scores: {e}")

    async def start_health_server(self):
        """Start the health check server"""
        # Extract port from api_endpoint if available, but use different port for health
        port = 8000  # Default health port (different from API port)
        if hasattr(self.info, 'api_endpoint') and self.info.api_endpoint:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(self.info.api_endpoint)
                if parsed.port:
                    # Use API port + 1000 for health server to avoid conflict
                    port = parsed.port + 1000
                    logger.info(f"Using health port {port} (API port + 1000) from validator api_endpoint: {self.info.api_endpoint}")
                else:
                    logger.warning(f"No port found in api_endpoint {self.info.api_endpoint}, using default health port {port}")
            except Exception as e:
                logger.warning(f"Failed to parse port from api_endpoint {self.info.api_endpoint}: {e}, using default health port {port}")
        
        config = uvicorn.Config(
            health_app,
            host="0.0.0.0",
            port=port,
            log_level="info"
        )
        self.health_server = uvicorn.Server(config)
        await self.health_server.serve()

    async def start_api_server(self):
        """Start the API server for receiving miner results"""
        # Extract port from api_endpoint if available
        port = 8001  # Default port
        if hasattr(self.info, 'api_endpoint') and self.info.api_endpoint:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(self.info.api_endpoint)
                if parsed.port:
                    port = parsed.port
                    logger.info(f"Using port {port} from validator api_endpoint for API server: {self.info.api_endpoint}")
                else:
                    logger.warning(f"No port found in api_endpoint {self.info.api_endpoint}, using default port {port}")
            except Exception as e:
                logger.warning(f"Failed to parse port from api_endpoint {self.info.api_endpoint}: {e}, using default port {port}")
        
        # Set this validator node instance for API dependencies
        from mt_aptos.network.app.dependencies import set_validator_node_instance
        set_validator_node_instance(self)
        
        # Import FastAPI app with miner endpoints
        from mt_aptos.network.app.main import app
        
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info"
        )
        self.api_server = uvicorn.Server(config)
        await self.api_server.serve()

    async def run(self):
        """Run the validator node with continuous consensus like Cardano ModernTensor"""
        # Load initial metagraph data before starting
        logger.info(f"📊 [V:{self.info.uid}] Loading initial metagraph data...")
        try:
            await self.load_metagraph_data()
            logger.info(f"✅ [V:{self.info.uid}] Initial metagraph loaded. Miners: {len(self.miners_info) if self.miners_info else 0}, Validators: {len(self.validators_info) if self.validators_info else 0}")
        except Exception as e:
            logger.error(f"⚠️ [V:{self.info.uid}] Failed to load initial metagraph: {e}")
            logger.warning(f"Continuing with empty metagraph - will retry during periodic updates")
        
        # Start health check server in background
        health_task = asyncio.create_task(self.start_health_server())
        
        # Start API server for miner communications in background
        api_task = asyncio.create_task(self.start_api_server())
        
        # Start consensus based on configured mode
        logger.info(f"🚀 [V:{self.info.uid}] Starting {self.consensus_mode} consensus mode...")
        
        if self.consensus_mode == "sequential":
            logger.info(f"📋 [V:{self.info.uid}] Sequential batch mode - Wait time: {self.batch_wait_time}s")
            await self.run_sequential_batch_consensus()
        elif self.consensus_mode == "synchronized":
            logger.info(f"🤝 [V:{self.info.uid}] Synchronized consensus mode - Validators coordinate and wait for each other")
            await self.run_synchronized_consensus()
        else:
            logger.info(f"🔄 [V:{self.info.uid}] Continuous consensus mode")
            await self.run_continuous_cardano_consensus()

    async def run_continuous_cardano_consensus(self):
        """Run consensus in synchronized slots based on blockchain time"""
        logger.info(f"🕰️ [V:{self.info.uid}] Starting synchronized slot-based consensus...")
        logger.info(f"   Slot duration: {self.slot_config.slot_duration_minutes} minutes")

        # Initial metagraph load
        await self._update_metagraph()

        last_processed_slot = -1

        while True:
            current_slot = -1  # Initialize for error logging
            try:
                current_slot = self.get_current_blockchain_slot()

                if current_slot is None:
                    logger.warning("Could not determine current slot, waiting...")
                    await asyncio.sleep(10)
                    continue

                if current_slot <= last_processed_slot:
                    # Wait for the next slot to begin
                    await self.wait_until_slot(current_slot + 1)
                    continue

                # New slot begins
                logger.info(f"====== SLOT {current_slot} START ======")
                phase, minutes_into_phase, minutes_remaining = self.get_slot_phase(current_slot)

                # Main state machine for the slot
                logger.info(f"Entering phase {phase.name} for slot {current_slot}")

                if phase == SlotPhase.TASK_ASSIGNMENT:
                    await self.handle_task_assignment_phase(current_slot, minutes_remaining)
                
                elif phase == SlotPhase.TASK_EXECUTION:
                    # This phase is mostly for miners. Validators wait.
                    await self.handle_task_execution_phase(current_slot, minutes_remaining)

                elif phase == SlotPhase.CONSENSUS_SCORING:
                    await self.handle_consensus_phase(current_slot, minutes_remaining)
                
                elif phase == SlotPhase.METAGRAPH_UPDATE:
                    await self.handle_metagraph_update_phase(current_slot, minutes_remaining)

                logger.info(f"====== SLOT {current_slot} PHASE {phase.name} COMPLETED ======")
                
                # After handling the current state, mark slot as processed
                last_processed_slot = current_slot

                # At the end of a full cycle, we might want to do extra cleanup
                if phase == SlotPhase.METAGRAPH_UPDATE:
                    logger.info(f"✅ [V:{self.info.uid}] Full consensus cycle for slot {current_slot} completed.")
                    # Update metagraph with consensus results
                    logger.info(f"🔄 [V:{self.info.uid}] Updating metagraph with consensus results...")
                    await self.cardano_update_metagraph_with_consensus()

            except Exception as e:
                logger.error(f"❌ [V:{self.info.uid}] Error in synchronized slot {current_slot}: {e}", exc_info=True)
                # Wait a bit before retrying to avoid spamming errors
                await asyncio.sleep(30)

    def cardano_select_miners_continuous(self, cycle: int) -> List[MinerInfo]:
        """Select miners using Cardano ModernTensor continuous pattern"""
        logger.debug(f"🔍 [V:{self.info.uid}] Continuous miner selection for cycle {cycle}")
        
        if not self.miners_info:
            logger.warning(f"⚠️ [V:{self.info.uid}] No miners_info available!")
            return []
        
        # Get active miners (Cardano pattern)
        active_miners = [
            m for m in self.miners_info.values()
            if getattr(m, "status", STATUS_ACTIVE) == STATUS_ACTIVE and m.uid not in self.miner_is_busy
        ]
        
        if not active_miners:
            logger.warning(f"⚠️ [V:{self.info.uid}] No active miners available!")
            return []
        
        # Cardano continuous pattern - select different miners each cycle
        num_to_select = min(
            getattr(self.settings, 'CONSENSUS_NUM_MINERS_TO_SELECT', 2),
            len(active_miners)
        )
        
        # Deterministic but rotating selection
        sorted_miners = sorted(active_miners, key=lambda m: m.uid)
        start_idx = cycle % len(sorted_miners)
        selected = []
        
        for i in range(num_to_select):
            idx = (start_idx + i) % len(sorted_miners)
            selected.append(sorted_miners[idx])
        
        return selected
    
    async def cardano_send_tasks_continuous(self, cycle: int, miners: List[MinerInfo]):
        """Send tasks using Cardano ModernTensor continuous pattern"""
        logger.info(f"🚀 [V:{self.info.uid}] Cardano continuous sending tasks to {len(miners)} miners (cycle {cycle})")
        
        # First, check health of all miners
        logger.info(f"🔍 [V:{self.info.uid}] Checking health of {len(miners)} miners...")
        healthy_miners = []
        
        health_checks = []
        for miner in miners:
            health_checks.append(self._check_miner_health(miner.api_endpoint))
        
        health_results = await asyncio.gather(*health_checks, return_exceptions=True)
        
        for miner, is_healthy in zip(miners, health_results):
            if is_healthy is True:
                healthy_miners.append(miner)
                logger.info(f"✅ [V:{self.info.uid}] Miner {miner.uid} is healthy")
            else:
                logger.warning(f"⚠️ [V:{self.info.uid}] Miner {miner.uid} is not healthy - skipping task send")
        
        if not healthy_miners:
            logger.warning(f"❌ [V:{self.info.uid}] No healthy miners available for cycle {cycle}")
            return
        
        logger.info(f"🎯 [V:{self.info.uid}] Sending tasks to {len(healthy_miners)}/{len(miners)} healthy miners")
        
        # Prepare all tasks first (Cardano pattern)
        task_assignments = []
        task_sends = []
        
        for miner in healthy_miners:
            try:
                # Continuous task ID (Cardano pattern)
                task_id = f"cycle_{cycle}_{miner.uid}_{self.info.uid}"
                
                # Create task (Cardano style)
                task_data = self.cardano_create_task_continuous(cycle, miner.uid)
                
                # Create assignment
                assignment = TaskAssignment(
                    task_id=task_id,
                    task_data=task_data,
                    miner_uid=miner.uid,
                    validator_uid=self.info.uid,
                    timestamp_sent=time.time(),
                    expected_result_format={},
                )
                
                # Store assignment for tracking
                task_assignments.append((task_id, assignment, miner))
                
                # Prepare task for sending
                from mt_aptos.network.server import TaskModel
                task = TaskModel(task_id=task_id, **task_data)
                
                # Add to parallel send list
                task_sends.append(self._cardano_send_single_task(task_id, assignment, miner, task))
                
            except Exception as e:
                logger.error(f"❌ [V:{self.info.uid}] Cardano continuous task prep error for {miner.uid}: {e}")
        
        # Send all tasks in parallel (Cardano ModernTensor SDK pattern)
        if task_sends:
            logger.info(f"📡 [V:{self.info.uid}] Sending {len(task_sends)} tasks in parallel...")
            results = await asyncio.gather(*task_sends, return_exceptions=True)
            
            # Process results
            success_count = 0
            for i, (result, (task_id, assignment, miner)) in enumerate(zip(results, task_assignments)):
                if result is True:
                    # Success - store assignment and mark miner busy
                    self.tasks_sent[task_id] = assignment
                    self.miner_is_busy.add(miner.uid)
                    success_count += 1
                    logger.info(f"✅ [V:{self.info.uid}] Cardano continuous task sent to {miner.uid}")
                else:
                    # Failed - log error
                    logger.warning(f"❌ [V:{self.info.uid}] Failed Cardano continuous task to {miner.uid}: {result if isinstance(result, Exception) else 'Unknown error'}")
            
            logger.info(f"🎯 [V:{self.info.uid}] Cardano continuous send complete: {success_count}/{len(task_sends)} successful")
    
    def cardano_create_task_continuous(self, cycle: int, miner_uid: str) -> Dict[str, Any]:
        """Create task using Cardano ModernTensor continuous pattern"""
        # Deadline for continuous cycles (shorter than slot-based)
        deadline_timestamp = time.time() + (self.settings.CONSENSUS_CYCLE_LENGTH * 0.6)  # 60% of cycle time
        deadline_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(deadline_timestamp))
        
        # TaskModel compatible format
        task_data = {
            "description": f"Generate an image for cycle {cycle}",  # Required field
            "deadline": deadline_str,  # String format required
            "priority": 3,  # Medium priority
            "validator_endpoint": getattr(self.info, 'api_endpoint', 'http://localhost:8001'),
            "task_data": {  # Actual task payload
                "type": "image_generation",
                "prompt": f"Beautiful landscape for cycle {cycle}",
                "cycle": cycle,
                "miner_uid": miner_uid,
                "expected_format": "base64_image"
            }
        }
        
        return task_data
    
    async def cardano_wait_for_results_batch(self, batch_number: int):
        """Wait for results using Cardano ModernTensor continuous pattern"""
        wait_time = self.settings.CONSENSUS_CYCLE_LENGTH * 0.5  # 50% of cycle time for results
        logger.info(f"⏳ [V:{self.info.uid}] Waiting {wait_time:.1f}s for batch {batch_number} results...")
        
        start_time = time.time()
        while time.time() - start_time < wait_time:
            # Check if we have results for current batch tasks
            batch_tasks = [task_id for task_id in self.tasks_sent.keys() if task_id.startswith(f"cycle_{batch_number}_")]
            received_results = [task_id for task_id in batch_tasks if task_id in self.results_buffer]
            
            if len(received_results) >= len(batch_tasks) * 0.8:  # 80% response rate
                logger.info(f"✅ [V:{self.info.uid}] Got {len(received_results)}/{len(batch_tasks)} results early!")
                break
                
            await asyncio.sleep(1)  # Check every second
        
        # Final check
        batch_tasks = [task_id for task_id in self.tasks_sent.keys() if task_id.startswith(f"cycle_{batch_number}_")]
        received_results = [task_id for task_id in batch_tasks if task_id in self.results_buffer]
        logger.info(f"📊 [V:{self.info.uid}] Final results: {len(received_results)}/{len(batch_tasks)} for batch {batch_number}")
    
    async def cardano_score_results_continuous(self, batch_number: int):
        """Score results using Cardano ModernTensor continuous pattern"""
        logger.info(f"📊 [V:{self.info.uid}] Cardano continuous scoring for batch {batch_number}")
        
        scored_tasks = []
        
        # ENHANCED LOGGING: Track all tasks and their status
        all_tasks_sent = list(self.tasks_sent.keys())
        logger.info(f"🔍 [V:{self.info.uid}] DEBUG: Total tasks_sent: {len(all_tasks_sent)} - {all_tasks_sent[:5]}...")
        
        # Process all tasks for this batch
        batch_tasks = [task_id for task_id, assignment in self.tasks_sent.items() if task_id.startswith(f"cycle_{batch_number}_")]
        logger.info(f"🔍 [V:{self.info.uid}] DEBUG: Batch {batch_number} tasks found: {len(batch_tasks)} - {batch_tasks[:3]}...")
        
        # FORCE SCORING: If no batch tasks found, check if any tasks exist at all
        if not batch_tasks and self.tasks_sent:
            logger.warning(f"⚠️ [V:{self.info.uid}] No batch tasks found but {len(self.tasks_sent)} tasks exist. Checking all tasks...")
            # Score all existing tasks if batch pattern doesn't match
            batch_tasks = list(self.tasks_sent.keys())
            logger.info(f"🔧 [V:{self.info.uid}] FORCE: Scoring all {len(batch_tasks)} existing tasks")
        
        for task_id in batch_tasks:
            if task_id not in self.tasks_sent:
                logger.warning(f"⚠️ [V:{self.info.uid}] Task {task_id} not in tasks_sent - skipping")
                continue
                
            assignment = self.tasks_sent[task_id]
            miner_uid = assignment.miner_uid
            
            # Check if we have result
            if task_id in self.results_buffer:
                try:
                    result = self.results_buffer[task_id]
                    
                    # Score using subnet-specific logic (CLIP scoring for Subnet1)
                    score = self._score_individual_result(assignment.task_data, result.result_data)
                    
                    # Create score record (Cardano pattern)
                    score_record = {
                        "task_id": task_id,
                        "miner_uid": miner_uid,
                        "score": score,
                        "validator_uid": self.info.uid,
                        "batch": batch_number,
                        "timestamp": time.time()
                    }
                    
                    scored_tasks.append(score_record)
                    logger.info(f"✅ [V:{self.info.uid}] Scored {miner_uid}: {score:.4f} (with result)")
                    
                except Exception as e:
                    logger.error(f"❌ Scoring error for {task_id}: {e}")
                    # Zero score on error
                    score_record = {
                        "task_id": task_id,
                        "miner_uid": miner_uid,
                        "score": 0.0,
                        "validator_uid": self.info.uid,
                        "batch": batch_number,
                        "timestamp": time.time()
                    }
                    scored_tasks.append(score_record)
                    logger.info(f"🔧 [V:{self.info.uid}] Scored {miner_uid}: 0.0000 (scoring error)")
            else:
                # No result = timeout score
                logger.warning(f"⏰ [V:{self.info.uid}] Timeout for {miner_uid} (task: {task_id})")
                score_record = {
                    "task_id": task_id,
                    "miner_uid": miner_uid,
                    "score": 0.0,
                    "validator_uid": self.info.uid,
                    "batch": batch_number,
                    "timestamp": time.time()
                }
                scored_tasks.append(score_record)
                logger.info(f"🔧 [V:{self.info.uid}] Scored {miner_uid}: 0.0000 (no result - timeout)")
            
            # Release miner (Cardano pattern)
            self.miner_is_busy.discard(miner_uid)
            
            # Clean up task
            del self.tasks_sent[task_id]
            if task_id in self.results_buffer:
                del self.results_buffer[task_id]
        
        # Store scores for this batch (accumulate scores)
        if batch_number not in self.cycle_scores:
            self.cycle_scores[batch_number] = []
        self.cycle_scores[batch_number].extend(scored_tasks)
        
        # ENHANCED LOGGING: Track cycle_scores accumulation
        total_cycle_scores = sum(len(scores) for scores in self.cycle_scores.values())
        logger.info(f"📊 [V:{self.info.uid}] Cardano continuous scoring complete: {len(scored_tasks)} tasks scored")
        logger.info(f"📊 [V:{self.info.uid}] Total cycle_scores accumulated: {total_cycle_scores} across {len(self.cycle_scores)} batches")
        
        # CRITICAL: If no scores were created, force create dummy scores for active miners
        if not scored_tasks and self.miners_info:
            logger.warning(f"⚠️ [V:{self.info.uid}] No tasks scored - creating dummy scores for active miners")
            active_miners = [m for m in self.miners_info.values() if m.status == "active"][:2]  # Take 2 miners
            for miner in active_miners:
                dummy_score = {
                    "task_id": f"dummy_{batch_number}_{miner.uid}",
                    "miner_uid": miner.uid,
                    "score": 0.0,
                    "validator_uid": self.info.uid,
                    "batch": batch_number,
                    "timestamp": time.time()
                }
                self.cycle_scores[batch_number].append(dummy_score)
                logger.info(f"🔧 [V:{self.info.uid}] Created dummy score for {miner.uid}: 0.0000")
            
            logger.info(f"🔧 [V:{self.info.uid}] Added {len(active_miners)} dummy scores to ensure blockchain submission")
    
    def get_current_cycle_number(self) -> int:
        """Get current cycle number based on time"""
        return int(time.time() // self.settings.CONSENSUS_CYCLE_LENGTH)
    
    @property
    def current_cycle(self) -> int:
        """Get current cycle number"""
        return getattr(self, '_current_cycle', self.get_current_cycle_number())

    def set_current_cycle(self, cycle: int):
        """Set the current cycle number"""
        self._current_cycle = cycle

    def advance_to_next_cycle(self):
        """Advance to the next cycle"""
        self._current_cycle = getattr(self, '_current_cycle', self.get_current_cycle_number()) + 1
    
    async def cardano_broadcast_accumulated_scores(self):
        """Broadcast all accumulated scores to other validators"""
        if not self.cycle_scores:
            logger.warning("No scores to broadcast.")
            return
        
        try:
            # Prepare Cardano-style broadcast payload
            broadcast_payload = {
                "type": "validator_scores",
                "cycle": self._current_cycle,
                "validator_uid": self.info.uid,
                "scores": [
                    {
                        "task_id": score_record.get("task_id", ""),
                        "miner_uid": score_record.get("miner_uid", ""),
                        "score": score_record.get("score", 0.0),
                        "validator_uid": self.info.uid,
                        "cycle": self._current_cycle,
                        "timestamp": time.time()
                    }
                    for batch_scores in self.cycle_scores.values()
                    for score_record in batch_scores
                ],
                "timestamp": time.time()
            }
            
            logger.info(f"📡 [V:{self.info.uid}] Broadcasting {len(broadcast_payload['scores'])} scores to {len(self.validators_info) - 1} validators")
            
            # Send to all other validators (Cardano P2P pattern)
            broadcast_tasks = []
            for validator in self.validators_info.values():
                if validator.uid != self.info.uid:
                    broadcast_tasks.append(
                        self.cardano_send_scores(validator, broadcast_payload)
                    )
            
            if broadcast_tasks:
                results = await asyncio.gather(*broadcast_tasks, return_exceptions=True)
                success_count = sum(1 for r in results if r is True)
                logger.info(f"📡 [V:{self.info.uid}] Cardano broadcast: {success_count}/{len(broadcast_tasks)} successful")
            
        except Exception as e:
            logger.error(f"❌ [V:{self.info.uid}] Cardano broadcast error: {e}")
    
    async def cardano_wait_for_peer_scores(self):
        """Wait for other validators' scores"""
        logger.info(f"🕒 [V:{self.info.uid}] Waiting for other validators' scores...")
        await self.wait_for_consensus_scores(self.settings.CONSENSUS_CYCLE_LENGTH)
    
    async def cardano_finalize_consensus_round(self):
        """Finalize consensus with all validator scores"""
        logger.info(f"🎯 [V:{self.info.uid}] Finalizing consensus with all validator scores")
        logger.info(f"🔍 [V:{self.info.uid}] DEBUG: Current cycle = {self._current_cycle}")
        logger.info(f"🔍 [V:{self.info.uid}] DEBUG: Miners info = {len(self.miners_info) if self.miners_info else 0} miners")
        logger.info(f"🔍 [V:{self.info.uid}] DEBUG: Cycle scores = {len(self.cycle_scores.get(self._current_cycle, [])) if self.cycle_scores else 0} scores")
        logger.info(f"🔍 [V:{self.info.uid}] DEBUG: Received validator scores = {len(self.received_validator_scores.get(self._current_cycle, {})) if self.received_validator_scores else 0} validators")
        
        try:
            # STEP 1: Calculate and broadcast OUR average scores to other validators
            await self.cardano_broadcast_average_scores()
            
            # STEP 2: Collect all scores (own + received from other validators)
            all_validator_scores = defaultdict(list)  # miner_uid -> list of scores
            
            # Add our own scores
            if self._current_cycle in self.cycle_scores:
                for score_record in self.cycle_scores[self._current_cycle]:
                    miner_uid = score_record["miner_uid"]
                    score = score_record["score"]
                    all_validator_scores[miner_uid].append(score)
            
            # Add scores from other validators (received via P2P)
            if self._current_cycle in self.received_validator_scores:
                for validator_uid, scores_dict in self.received_validator_scores[self._current_cycle].items():
                    for score_record in scores_dict.values():
                        if isinstance(score_record, dict):
                            miner_uid = score_record.get("miner_uid")
                            score = score_record.get("score", 0.0)
                            if miner_uid:
                                all_validator_scores[miner_uid].append(score)
            
            # Calculate final consensus scores (Cardano aggregation)
            final_scores = {}
            
            # IMPORTANT: Track ALL miners that were sent tasks, even if they didn't respond
            all_miners_with_tasks = set()
            
            # Method 1: Get miners from cycle_scores (has scores)
            if self._current_cycle in self.cycle_scores:
                for score_record in self.cycle_scores[self._current_cycle]:
                    miner_uid = score_record.get("miner_uid")
                    if miner_uid:
                        all_miners_with_tasks.add(miner_uid)
            
            # Method 2: Get miners from received validator scores
            if self._current_cycle in self.received_validator_scores:
                for validator_uid, scores_dict in self.received_validator_scores[self._current_cycle].items():
                    for score_record in scores_dict.values():
                        if isinstance(score_record, dict):
                            miner_uid = score_record.get("miner_uid")
                            if miner_uid:
                                all_miners_with_tasks.add(miner_uid)
            
            # Method 3: FORCE INCLUSION - Get miners from current active miners list
            # This ensures we always have miners to submit, even if no tasks were sent
            if not all_miners_with_tasks and self.miners_info:
                logger.warning(f"⚠️ [V:{self.info.uid}] No miners found in scores - adding active miners for blockchain submission")
                active_miners = [miner for miner in self.miners_info.values() if miner.status == STATUS_ACTIVE]
                for miner in active_miners[:3]:  # Take first 3 active miners
                    all_miners_with_tasks.add(miner.uid)
                    logger.info(f"🔧 [V:{self.info.uid}] Force-added miner {miner.uid} for blockchain submission")
            
            # Calculate scores for all miners (including those who didn't respond)
            for miner_uid in all_miners_with_tasks:
                score_list = all_validator_scores.get(miner_uid, [])
                
                if score_list:
                    # Has scores from validators
                    consensus_score = sum(score_list) / len(score_list)  # Average
                    final_scores[miner_uid] = consensus_score
                    logger.info(f"🎯 [V:{self.info.uid}] Final: {miner_uid} = {consensus_score:.4f} (from {len(score_list)} validators)")
                else:
                    # No scores = miner didn't respond = 0.0 score
                    final_scores[miner_uid] = 0.0
                    logger.info(f"🎯 [V:{self.info.uid}] Final: {miner_uid} = 0.0000 (no response - penalty)")
            
            # Store final results (Cardano pattern)
            self.slot_consensus_results[self._current_cycle] = final_scores
            
            # 🔥 ALWAYS SUBMIT TO BLOCKCHAIN - Even if no tasks were sent or no scores exist 🔥
            if final_scores:
                await self.cardano_submit_consensus_to_blockchain(final_scores)
                logger.info(f"✅ [V:{self.info.uid}] Blockchain submission completed for {len(final_scores)} miners")
            else:
                # FALLBACK: Submit empty consensus to maintain blockchain consistency
                logger.warning(f"⚠️ [V:{self.info.uid}] No miners available - submitting empty consensus to blockchain")
                empty_scores = {"empty_consensus": 0.0}  # Placeholder for empty consensus
                await self.cardano_submit_consensus_to_blockchain(empty_scores)
                logger.info(f"✅ [V:{self.info.uid}] Empty consensus submitted to blockchain")
            
            logger.info(f"✅ [V:{self.info.uid}] Cardano consensus complete: {len(final_scores)} miners scored")
            
        except Exception as e:
            logger.error(f"❌ [V:{self.info.uid}] Cardano consensus error: {e}")
            # Even on error, try to submit something to maintain blockchain consistency
            try:
                error_scores = {"error_consensus": 0.0}
                await self.cardano_submit_consensus_to_blockchain(error_scores)
                logger.info(f"✅ [V:{self.info.uid}] Error consensus submitted to blockchain")
            except Exception as e2:
                logger.error(f"❌ [V:{self.info.uid}] Failed to submit error consensus: {e2}")
    
    async def cardano_update_metagraph_with_consensus(self):
        """Update metagraph with consensus results"""
        logger.info(f"📊 [V:{self.info.uid}] Updating metagraph with consensus results")
        
        try:
            # Update active nodes count
            active_miners = len([m for m in self.miners_info.values() if m.status == STATUS_ACTIVE])
            active_validators = len([v for v in self.validators_info.values() if v.status == STATUS_ACTIVE])
            
            self.metrics.update_active_nodes(active_miners + active_validators)
            logger.info(f"Updated metagraph: {active_miners} active miners, {active_validators} active validators")
            
            # Update metagraph data
            await self.load_metagraph_data()
            
        except Exception as e:
            logger.error(f"❌ [V:{self.info.uid}] Error updating metagraph: {e}")

    async def _check_miner_health(self, miner_endpoint: str, timeout: float = 5.0) -> bool:
        """Check if miner is healthy and available to receive tasks"""
        try:
            if not miner_endpoint or not miner_endpoint.startswith(("http://", "https://")):
                return False
                
            health_url = f"{miner_endpoint}/health"
            response = await self.http_client.get(health_url, timeout=timeout)
            
            if response.status_code == 200:
                health_data = response.json()
                return health_data.get("status") == "healthy"
            return False
            
        except Exception as e:
            logger.debug(f"Health check failed for {miner_endpoint}: {e}")
            return False

    async def _cardano_send_single_task(self, task_id: str, assignment: TaskAssignment, miner: MinerInfo, task) -> bool:
        """Send a single task to miner (used in parallel sends)"""
        try:
            logger.debug(f"🚀 Sending task {task_id} to miner {miner.uid} at {miner.api_endpoint}")
            success = await self._send_task_via_network_async(miner.api_endpoint, task)
            if not success:
                logger.warning(f"❌ Task send returned False for {miner.uid}")
            return success
        except Exception as e:
            logger.error(f"❌ Task send exception to {miner.uid}: {e}")
            import traceback
            logger.error(f"Task send traceback: {traceback.format_exc()}")
            return False

    async def run_sequential_batch_consensus(self):
        """Run sequential batch consensus - wait for scoring before next batch"""
        logger.info(f"🔄 [V:{self.info.uid}] Starting SEQUENTIAL batch consensus mode")
        
        batch_number = 1
        
        while True:
            try:
                logger.info(f"🔄 [V:{self.info.uid}] ===== SEQUENTIAL BATCH {batch_number} START =====")
                
                # 1. Load metagraph if needed
                if not self.miners_info:
                    await self._update_metagraph()
                
                # 2. Select miners for this batch
                selected_miners = self.cardano_select_miners_continuous(batch_number)
                if not selected_miners:
                    logger.warning(f"⚠️ [V:{self.info.uid}] No miners available for batch {batch_number}")
                    await asyncio.sleep(10)  # Wait 10s before retry
                    continue
                
                logger.info(f"🎯 [V:{self.info.uid}] Selected {len(selected_miners)} miners: {[m.uid for m in selected_miners]}")
                
                # 3. Send tasks to all selected miners
                await self.cardano_send_tasks_continuous(batch_number, selected_miners)
                
                # 4. Wait for results with SHORT timeout (30 seconds max)
                await self.cardano_wait_for_results_batch_quick(batch_number)
                
                # 5. Score results immediately
                await self.cardano_score_results_continuous(batch_number)
                
                # 6. REMOVED: Don't broadcast scores immediately - only at end of cycle
                # await self.cardano_broadcast_batch_scores(batch_number)
                
                logger.info(f"✅ [V:{self.info.uid}] ===== SEQUENTIAL BATCH {batch_number} COMPLETED =====")
                
                # 7. Advance to next batch
                batch_number += 1
                
                # 8. Short pause before next batch (1-2 seconds)
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ [V:{self.info.uid}] Error in sequential batch {batch_number}: {e}")
                await asyncio.sleep(5)  # Brief pause before retry

    async def cardano_wait_for_results_batch_quick(self, batch_number: int):
        """Wait for results with SHORT timeout - optimized for fast batching"""
        max_wait_time = self.batch_wait_time  # Use configured wait time
        check_interval = 1.0   # Check every 1 second
        
        logger.info(f"⏳ [V:{self.info.uid}] Waiting max {max_wait_time}s for batch {batch_number} results...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            # Check if we have results for current batch tasks
            batch_tasks = [task_id for task_id in self.tasks_sent.keys() if task_id.startswith(f"cycle_{batch_number}_")]
            received_results = [task_id for task_id in batch_tasks if task_id in self.results_buffer]
            
            if batch_tasks:  # Only check if we have tasks
                response_rate = len(received_results) / len(batch_tasks)
                
                # Early exit conditions:
                if len(received_results) == len(batch_tasks):  # 100% response
                    logger.info(f"✅ [V:{self.info.uid}] Got ALL {len(received_results)}/{len(batch_tasks)} results!")
                    break
                elif len(received_results) >= len(batch_tasks) * 0.8:  # 80% response after some time
                    elapsed = time.time() - start_time
                    if elapsed > max_wait_time * 0.5:  # Wait at least half the max time for stragglers
                        logger.info(f"✅ [V:{self.info.uid}] Got {len(received_results)}/{len(batch_tasks)} results ({response_rate:.1%}) - proceeding")
                        break
                        
                # Log progress every 5 seconds
                if int(time.time() - start_time) % 5 == 0:
                    logger.info(f"⏳ [V:{self.info.uid}] Progress: {len(received_results)}/{len(batch_tasks)} ({response_rate:.1%})")
                    
            await asyncio.sleep(check_interval)
        
        # Final summary
        batch_tasks = [task_id for task_id in self.tasks_sent.keys() if task_id.startswith(f"cycle_{batch_number}_")]
        received_results = [task_id for task_id in batch_tasks if task_id in self.results_buffer]
        logger.info(f"📊 [V:{self.info.uid}] Final results: {len(received_results)}/{len(batch_tasks)} for batch {batch_number}")

    async def cardano_broadcast_batch_scores(self, batch_number: int):
        """Broadcast scores for this specific batch (optional, can be done in background)"""
        if batch_number not in self.cycle_scores:
            return
            
        try:
            batch_scores = self.cycle_scores[batch_number]
            
            broadcast_payload = {
                "type": "batch_scores",
                "batch": batch_number, 
                "validator_uid": self.info.uid,
                "scores": batch_scores,
                "timestamp": time.time()
            }
            
            logger.info(f"📡 [V:{self.info.uid}] Broadcasting {len(batch_scores)} scores for batch {batch_number}")
            
            # Send to other validators (can be done async)
            active_validators = [v for v in self.validators_info.values() if v.uid != self.info.uid]
            if active_validators:
                broadcast_tasks = [
                    self.cardano_send_scores(validator, broadcast_payload)
                    for validator in active_validators
                ]
                
                results = await asyncio.gather(*broadcast_tasks, return_exceptions=True)
                success_count = sum(1 for r in results if r is True)
                logger.info(f"📡 [V:{self.info.uid}] Batch {batch_number} broadcast: {success_count}/{len(active_validators)} successful")
                
        except Exception as e:
            logger.error(f"❌ [V:{self.info.uid}] Error broadcasting batch {batch_number} scores: {e}")

    async def run_synchronized_consensus(self):
        """Run synchronized consensus - validators coordinate and wait for each other"""
        logger.info(f"🔄 [V:{self.info.uid}] Starting SYNCHRONIZED consensus mode")
        logger.info(f"📋 [V:{self.info.uid}] Consensus Config: Wait for peer scores, coordinate batches")
        
        batch_number = 1
        consensus_round = 1
        last_consensus_time = time.time()
        
        while True:
            try:
                current_time = time.time()
                
                # === PHASE 1: COORDINATED BATCH EXECUTION ===
                logger.info(f"🔄 [V:{self.info.uid}] ===== SYNCHRONIZED BATCH {batch_number} START =====")
                
                # Load metagraph if needed
                if not self.miners_info:
                    await self._update_metagraph()
                
                # Select miners for this batch
                selected_miners = self.cardano_select_miners_continuous(batch_number)
                if not selected_miners:
                    logger.warning(f"⚠️ [V:{self.info.uid}] No miners available for batch {batch_number}")
                    await asyncio.sleep(10)
                    continue
                
                logger.info(f"🎯 [V:{self.info.uid}] Selected {len(selected_miners)} miners: {[m.uid for m in selected_miners]}")
                
                # Send tasks to selected miners
                await self.cardano_send_tasks_continuous(batch_number, selected_miners)
                
                # Wait for results
                await self.cardano_wait_for_results_batch_quick(batch_number)
                
                # Score results locally
                await self.cardano_score_results_continuous(batch_number)
                
                # REMOVED: Don't broadcast scores immediately - only during consensus rounds  
                # === PHASE 2: BROADCAST SCORES TO OTHER VALIDATORS ===
                # logger.info(f"📡 [V:{self.info.uid}] Broadcasting scores for batch {batch_number}")
                # await self.cardano_broadcast_batch_scores(batch_number)
                
                logger.info(f"✅ [V:{self.info.uid}] ===== SYNCHRONIZED BATCH {batch_number} COMPLETED =====")
                batch_number += 1
                
                # === PHASE 3: PERIODIC CONSENSUS ROUNDS ===
                if current_time - last_consensus_time > self.settings.CONSENSUS_CYCLE_LENGTH:
                    logger.info(f"🎯 [V:{self.info.uid}] ===== CONSENSUS ROUND {consensus_round} START =====")
                    
                    # Wait for scores from other validators
                    logger.info(f"⏳ [V:{self.info.uid}] Waiting for peer validator scores...")
                    await self.cardano_wait_for_peer_scores()
                    
                    # Finalize consensus with all validator scores
                    logger.info(f"🧮 [V:{self.info.uid}] Finalizing consensus with all validator scores...")
                    await self.cardano_finalize_consensus_round()
                    
                    # Update metagraph with consensus results
                    logger.info(f"🔄 [V:{self.info.uid}] Updating metagraph with consensus results...")
                    await self.cardano_update_metagraph_with_consensus()
                    
                    logger.info(f"✅ [V:{self.info.uid}] ===== CONSENSUS ROUND {consensus_round} COMPLETED =====")
                    
                    last_consensus_time = current_time
                    consensus_round += 1
                
                # Short pause between batches
                await asyncio.sleep(5)  # 5 seconds between batches
                
            except Exception as e:
                logger.error(f"❌ [V:{self.info.uid}] Error in synchronized batch {batch_number}: {e}")
                await asyncio.sleep(10)  # Brief pause before retry

    async def cardano_submit_consensus_to_blockchain(self, final_scores: Dict[str, float]):
        """Submit consensus results to Aptos blockchain"""
        logger.info(f"🔗 [V:{self.info.uid}] Submitting {len(final_scores)} consensus scores to blockchain...")
        
        # 🔍 DEBUG: Add detailed logging
        logger.info(f"🔍 [V:{self.info.uid}] DEBUG: final_scores = {final_scores}")
        logger.info(f"🔍 [V:{self.info.uid}] DEBUG: miners_info count = {len(self.miners_info) if self.miners_info else 0}")
        logger.info(f"🔍 [V:{self.info.uid}] DEBUG: contract_address = {self.contract_address}")
        
        try:
            from aptos_sdk.transactions import EntryFunction, TransactionArgument, TransactionPayload
            from aptos_sdk.bcs import Serializer
            
            # Submit each miner's final score to blockchain
            transaction_hashes = []
            
            for miner_uid, consensus_score in final_scores.items():
                try:
                    # Find miner address from uid
                    miner_address = None
                    for uid, miner_info in self.miners_info.items():
                        if uid == miner_uid:
                            miner_address = miner_info.address  # Get actual address from MinerInfo object
                            break
                    
                    if not miner_address:
                        logger.warning(f"⚠️ [V:{self.info.uid}] Miner {miner_uid} address not found, skipping...")
                        continue
                    
                    # Ensure address has 0x prefix
                    if not miner_address.startswith('0x'):
                        miner_address = '0x' + miner_address
                    
                    # Scale score (0.0-1.0 -> 0-100000000)
                    trust_score_scaled = int(consensus_score * 100_000_000)
                    performance_scaled = int(consensus_score * 100_000_000)
                    
                    # Create transaction payload with correct module name and address format
                    from aptos_sdk.account_address import AccountAddress
                    from aptos_sdk.transactions import ModuleId
                    from aptos_sdk.bcs import Serializer
                    
                    # Serialization functions
                    def serialize_address(addr_str: str) -> bytes:
                        """Serialize address"""
                        serializer = Serializer()
                        serializer.struct(AccountAddress.from_str(addr_str))
                        return serializer.output()
                        
                    def serialize_u64(value: int) -> bytes:
                        """Serialize u64"""
                        serializer = Serializer()
                        serializer.u64(value)
                        return serializer.output()
                        
                    def serialize_string(value: str) -> bytes:
                        """Serialize string"""
                        serializer = Serializer()
                        serializer.str(value)
                        return serializer.output()
                    
                    # Create module ID
                    module_id = ModuleId(
                        AccountAddress.from_str(self.contract_address),
                        "full_moderntensor"
                    )
                    
                    # Serialize arguments
                    args = [
                        serialize_address(miner_address),  # address
                        serialize_u64(trust_score_scaled),  # trust score
                        serialize_u64(performance_scaled),  # performance score
                        serialize_u64(0),  # rewards
                        serialize_string(""),  # performance hash
                        serialize_u64(100_000_000),  # weight
                    ]
                    
                    payload = EntryFunction(
                        module_id,
                        "update_miner_performance",
                        [],  # No type arguments
                        args
                    )
                    
                    # Submit transaction
                    signed_txn = await self.aptos_client.create_bcs_signed_transaction(
                        self.account, TransactionPayload(payload)
                    )
                    tx_hash = await self.aptos_client.submit_bcs_transaction(signed_txn)
                    
                    # Wait for confirmation
                    await self.aptos_client.wait_for_transaction(tx_hash)
                    
                    transaction_hashes.append(tx_hash)
                    logger.info(f"✅ [V:{self.info.uid}] Submitted score for {miner_uid}: {consensus_score:.4f} → TX: {tx_hash}")
                    
                except Exception as e:
                    logger.error(f"❌ [V:{self.info.uid}] Failed to submit score for {miner_uid}: {e}")
                    continue
            
            logger.info(f"🎯 [V:{self.info.uid}] Blockchain submission complete: {len(transaction_hashes)}/{len(final_scores)} transactions submitted")
            
        except Exception as e:
            logger.error(f"❌ [V:{self.info.uid}] Blockchain submission error: {e}")

    async def cardano_broadcast_average_scores(self):
        """Calculate and broadcast average scores for current cycle to other validators"""
        logger.info(f"📡 [V:{self.info.uid}] Broadcasting average scores for cycle {self._current_cycle}")
        
        try:
            # Calculate average scores for each miner from all our batches
            miner_averages = {}
            miner_score_counts = defaultdict(list)
            
            # Collect all scores for each miner across all batches
            if self._current_cycle in self.cycle_scores:
                for score_record in self.cycle_scores[self._current_cycle]:
                    miner_uid = score_record["miner_uid"]
                    score = score_record["score"]
                    miner_score_counts[miner_uid].append(score)
            
            # Calculate averages
            for miner_uid, scores in miner_score_counts.items():
                average_score = sum(scores) / len(scores)
                miner_averages[miner_uid] = average_score
                logger.info(f"📊 [V:{self.info.uid}] Average for {miner_uid}: {average_score:.4f} (from {len(scores)} tasks)")
            
            if not miner_averages:
                logger.warning(f"⚠️ [V:{self.info.uid}] No scores to broadcast for cycle {self._current_cycle}")
                return
            
            # Create ValidatorScore objects for P2P broadcast
            broadcast_scores = []
            for miner_uid, avg_score in miner_averages.items():
                score_obj = ValidatorScore(
                    task_id=f"cycle_{self._current_cycle}_average",
                    miner_uid=miner_uid,
                    validator_uid=self.info.uid,
                    score=avg_score,
                    timestamp=time.time()
                )
                broadcast_scores.append(score_obj)
            
            # Broadcast to other validators
            await self.cardano_broadcast_accumulated_scores_to_peers(broadcast_scores)
            
        except Exception as e:
            logger.error(f"❌ [V:{self.info.uid}] Error broadcasting average scores: {e}")

    async def cardano_broadcast_accumulated_scores_to_peers(self, scores: List[ValidatorScore]):
        """Broadcast scores to other validators using P2P"""
        try:
            active_validators = [v for v in self.validators_info.values() if v.uid != self.info.uid and v.api_endpoint]
            
            if not active_validators:
                logger.warning(f"⚠️ [V:{self.info.uid}] No other validators to broadcast to")
                return
            
            # Create broadcast payload
            broadcast_payload = {
                "type": "average_scores",
                "cycle": self._current_cycle,
                "validator_uid": self.info.uid,
                "scores": [score.dict() for score in scores],  # Convert to dict for JSON
                "timestamp": time.time()
            }
            
            logger.info(f"📡 [V:{self.info.uid}] Broadcasting {len(scores)} average scores to {len(active_validators)} validators")
            
            # Send to all validators in parallel
            broadcast_tasks = [
                self.cardano_send_scores(validator, broadcast_payload)
                for validator in active_validators
            ]
            
            results = await asyncio.gather(*broadcast_tasks, return_exceptions=True)
            success_count = sum(1 for r in results if r is True)
            logger.info(f"📡 [V:{self.info.uid}] Average scores broadcast: {success_count}/{len(active_validators)} successful")
            
        except Exception as e:
            logger.error(f"❌ [V:{self.info.uid}] Error broadcasting to peers: {e}")

async def run_validator_node():
    node = None
    try:
        # --- Validate Settings ---
        logger.info("Setting up Validator Node with Aptos...")
        if not settings:
            logger.error("Critical error: Settings not loaded. Please check your configuration file.")
            return

        # Validate required settings
        required_settings = {
            'APTOS_NODE_URL': settings.APTOS_NODE_URL,
            'APTOS_PRIVATE_KEY': settings.APTOS_PRIVATE_KEY,
            'APTOS_CONTRACT_ADDRESS': settings.APTOS_CONTRACT_ADDRESS,
            'HTTP_CLIENT_TIMEOUT': settings.HTTP_CLIENT_TIMEOUT,
            'HTTP_CLIENT_MAX_CONNECTIONS': settings.HTTP_CLIENT_MAX_CONNECTIONS,
            'CONSENSUS_CYCLE_LENGTH': settings.CONSENSUS_CYCLE_LENGTH,
            'CONSENSUS_MAX_RETRIES': settings.CONSENSUS_MAX_RETRIES,
            'CONSENSUS_RETRY_DELAY_SECONDS': settings.CONSENSUS_RETRY_DELAY_SECONDS
        }

        # Check validator API endpoint dynamically
        validator_api_endpoint = settings.get_current_validator_endpoint()
        if not validator_api_endpoint:
            logger.error("No validator API endpoint configured. Please set VALIDATOR_API_ENDPOINT or VALIDATOR_1_API_ENDPOINT")
            return

        missing_settings = [key for key, value in required_settings.items() if value is None]
        if missing_settings:
            logger.error(f"Missing required settings: {', '.join(missing_settings)}")
            return

        # Validate settings format
        if not settings.APTOS_NODE_URL.startswith(('http://', 'https://')):
            logger.error("APTOS_NODE_URL must be a valid HTTP(S) URL")
            return

        if not settings.APTOS_CONTRACT_ADDRESS.startswith('0x'):
            logger.error("APTOS_CONTRACT_ADDRESS must start with '0x'")
            return

        if not validator_api_endpoint.startswith(('http://', 'https://')):
            logger.error("VALIDATOR_API_ENDPOINT must be a valid HTTP(S) URL")
            return

        # Validate numeric settings
        try:
            if settings.HTTP_CLIENT_TIMEOUT <= 0:
                raise ValueError("HTTP_CLIENT_TIMEOUT must be positive")
            if settings.HTTP_CLIENT_MAX_CONNECTIONS <= 0:
                raise ValueError("HTTP_CLIENT_MAX_CONNECTIONS must be positive")
            if settings.CONSENSUS_CYCLE_LENGTH <= 0:
                raise ValueError("CONSENSUS_CYCLE_LENGTH must be positive")
            if settings.CONSENSUS_MAX_RETRIES <= 0:
                raise ValueError("CONSENSUS_MAX_RETRIES must be positive")
            if settings.CONSENSUS_RETRY_DELAY_SECONDS <= 0:
                raise ValueError("CONSENSUS_RETRY_DELAY_SECONDS must be positive")
        except ValueError as e:
            logger.error(f"Invalid numeric setting: {str(e)}")
            return

        # --- Initialize Aptos context ---
        from mt_aptos.aptos_core.context import get_aptos_context
        
        try:
            # Get Aptos context (client, account)
            contract_client, aptos_client, account = await get_aptos_context(
                node_url=settings.APTOS_NODE_URL,
                private_key=settings.APTOS_PRIVATE_KEY,
                contract_address=settings.APTOS_CONTRACT_ADDRESS
            )
            
            if not contract_client or not aptos_client or not account:
                logger.error("Failed to initialize Aptos context: One or more required components are missing")
                return
                
            logger.info(f"Successfully connected to Aptos network with address: {account.address()}")
            
            # --- Get validator info ---
            from mt_aptos.aptos_core.validator_helper import get_validator_info
            
            # Using account address as validator address
            validator_address = account.address().hex()
            if not validator_address.startswith("0x"):
                validator_address = f"0x{validator_address}"
            
            validator_data = await get_validator_info(
                aptos_client, 
                settings.APTOS_CONTRACT_ADDRESS, 
                validator_address
            )
            
            if not validator_data:
                logger.error(
                    f"Failed to retrieve validator data for address {validator_address}. "
                    "Please ensure you are registered as a validator on the network."
                )
                return
                
            # Construct ValidatorInfo object
            from mt_aptos.core.datatypes import ValidatorInfo
            
            validator_info = ValidatorInfo(
                uid=validator_data.get("uid", ""),
                address=validator_address,
                api_endpoint=validator_api_endpoint
            )
            
            if not validator_info.uid:
                logger.error("Invalid validator UID received from network. Please check your registration status.")
                return
                
            logger.info(f"Successfully loaded validator info: UID={validator_info.uid}, Address={validator_address}")
            
            # --- Initialize validator node ---
            node = ValidatorNode(
                validator_info=validator_info,
                aptos_client=aptos_client,
                account=account,
                contract_address=settings.APTOS_CONTRACT_ADDRESS
            )
            
            # --- Run main loop ---
            logger.info("Starting validator node main loop...")
            await node.run()
            
        except Exception as e:
            logger.error(
                f"Error during Aptos context setup: {str(e)}\n"
                "Please check your network connection and configuration settings."
            )
            return
    except Exception as e:
        logger.error(
            f"Critical error during validator node setup: {str(e)}\n"
            "Please check the logs for more details and ensure all required components are properly configured."
        )
    finally:
        # Clean up resources if necessary
        if node and hasattr(node, "http_client"):
            try:
                await node.http_client.aclose()
                logger.info("Successfully closed HTTP client connection")
            except Exception as e:
                logger.error(f"Error closing HTTP client: {str(e)}")
        logger.info("Validator node shutdown complete.")


async def create_and_run_validator_sequential(
    validator_name: str = "validator",
    batch_wait_time: float = 30.0,
    auto_password: str = "default123"
) -> None:
    """
    Factory function để tạo và chạy ValidatorNode với sequential batch mode
    Tự động tạo account nếu chưa có và sử dụng cấu hình tối ưu.
    
    Args:
        validator_name: Tên account validator 
        batch_wait_time: Thời gian đợi cho sequential mode (seconds)
        auto_password: Mật khẩu tự động để tạo account
    """
    from mt_aptos.keymanager.account_manager import AccountKeyManager
    from aptos_sdk.async_client import RestClient
    from mt_aptos.core.datatypes import ValidatorInfo
    import os
    
    # Load environment settings 
    from moderntensor.mt_aptos.config.settings import Settings
    settings = Settings()
    
    # Hiển thị cấu hình
    print("╭───────────────────────────────────╮")
    print("│ 🔄 ModernTensor Aptos Validator  │")
    print("│       SEQUENTIAL BATCH MODE       │")
    print("╰───────────────────────────────────╯")
    print("📋 Configuration:")
    print("   • Mode: Sequential Batch Processing")
    print(f"   • Wait Time: {batch_wait_time} seconds max per batch")
    print("   • Scoring: Immediate after results")
    print("   • Next Batch: 2 seconds after scoring")
    print()
    
    # Initialize account manager và tự động tạo account nếu cần
    account_manager = AccountKeyManager()
    
    try:
        # Sử dụng load_or_create_account thay vì load_account
        validator_account = account_manager.load_or_create_account(
            validator_name, 
            auto_password=auto_password
        )
        logger.info(f"✅ Validator account loaded/created: {validator_account.address()}")
    except Exception as e:
        logger.error(f"❌ Failed to load/create validator account: {e}")
        raise
    
    # Initialize Aptos client
    aptos_client = RestClient(settings.APTOS_NODE_URL)
    
    # Create validator info
    validator_info = ValidatorInfo(
        uid=validator_name,
        address=str(validator_account.address()),
        api_endpoint=settings.VALIDATOR_API_ENDPOINT or "http://127.0.0.1:8080"
    )
    
    # Create ValidatorNode với sequential consensus mode 
    node = ValidatorNode(
        validator_info=validator_info,
        aptos_client=aptos_client,
        account=validator_account,
        contract_address=settings.APTOS_CONTRACT_ADDRESS,
        consensus_mode="sequential",  # Force sequential mode
        batch_wait_time=batch_wait_time
    )
    
    # Log configuration
    logger.info(f"🎯 Validator configured:")
    logger.info(f"   • Name: {validator_name}")
    logger.info(f"   • Mode: sequential batch processing")
    logger.info(f"   • Address: {validator_account.address()}")
    logger.info(f"   • Batch wait: {batch_wait_time}s")
    
    # Start node
    await node.run()


async def create_and_run_validator_continuous(
    validator_name: str = "validator",
    auto_password: str = "default123"
) -> None:
    """
    Factory function để tạo và chạy ValidatorNode với continuous slot-based mode
    
    Args:
        validator_name: Tên account validator
        auto_password: Mật khẩu tự động để tạo account
    """
    from mt_aptos.keymanager.account_manager import AccountKeyManager
    from aptos_sdk.async_client import RestClient
    from mt_aptos.core.datatypes import ValidatorInfo
    
    # Load environment settings
    from moderntensor.mt_aptos.config.settings import Settings
    settings = Settings()
    
    # Hiển thị cấu hình
    print("╭───────────────────────────────────╮")
    print("│ 🔄 ModernTensor Aptos Validator  │")
    print("│      CONTINUOUS SLOT MODE         │")
    print("╰───────────────────────────────────╯")
    print("📋 Configuration:")
    print("   • Mode: Continuous Slot-Based Processing")
    print("   • Slot Duration: 20 minutes")
    print("   • Phases: Assignment → Execution → Consensus → Update")
    print()
    
    # Initialize account manager và tự động tạo account nếu cần
    account_manager = AccountKeyManager()
    
    try:
        validator_account = account_manager.load_or_create_account(
            validator_name,
            auto_password=auto_password
        )
        logger.info(f"✅ Validator account loaded/created: {validator_account.address()}")
    except Exception as e:
        logger.error(f"❌ Failed to load/create validator account: {e}")
        raise
    
    # Initialize Aptos client
    aptos_client = RestClient(settings.APTOS_NODE_URL)
    
    # Create validator info
    validator_info = ValidatorInfo(
        uid=validator_name,
        address=str(validator_account.address()),
        api_endpoint=settings.VALIDATOR_API_ENDPOINT or "http://127.0.0.1:8080"
    )
    
    # Create ValidatorNode với continuous consensus mode
    node = ValidatorNode(
        validator_info=validator_info,
        aptos_client=aptos_client,
        account=validator_account,
        contract_address=settings.APTOS_CONTRACT_ADDRESS,
        consensus_mode="continuous",  # Force continuous mode
        batch_wait_time=30.0  # Not used in continuous mode
    )
    
    # Log configuration
    logger.info(f"🎯 Validator configured:")
    logger.info(f"   • Name: {validator_name}")
    logger.info(f"   • Mode: continuous slot-based")
    logger.info(f"   • Address: {validator_account.address()}")
    
    # Start node
    await node.run()
