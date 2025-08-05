#!/usr/bin/env python3
"""
ValidatorNode Consensus Module for Core Blockchain

This module handles all consensus-related functionality for ValidatorNode including:
- Result scoring and evaluation
- P2P consensus coordination between validators
- Score broadcasting and collection
- Consensus finalization and agreement
- Core blockchain submission of consensus results
- Bitcoin staking integration for validator rewards

The consensus module ensures validators reach agreement on miner performance scores.
"""

import asyncio
import logging
import time
from collections import defaultdict
from typing import Dict, List, Optional, Any, Union

import httpx
from web3 import Web3
from eth_account import Account

from ..core.datatypes import (
    ValidatorScore,
    MinerResult,
    ValidatorInfo,
    TaskAssignment,
)

# Import TaskModel from network.server (miner-compatible format)
from ..network.server import TaskModel
from ..formulas.incentive import calculate_miner_incentive
from ..formulas.performance import calculate_adjusted_miner_performance
from ..formulas.trust_score import update_trust_score
from .scoring import score_results_logic, broadcast_scores_logic
from .slot_coordinator import SlotPhase
from ..core_client.contract_client import ModernTensorCoreClient
from .modern_consensus import (
    ModernConsensus,
    NetworkMetrics,
    format_consensus_results,
)

logger = logging.getLogger(__name__)

# Constants - Adjusted for 3.5 minute cycles
CONSENSUS_TIMEOUT = 60  # Reduced from 120s to 60s for faster cycles
SCORE_BROADCAST_TIMEOUT = 20  # Reduced from 30s to 20s
SCORE_COLLECTION_TIMEOUT = 50  # Reduced from 90s to 50s
MIN_VALIDATORS_FOR_CONSENSUS = 2
MAJORITY_THRESHOLD = 2  # Minimum validators for majority consensus
HTTP_TIMEOUT = 20.0  # Increased from 10.0s to 20.0s for better task assignment

# Core blockchain constants
CORE_BLOCK_TIME = 3  # 3 seconds average
CORE_CONFIRMATION_BLOCKS = 12  # Number of blocks for confirmation
BITCOIN_STAKING_EPOCHS = 144  # Blocks per epoch for Bitcoin staking rewards


class ValidatorNodeConsensus:
    """
    Consensus functionality for ValidatorNode on Core blockchain.

    This class handles:
    - Scoring of miner results
    - P2P consensus coordination
    - Score broadcasting and collection
    - Consensus finalization
    - Core blockchain submission
    - Bitcoin staking reward distribution
    """

    def __init__(self, core_node):
        """
        Initialize consensus management with reference to core node.

        Args:
            core_node: Reference to the ValidatorNodeCore instance
        """
        self.core = core_node
        self.uid_prefix = core_node.uid_prefix

        # Core blockchain client
        self.core_client: Optional[ModernTensorCoreClient] = None

        # Bitcoin staking tracking
        self.bitcoin_staking_rewards = {}
        self.staking_epoch_data = {}

        # === MODERN CONSENSUS INTEGRATION ===
        self.modern_consensus_engine: Optional[ModernConsensus] = None
        self.modern_consensus_enabled = True
        self.use_modern_consensus_algorithms = True

        # === FLEXIBLE CONSENSUS EXTENSIONS ===
        self.flexible_mode_enabled = False
        self.consensus_participation_rate = 1.0
        self.last_successful_consensus = None
        self.auto_adapt_timing = True
        self.flexible_metrics = {
            "mid_slot_joins": 0,
            "auto_extensions_used": 0,
            "consensus_below_threshold": 0,
            "total_consensus_attempts": 0,
        }

        # Initialize Core client if account is available
        if hasattr(core_node, "account") and core_node.account:
            self._initialize_core_client()

        # Initialize Modern consensus engine after Core client is ready
        self._initialize_modern_consensus_engine()

    def _initialize_core_client(self):
        """Initialize Core blockchain client for consensus operations."""
        try:
            from ..core_client.contract_client import ModernTensorCoreClient
            from web3 import Web3
            from eth_account import Account
            import os

            # Initialize Web3 connection
            core_node_url = "https://rpc.test2.btcs.network"
            w3 = Web3(Web3.HTTPProvider(core_node_url))

            # Get environment variables
            contract_address = os.getenv("CORE_CONTRACT_ADDRESS")
            private_key = os.getenv("VALIDATOR_1_PRIVATE_KEY") or os.getenv(
                "VALIDATOR_2_PRIVATE_KEY"
            )

            if not contract_address:
                raise ValueError("CORE_CONTRACT_ADDRESS environment variable not set")
            if not private_key:
                raise ValueError("VALIDATOR_PRIVATE_KEY environment variable not set")

            account = Account.from_key(private_key)

            # Initialize ModernTensorCoreClient with transaction capabilities
            self.core_client = ModernTensorCoreClient(
                w3=w3, contract_address=contract_address, account=account
            )

            logger.info(
                f"✅ {self.uid_prefix} ModernTensorCoreClient initialized successfully with account {account.address}"
            )

        except Exception as e:
            logger.error(f"❌ {self.uid_prefix} Failed to initialize Core client: {e}")
            self.core_client = None

    def _initialize_modern_consensus_engine(self):
        """Initialize Modern consensus engine for enhanced algorithms."""
        try:
            if self.core_client and self.modern_consensus_enabled:
                from ..config.settings import Settings

                # Get settings
                settings = Settings() if hasattr(Settings, "__call__") else None

                # Initialize Modern consensus engine with Core client
                self.modern_consensus_engine = ModernConsensus(
                    core_client=self.core_client, settings=settings
                )

                logger.info(
                    f"✅ {self.uid_prefix} ModernTensor consensus engine initialized successfully"
                )

            else:
                logger.warning(
                    f"⚠️ {self.uid_prefix} Modern consensus engine not initialized - Core client required"
                )
                self.modern_consensus_enabled = False

        except Exception as e:
            logger.error(
                f"❌ {self.uid_prefix} Failed to initialize Modern consensus engine: {e}"
            )
            self.modern_consensus_engine = None
            self.modern_consensus_enabled = False

    # === Scoring Methods ===

    def score_miner_results(self):
        """Score all miner results using the configured scoring logic."""
        logger.info(
            f"{self.uid_prefix} Scoring miner results for cycle {self.core.current_cycle}"
        )

        # Convert results_buffer to the expected format for score_results_logic
        # results_buffer is Dict[str, MinerResult], need Dict[str, List[MinerResult]]
        results_received = {}
        for task_id, result in self.core.results_buffer.items():
            results_received[task_id] = [result]

        # Use the scoring logic from the scoring module
        scores_dict = score_results_logic(
            results_received=results_received,
            tasks_sent=self.core.tasks_sent,
            validator_uid=self.core.info.uid,
            validator_instance=getattr(self.core, "validator_instance", None),
        )

        # Flatten scores dict to list
        scores = []
        for task_id, scores_list in scores_dict.items():
            scores.extend(scores_list)

        # Store scores
        for score in scores:
            self.core.cycle_scores[score.task_id].append(score)

        logger.info(
            f"{self.uid_prefix} Generated {len(scores)} scores for cycle {self.core.current_cycle}"
        )
        return scores

    async def core_score_results(self, slot: int):
        """
        Score results for Core blockchain slot-based consensus.

        Args:
            slot: Current slot number
        """
        logger.info(f"{self.uid_prefix} Scoring results for slot {slot}")

        slot_scores = []

        # Score each result in the buffer
        for task_id, result in self.core.results_buffer.items():
            if task_id in self.core.tasks_sent:
                assignment = self.core.tasks_sent[task_id]

                try:
                    # Check if this is a timeout result
                    if isinstance(result.result_data, dict) and result.result_data.get(
                        "timeout"
                    ):
                        score_value = 0.0  # Timeout gets 0 score
                        logger.warning(
                            f"{self.uid_prefix} Task {task_id} timeout - assigning 0 score to miner {result.miner_uid}"
                        )
                    else:
                        # Calculate score using the scoring algorithm
                        score_value = self._calculate_score(
                            assignment.task_data, result.result_data
                        )

                    # Create validator score
                    validator_score = ValidatorScore(
                        task_id=task_id,
                        miner_uid=result.miner_uid,
                        validator_uid=self.core.info.uid,
                        score=score_value,
                        timestamp=time.time(),
                        cycle=slot,  # Use slot as cycle for Core blockchain consensus
                    )

                    slot_scores.append(validator_score)

                except Exception as e:
                    logger.error(
                        f"{self.uid_prefix} Error scoring result for task {task_id}: {e}"
                    )

        # Store slot scores
        self.core.slot_scores[slot] = slot_scores

        logger.info(
            f"{self.uid_prefix} Generated {len(slot_scores)} scores for slot {slot}"
        )

    def _calculate_score(self, task_data: Dict, result_data: Dict) -> float:
        """
        Calculate score for a task-result pair.

        Args:
            task_data: Task data
            result_data: Result data

        Returns:
            Score value between 0.0 and 1.0
        """
        try:
            # Basic scoring algorithm - can be overridden by subnet-specific logic

            # Check if result matches expected format
            if not isinstance(result_data, dict):
                return 0.0

            # Check for required fields
            required_fields = ["result", "timestamp", "miner_uid"]
            for field in required_fields:
                if field not in result_data:
                    return 0.1  # Partial credit for attempting

            # Check timing (penalize very late responses)
            if "timestamp" in task_data and "timestamp" in result_data:
                task_time = task_data["timestamp"]
                result_time = result_data["timestamp"]

                if result_time < task_time:
                    return 0.0  # Invalid timestamp

                response_time = result_time - task_time
                max_time = 300  # 5 minutes max

                if response_time > max_time:
                    return 0.2  # Very late response

                # Time bonus: faster responses get higher scores
                time_factor = max(0, 1 - (response_time / max_time))
                base_score = 0.8  # Base score for correct format

                return base_score + (0.2 * time_factor)

            return 0.5  # Default score when timing info is unavailable

        except Exception as e:
            logger.error(f"{self.uid_prefix} Error in score calculation: {e}")
            return 0.0

    def core_calculate_score(
        self, task_data: Dict[str, Any], result_data: Dict[str, Any]
    ) -> float:
        """
        Calculate score for a Core blockchain consensus task result.

        This is a simplified scoring function that can be overridden by subnet-specific validators.

        Args:
            task_data: The original task data sent to the miner
            result_data: The result data received from the miner

        Returns:
            Score value between 0.0 and 1.0
        """
        try:
            # Basic validation - ensure result is not empty
            if not result_data:
                logger.warning(f"{self.uid_prefix} Empty result data received")
                return 0.0

            # Basic scoring logic - can be overridden by subnet validators
            score = 0.5  # Default baseline score

            # Check if result has required fields
            if isinstance(result_data, dict):
                # Award points for having proper structure
                if "status" in result_data:
                    score += 0.2
                if "data" in result_data:
                    score += 0.2
                if "timestamp" in result_data:
                    score += 0.1

                # Check if task was completed successfully
                if result_data.get("status") == "success":
                    score += 0.0  # Already at 1.0 if all fields present
                elif result_data.get("status") == "completed":
                    score += 0.0  # Alternative success status
                else:
                    score *= 0.5  # Penalize if not successful

            # Ensure score is within valid range
            score = max(0.0, min(1.0, score))

            logger.debug(
                f"{self.uid_prefix} Calculated score {score:.3f} for task result"
            )
            return score

        except Exception as e:
            logger.error(f"{self.uid_prefix} Error calculating score: {e}")
            return 0.0  # Return 0 score on error

    # === Consensus Coordination Methods ===

    async def _collect_local_scores_for_consensus(self, slot: int) -> Dict[str, float]:
        """
        Collect local scores for consensus coordination.

        Args:
            slot: Slot number

        Returns:
            Dictionary mapping miner UID to score
        """
        local_scores = {}

        # Prioritize slot_scores if available
        if slot in self.core.slot_scores and self.core.slot_scores[slot]:
            for score in self.core.slot_scores[slot]:
                local_scores[score.miner_uid] = score.score
            logger.info(
                f"{self.uid_prefix} Collected {len(local_scores)} local scores from slot_scores for slot {slot}"
            )

        # Fallback to cycle_scores if slot_scores not available
        elif self.core.cycle_scores:
            for task_id, scores_list in self.core.cycle_scores.items():
                if scores_list:
                    latest_score = scores_list[-1]
                    local_scores[latest_score.miner_uid] = latest_score.score
            logger.info(
                f"{self.uid_prefix} Collected {len(local_scores)} local scores from cycle_scores for slot {slot}"
            )

        # Fallback to validator_scores
        elif self.core.validator_scores:
            for task_id, scores_list in self.core.validator_scores.items():
                if scores_list:
                    latest_score = scores_list[-1]
                    local_scores[latest_score.miner_uid] = latest_score.score
            logger.info(
                f"{self.uid_prefix} Collected {len(local_scores)} local scores from validator_scores for slot {slot}"
            )

        else:
            logger.warning(
                f"{self.uid_prefix} No local scores available for consensus in slot {slot}"
            )

        return local_scores

    async def _coordinate_synchronized_metagraph_update(
        self, slot: int, local_scores: Dict[str, float]
    ) -> bool:
        """
        Coordinate synchronized metagraph update using slot coordinator.

        Args:
            slot: Current slot number
            local_scores: Local validator scores

        Returns:
            True if successful, False otherwise
        """
        logger.info(
            f"{self.uid_prefix} Coordinating synchronized metagraph update for slot {slot}"
        )

        try:
            # Check consensus mode
            consensus_mode = getattr(self.core, "consensus_mode", "continuous")

            if consensus_mode == "synchronized":
                # Wait for all validators to reach consensus phase
                await self._wait_for_validator_coordination(slot)

                # Verify we have sufficient validator participation
                if not await self._check_validator_participation(slot):
                    logger.warning(
                        f"{self.uid_prefix} Insufficient validator participation for slot {slot}"
                    )
                    return False

                # Use slot coordinator for consensus if available
                if hasattr(self.core, "slot_coordinator") and hasattr(
                    self.core.slot_coordinator, "coordinate_consensus_round"
                ):
                    consensus_scores = (
                        await self.core.slot_coordinator.coordinate_consensus_round(
                            slot, local_scores
                        )
                    )
                else:
                    # Fallback: Use our own consensus aggregation
                    consensus_scores = await self._manual_consensus_coordination(
                        slot, local_scores
                    )

                if consensus_scores:
                    # Apply consensus scores to metagraph
                    await self._apply_consensus_scores_to_metagraph(
                        slot, consensus_scores
                    )
                    logger.info(
                        f"{self.uid_prefix} Synchronized metagraph update completed for slot {slot}"
                    )
                    return True
                else:
                    logger.warning(
                        f"{self.uid_prefix} No consensus reached for slot {slot}"
                    )
                    return False
            else:
                # For continuous/flexible mode, proceed immediately
                logger.info(
                    f"{self.uid_prefix} Using {consensus_mode} consensus mode - proceeding without coordination"
                )
                await self._apply_consensus_scores_to_metagraph(slot, local_scores)
                return True

        except Exception as e:
            logger.error(
                f"{self.uid_prefix} Error in synchronized metagraph update: {e}"
            )
            return False

    async def _wait_for_validator_coordination(self, slot: int, timeout: float = 30.0):
        """
        Wait for other validators to reach consensus phase.

        Args:
            slot: Current slot number
            timeout: Maximum time to wait in seconds
        """
        try:
            logger.info(
                f"{self.uid_prefix} Waiting for validator coordination for slot {slot}"
            )

            start_time = time.time()
            min_validators = getattr(
                self.core.settings, "min_validators_for_consensus", 2
            )

            while time.time() - start_time < timeout:
                # Check how many validators have reached consensus phase
                active_validators = await self._get_active_validators()
                participating_validators = len(
                    [v for v in active_validators if v.uid != self.core.info.uid]
                )

                if (
                    participating_validators >= min_validators - 1
                ):  # -1 because we don't count ourselves
                    logger.info(
                        f"{self.uid_prefix} Sufficient validators ready for consensus: {participating_validators + 1}"
                    )
                    return True

                await asyncio.sleep(2.0)  # Check every 2 seconds

            logger.warning(
                f"{self.uid_prefix} Timeout waiting for validator coordination"
            )
            return False

        except Exception as e:
            logger.error(
                f"{self.uid_prefix} Error waiting for validator coordination: {e}"
            )
            return False

    async def _check_validator_participation(self, slot: int) -> bool:
        """
        Check if we have sufficient validator participation for consensus.

        Args:
            slot: Current slot number

        Returns:
            True if sufficient participation
        """
        try:
            # Count active validators
            active_validators = await self._get_active_validators()
            total_validators = len(active_validators)

            # Count validators with scores for this slot/cycle
            current_cycle = self.core.current_cycle
            participating_validators = 1  # Count ourselves

            if current_cycle in self.core.received_validator_scores:
                participating_validators += len(
                    self.core.received_validator_scores[current_cycle]
                )

            # Check if we have minimum participation
            min_validators = getattr(
                self.core.settings, "min_validators_for_consensus", 2
            )
            required_percentage = getattr(
                self.core.settings, "required_consensus_percentage", 0.6
            )

            min_required = max(
                min_validators, int(total_validators * required_percentage)
            )

            logger.info(
                f"{self.uid_prefix} Validator participation: {participating_validators}/{total_validators} "
                f"(required: {min_required})"
            )

            return participating_validators >= min_required

        except Exception as e:
            logger.error(
                f"{self.uid_prefix} Error checking validator participation: {e}"
            )
            return False

    async def _manual_consensus_coordination(
        self, slot: int, local_scores: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Manual consensus coordination as fallback when slot_coordinator is not available.

        Args:
            slot: Current slot number
            local_scores: Local validator scores

        Returns:
            Consensus scores
        """
        try:
            logger.info(
                f"{self.uid_prefix} Using manual consensus coordination for slot {slot}"
            )

            # Combine local scores with received P2P scores
            consensus_scores = {}

            # Start with local scores
            for miner_uid, score in local_scores.items():
                consensus_scores[miner_uid] = [score]

            # Add P2P scores
            current_cycle = self.core.current_cycle
            if current_cycle in self.core.received_validator_scores:
                p2p_scores = self.core.received_validator_scores[current_cycle]

                for validator_uid, validator_scores in p2p_scores.items():
                    for task_id, score_obj in validator_scores.items():
                        miner_uid = score_obj.miner_uid
                        score_value = score_obj.score

                        if miner_uid not in consensus_scores:
                            consensus_scores[miner_uid] = []
                        consensus_scores[miner_uid].append(score_value)

            # Apply Modern consensus-enhanced consensus if available
            if self.modern_consensus_enabled and self.modern_consensus_engine:
                final_consensus = await self._apply_modern_consensus(
                    slot, consensus_scores, current_cycle
                )
            else:
                # Fallback to simple averaging
                final_consensus = {}
                for miner_uid, scores_list in consensus_scores.items():
                    if scores_list:
                        final_consensus[miner_uid] = sum(scores_list) / len(scores_list)
                        logger.debug(
                            f"{self.uid_prefix} Manual consensus for {miner_uid}: "
                            f"{final_consensus[miner_uid]:.4f} (from {len(scores_list)} validators)"
                        )

            logger.info(
                f"{self.uid_prefix} {'ModernTensor-enhanced' if self.modern_consensus_enabled else 'Simple'} consensus completed: {len(final_consensus)} miners"
            )
            return final_consensus

        except Exception as e:
            logger.error(
                f"{self.uid_prefix} Error in manual consensus coordination: {e}"
            )
            return {}

    async def _apply_modern_consensus(
        self, slot: int, consensus_scores: Dict[str, List[float]], current_cycle: int
    ) -> Dict[str, float]:
        """
        Apply ModernTensor-enhanced consensus algorithms.

        Args:
            slot: Current slot number
            consensus_scores: Dict of miner_uid -> list of scores from validators
            current_cycle: Current consensus cycle

        Returns:
            Enhanced consensus scores using ModernTensor algorithms
        """
        try:
            logger.info(
                f"🧠 {self.uid_prefix} Applying ModernTensor consensus algorithms for slot {slot}"
            )

            # Convert scores format for Modern consensus engine
            # consensus_scores: {miner_uid: [score1, score2, ...]}
            # Need: {miner_uid: {validator_uid: score}}
            miner_evaluations = {}

            # Get validator information for weight calculation
            active_validators = await self._get_active_validators()
            validator_weights = {}

            # Calculate validator weights based on stake and trust
            for validator in active_validators:
                if hasattr(validator, "stake") and hasattr(validator, "trust_score"):
                    # Simple weight calculation - can be enhanced
                    # Enhanced weight calculation with dual token staking
                    core_weight = validator.stake * validator.trust_score
                    btc_weight = (
                        getattr(validator, "bitcoin_stake", 0)
                        * 2.0
                        * validator.trust_score
                    )
                    weight = core_weight + btc_weight
                    validator_weights[validator.uid] = weight
                else:
                    validator_weights[validator.uid] = 1.0  # Default weight

            # Normalize validator weights
            total_weight = sum(validator_weights.values())
            if total_weight > 0:
                for uid in validator_weights:
                    validator_weights[uid] = validator_weights[uid] / total_weight

            # Convert consensus_scores to format expected by Modern consensus
            for miner_uid, scores_list in consensus_scores.items():
                miner_evaluations[miner_uid] = {}

                # Assign scores to validators (simplified mapping)
                validator_uids = list(validator_weights.keys())
                for i, score in enumerate(scores_list):
                    if i < len(validator_uids):
                        validator_uid = validator_uids[i]
                        miner_evaluations[miner_uid][validator_uid] = score

            # Apply Modern consensus algorithm
            final_scores = self.modern_consensus_engine.apply_consensus_algorithm(
                miner_evaluations, validator_weights
            )

            # Calculate incentives using ModernTensor formulas
            if self.use_modern_consensus_algorithms:
                # Get miner information for incentive calculation
                miners_info = {}
                for miner_uid in final_scores.keys():
                    if miner_uid in self.core.miners_info:
                        miner_info = self.core.miners_info[miner_uid]
                        miners_info[miner_uid] = {
                            "stake": getattr(
                                miner_info, "stake", 1000000
                            ),  # Default stake
                            "bitcoin_stake": getattr(miner_info, "bitcoin_stake", 0),
                            "trust_score": getattr(miner_info, "trust_score", 0.5),
                        }

                # Calculate ModernTensor incentives
                if miners_info:
                    incentives = self.modern_consensus_engine.calculate_incentives(
                        final_scores, miners_info
                    )

                    logger.info(
                        f"💰 {self.uid_prefix} Calculated ModernTensor incentives for {len(incentives)} miners"
                    )

                    # Store incentives for later distribution
                    self._store_modern_consensus_incentives(slot, incentives)

            logger.info(
                f"✅ {self.uid_prefix} ModernTensor consensus completed with {len(final_scores)} final scores"
            )
            return final_scores

        except Exception as e:
            logger.error(f"❌ {self.uid_prefix} Error in ModernTensor consensus: {e}")

            # Fallback to simple averaging
            fallback_scores = {}
            for miner_uid, scores_list in consensus_scores.items():
                if scores_list:
                    fallback_scores[miner_uid] = sum(scores_list) / len(scores_list)

            logger.warning(
                f"⚠️ {self.uid_prefix} Using fallback consensus for {len(fallback_scores)} miners"
            )
            return fallback_scores

    def _store_modern_consensus_incentives(
        self, slot: int, incentives: Dict[str, float]
    ):
        """Store ModernTensor incentives for later blockchain submission."""
        try:
            # Store in internal structure for later use
            if not hasattr(self, "modern_consensus_incentives"):
                self.modern_consensus_incentives = {}

            self.modern_consensus_incentives[slot] = {
                "incentives": incentives,
                "timestamp": time.time(),
                "total_rewards": sum(incentives.values()),
            }

            logger.debug(
                f"💾 {self.uid_prefix} Stored ModernTensor incentives for slot {slot}"
            )

        except Exception as e:
            logger.error(
                f"❌ {self.uid_prefix} Error storing ModernTensor incentives: {e}"
            )

    async def _apply_consensus_scores_to_metagraph(
        self, slot: int, consensus_scores: Dict[str, float]
    ):
        """
        Apply consensus scores to metagraph using exponential moving average.

        Args:
            slot: Current slot number
            consensus_scores: Consensus scores from all validators
        """
        logger.info(
            f"{self.uid_prefix} Applying consensus scores to metagraph for slot {slot}"
        )

        try:
            alpha = 0.2  # Learning rate for exponential moving average

            for miner_uid, consensus_score in consensus_scores.items():
                if miner_uid in self.core.miners_info:
                    miner_info = self.core.miners_info[miner_uid]

                    # Update trust score using exponential moving average
                    old_trust_score = getattr(miner_info, "trust_score", 0.5)
                    new_trust_score = update_trust_score(
                        old_trust_score, consensus_score, alpha
                    )

                    miner_info.trust_score = new_trust_score

                    logger.debug(
                        f"{self.uid_prefix} Updated miner {miner_uid} trust score: "
                        f"{old_trust_score:.3f} → {new_trust_score:.3f}"
                    )

            logger.info(
                f"{self.uid_prefix} Applied {len(consensus_scores)} consensus scores to metagraph"
            )

        except Exception as e:
            logger.error(
                f"{self.uid_prefix} Error applying consensus scores to metagraph: {e}"
            )

    # === Score Broadcasting Methods ===

    async def broadcast_scores(
        self, scores_to_broadcast: Dict[str, List[ValidatorScore]]
    ):
        """
        Broadcast scores to other validators.

        Args:
            scores_to_broadcast: Dictionary mapping validator UID to list of scores
        """
        logger.info(f"{self.uid_prefix} Broadcasting scores to peer validators")

        try:
            # Flatten scores from dict format to single list
            all_scores = []
            for validator_uid, score_list in scores_to_broadcast.items():
                all_scores.extend(score_list)

            if not all_scores:
                logger.warning(f"{self.uid_prefix} No scores to broadcast")
                return

            # Get active validators for broadcasting
            active_validators = await self._get_active_validators()
            target_validators = [
                v for v in active_validators if v.uid != self.core.info.uid
            ]

            if not target_validators:
                logger.warning(
                    f"{self.uid_prefix} No target validators for broadcasting"
                )
                return

            # Create broadcast tasks for all validators
            broadcast_tasks = []
            broadcast_id = f"broadcast_{int(time.time())}_{len(all_scores)}"

            for validator in target_validators:
                task = self._send_scores_to_validator_p2p(
                    validator, all_scores, broadcast_id
                )
                broadcast_tasks.append((validator.uid, task))

            # Execute broadcasts concurrently
            results = await asyncio.gather(
                *[task for _, task in broadcast_tasks], return_exceptions=True
            )

            # Process results
            success_count = 0
            for i, result in enumerate(results):
                validator_uid = broadcast_tasks[i][0]

                if isinstance(result, Exception):
                    logger.error(
                        f"{self.uid_prefix} Broadcast failed to {validator_uid}: {result}"
                    )
                elif result:
                    success_count += 1
                    logger.debug(
                        f"{self.uid_prefix} Scores sent successfully to {validator_uid}"
                    )
                else:
                    logger.warning(
                        f"{self.uid_prefix} Failed to send scores to {validator_uid}"
                    )

            logger.info(
                f"{self.uid_prefix} Broadcast completed: {success_count}/{len(target_validators)} validators reached"
            )

        except Exception as e:
            logger.error(f"{self.uid_prefix} Error broadcasting scores: {e}")

    async def _send_scores_to_validator_p2p(
        self, validator: ValidatorInfo, scores: List[ValidatorScore], broadcast_id: str
    ) -> bool:
        """
        Send scores to a specific validator via P2P HTTP.

        Args:
            validator: Target validator info
            scores: List of scores to send
            broadcast_id: Unique broadcast identifier

        Returns:
            True if successfully sent
        """
        try:
            validator_endpoint = getattr(validator, "api_endpoint", None)
            if not validator_endpoint:
                logger.warning(
                    f"{self.uid_prefix} No API endpoint for validator {validator.uid}"
                )
                return False

            # Prepare score data for transmission
            scores_data = []
            for score in scores:
                scores_data.append(
                    {
                        "task_id": score.task_id,
                        "miner_uid": score.miner_uid,
                        "score": score.score,
                        "timestamp": score.timestamp,
                        "validator_uid": score.validator_uid,
                        "cycle": getattr(score, "cycle", 0),
                    }
                )

            # Create request payload
            payload = {
                "broadcast_id": broadcast_id,
                "sender_uid": self.core.info.uid,
                "scores": scores_data,
                "timestamp": int(time.time()),
            }

            # Send HTTP request
            url = f"{validator_endpoint.rstrip('/')}/consensus/receive_scores"

            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    logger.debug(
                        f"{self.uid_prefix} Successfully sent {len(scores)} scores to {validator.uid}"
                    )
                    return True
                else:
                    logger.warning(
                        f"{self.uid_prefix} Failed to send scores to {validator.uid}: "
                        f"HTTP {response.status_code}"
                    )
                    return False

        except Exception as e:
            logger.error(
                f"{self.uid_prefix} Error sending scores to {validator.uid}: {e}"
            )
            return False

    async def core_broadcast_scores(self, slot: int):
        """
        Broadcast scores for Core blockchain consensus.

        Args:
            slot: Current slot number
        """
        logger.info(f"{self.uid_prefix} Broadcasting scores for slot {slot}")

        if slot not in self.core.slot_scores:
            logger.warning(f"{self.uid_prefix} No scores to broadcast for slot {slot}")
            return

        scores = self.core.slot_scores[slot]

        # Prepare broadcast payload
        payload = {
            "validator_uid": self.core.info.uid,
            "slot": slot,
            "scores": [
                {
                    "task_id": score.task_id,
                    "miner_uid": score.miner_uid,
                    "score": score.score,
                    "timestamp": score.timestamp,
                }
                for score in scores
            ],
            "timestamp": time.time(),
        }

        # Get active validators
        active_validators = await self._get_active_validators()

        # Send to each validator
        send_tasks = []
        for validator in active_validators:
            if validator.uid != self.core.info.uid:  # Don't send to self
                send_tasks.append(self._send_scores_to_validator(validator, payload))

        if send_tasks:
            results = await asyncio.gather(*send_tasks, return_exceptions=True)
            success_count = sum(
                1 for result in results if isinstance(result, bool) and result
            )
            logger.info(
                f"{self.uid_prefix} Broadcast scores for slot {slot}: {success_count}/{len(send_tasks)} successful"
            )

    async def _send_scores_to_validator(
        self, validator: ValidatorInfo, payload: Dict
    ) -> bool:
        """
        Send scores to a specific validator.

        Args:
            validator: Validator to send scores to
            payload: Score payload

        Returns:
            True if successful, False otherwise
        """
        if not validator.api_endpoint:
            logger.warning(
                f"{self.uid_prefix} No API endpoint for validator {validator.uid}"
            )
            return False

        try:
            url = f"{validator.api_endpoint.rstrip('/')}/consensus/scores"

            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                response = await client.post(
                    url, json=payload, headers={"Content-Type": "application/json"}
                )

                if response.status_code == 200:
                    logger.debug(
                        f"{self.uid_prefix} Scores sent successfully to {validator.uid}"
                    )
                    return True
                else:
                    logger.warning(
                        f"{self.uid_prefix} Failed to send scores to {validator.uid}: HTTP {response.status_code}"
                    )
                    return False

        except Exception as e:
            logger.error(
                f"{self.uid_prefix} Error sending scores to {validator.uid}: {e}"
            )
            return False

    async def _get_active_validators(self) -> List[ValidatorInfo]:
        """Get list of active validators for score broadcasting."""
        active_validators = []

        # Debug: Log validator info structure
        logger.debug(
            f"{self.uid_prefix} Debug - validators_info keys: {list(self.core.validators_info.keys())}"
        )
        logger.debug(
            f"{self.uid_prefix} Debug - total validators_info count: {len(self.core.validators_info)}"
        )

        for validator_uid, validator_info in self.core.validators_info.items():
            logger.debug(
                f"{self.uid_prefix} Debug - Checking validator {validator_uid}"
            )
            logger.debug(
                f"{self.uid_prefix} Debug - validator_info type: {type(validator_info)}"
            )
            logger.debug(
                f"{self.uid_prefix} Debug - validator_info attributes: {dir(validator_info)}"
            )

            # More flexible status check - accept multiple status values
            status_ok = True
            if hasattr(validator_info, "status"):
                status = validator_info.status
                logger.debug(
                    f"{self.uid_prefix} Debug - validator {validator_uid} status: {status} (type: {type(status)})"
                )

                # Handle different status formats:
                # - Integer: 0 = inactive, 1 = active
                # - String: "active", "online", "registered"
                # - Boolean: True = active, False = inactive
                if isinstance(status, int):
                    status_ok = status >= 1  # 1 or higher means active
                elif isinstance(status, str):
                    status_ok = status.lower() in [
                        "active",
                        "online",
                        "registered",
                        "true",
                        "1",
                    ]
                elif isinstance(status, bool):
                    status_ok = status
                else:
                    # Unknown status type, assume active
                    logger.debug(
                        f"{self.uid_prefix} Debug - Unknown status type {type(status)} for validator {validator_uid}, assuming active"
                    )
                    status_ok = True
            else:
                logger.debug(
                    f"{self.uid_prefix} Debug - validator {validator_uid} has no status attribute, assuming active"
                )
                # If no status attribute, assume it's active if it exists
                status_ok = True

            # Check endpoint
            endpoint_ok = False
            endpoint = None
            if hasattr(validator_info, "api_endpoint") and validator_info.api_endpoint:
                endpoint = validator_info.api_endpoint
                endpoint_ok = True
            elif hasattr(validator_info, "endpoint") and validator_info.endpoint:
                endpoint = validator_info.endpoint
                endpoint_ok = True

            logger.debug(
                f"{self.uid_prefix} Debug - validator {validator_uid} endpoint: {endpoint} (ok: {endpoint_ok})"
            )

            # Include validator if either status is good OR it has an endpoint
            # This is more permissive to handle different validator states
            if (status_ok and endpoint_ok) or endpoint_ok:
                active_validators.append(validator_info)
                logger.debug(
                    f"{self.uid_prefix} Debug - Added validator {validator_uid} to active list"
                )
            else:
                logger.debug(
                    f"{self.uid_prefix} Debug - Skipped validator {validator_uid} (status_ok: {status_ok}, endpoint_ok: {endpoint_ok})"
                )

        logger.info(
            f"{self.uid_prefix} Found {len(active_validators)} active validators out of {len(self.core.validators_info)} total"
        )

        # Special logging for broadcast context
        other_validators = [
            v
            for v in active_validators
            if getattr(v, "uid", None) != self.core.info.uid
        ]
        logger.info(
            f"{self.uid_prefix} Found {len(other_validators)} other validators for P2P communication"
        )

        if len(other_validators) == 0:
            logger.warning(
                f"{self.uid_prefix} ⚠️ NO OTHER VALIDATORS FOUND FOR P2P COMMUNICATION!"
                f"\n  - Total validators in system: {len(self.core.validators_info)}"
                f"\n  - Active validators: {len(active_validators)}"
                f"\n  - Self UID: {self.core.info.uid}"
                f"\n  - This means P2P consensus cannot work with only 1 validator"
            )

        # If no validators found, try fallback method
        if not active_validators:
            logger.warning(
                f"{self.uid_prefix} No active validators found, trying fallback detection..."
            )
            active_validators = await self._fallback_get_validators()

        return active_validators

    async def _fallback_get_validators(self) -> List[ValidatorInfo]:
        """
        Fallback method to get validators when normal detection fails.
        This tries to get validators from various sources.
        """
        try:
            fallback_validators = []

            # Method 1: Try to get from all validators_info regardless of status
            for validator_uid, validator_info in self.core.validators_info.items():
                if validator_uid != self.core.info.uid:  # Don't include self
                    fallback_validators.append(validator_info)
                    logger.debug(
                        f"{self.uid_prefix} Fallback: Added validator {validator_uid}"
                    )

            # Method 2: If still empty, try to construct from metagraph data
            if not fallback_validators and hasattr(self.core, "metagraph_data"):
                logger.debug(f"{self.uid_prefix} Fallback: Trying metagraph_data...")
                # This would depend on the metagraph structure
                # Add logic here if needed

            # Method 3: Try blockchain validators
            if not fallback_validators and hasattr(self.core, "blockchain_validators"):
                logger.debug(
                    f"{self.uid_prefix} Fallback: Trying blockchain_validators..."
                )
                # Add logic here if needed

            logger.info(
                f"{self.uid_prefix} Fallback found {len(fallback_validators)} validators"
            )
            return fallback_validators

        except Exception as e:
            logger.error(
                f"{self.uid_prefix} Error in fallback validator detection: {e}"
            )
            return []

    # === Received Scores Handling ===

    async def add_received_score(
        self, submitter_uid: str, cycle: int, scores: List[ValidatorScore]
    ):
        """
        Add received scores from other validators.

        Args:
            submitter_uid: UID of the validator who submitted the scores
            cycle: Cycle number
            scores: List of validator scores
        """
        try:
            async with self.core.received_scores_lock:
                if cycle not in self.core.received_validator_scores:
                    self.core.received_validator_scores[cycle] = {}

                self.core.received_validator_scores[cycle][submitter_uid] = {
                    score.task_id: score for score in scores
                }

                logger.debug(
                    f"{self.uid_prefix} Added {len(scores)} scores from validator {submitter_uid} for cycle {cycle}"
                )

        except Exception as e:
            logger.error(f"{self.uid_prefix} Error adding received scores: {e}")

    async def wait_for_consensus_scores(self, wait_timeout_seconds: float) -> bool:
        """
        Wait for consensus scores from other validators.

        Args:
            wait_timeout_seconds: Maximum time to wait

        Returns:
            True if sufficient scores received, False otherwise
        """
        logger.info(
            f"{self.uid_prefix} Waiting for consensus scores (timeout: {wait_timeout_seconds}s)"
        )

        start_time = time.time()

        while time.time() - start_time < wait_timeout_seconds:
            async with self.core.received_scores_lock:
                current_cycle = self.core.current_cycle

                if current_cycle in self.core.received_validator_scores:
                    received_count = len(
                        self.core.received_validator_scores[current_cycle]
                    )

                    if received_count >= MIN_VALIDATORS_FOR_CONSENSUS:
                        logger.info(
                            f"{self.uid_prefix} Sufficient consensus scores received: {received_count}"
                        )
                        return True

            await asyncio.sleep(1)

        logger.warning(f"{self.uid_prefix} Timeout waiting for consensus scores")
        return False

    # === Blockchain Submission Methods ===

    async def submit_consensus_to_blockchain(self, final_scores: Dict[str, float]):
        """Submit consensus results to Core blockchain"""
        logger.info(
            f"🔗 {self.uid_prefix} Submitting {len(final_scores)} consensus scores to Core blockchain..."
        )

        # 🔍 DEBUG: Add detailed logging
        logger.info(f"🔍 {self.uid_prefix} DEBUG: final_scores = {final_scores}")
        logger.info(
            f"🔍 {self.uid_prefix} DEBUG: miners_info count = {len(self.core.miners_info) if self.core.miners_info else 0}"
        )
        logger.info(
            f"🔍 {self.uid_prefix} DEBUG: contract_address = {self.core.contract_address}"
        )
        logger.info(
            f"🔍 {self.uid_prefix} DEBUG: core_client type = {type(self.core_client).__name__}"
        )
        logger.info(
            f"🔍 {self.uid_prefix} DEBUG: available miners_info UIDs = {list(self.core.miners_info.keys()) if self.core.miners_info else []}"
        )

        if not self.core_client:
            logger.warning(
                f"⚠️ {self.uid_prefix} Core client not initialized, skipping blockchain submission"
            )
            return

        try:
            # Submit each miner's final score to blockchain
            transaction_hashes = []

            for miner_uid, consensus_score in final_scores.items():
                try:
                    # Find miner address from uid
                    miner_address = None
                    for uid, miner_info in self.core.miners_info.items():
                        if (
                            miner_info.uid == miner_uid
                        ):  # Compare MinerInfo.uid with consensus miner_uid
                            miner_address = (
                                miner_info.address
                            )  # Get actual address from MinerInfo object
                            logger.info(
                                f"🔍 {self.uid_prefix} Found miner address mapping: {miner_uid} → {miner_address}"
                            )
                            break

                    # FALLBACK: Use known UID-to-address mapping for testing
                    if not miner_address:
                        # Convert hex UID to string if possible
                        test_uid = None
                        try:
                            if miner_uid.startswith("7375626e6574315f6d696e65725f"):
                                # Hex encoded "subnet1_miner_X" - decode it
                                hex_bytes = bytes.fromhex(miner_uid)
                                test_uid = hex_bytes.decode("utf-8")
                                logger.info(
                                    f"🔍 {self.uid_prefix} Decoded miner UID: {test_uid}"
                                )
                        except:
                            pass

                        # Map known test UIDs to addresses (UPDATED WITH CURRENT ENTITY ADDRESSES)
                        uid_to_address_map = {
                            # Current entity addresses from subnet1_aptos/entities/
                            "subnet1_miner_001": "0xd89fBAbb72190ed22F012ADFC693ad974bAD3005",
                            "subnet1_miner_002": "0x16102CA8BEF74fb6214AF352989b664BF0e50498",
                            # Legacy formats for backward compatibility
                            "subnet1_miner_1": "0xd89fBAbb72190ed22F012ADFC693ad974bAD3005",
                            "subnet1_miner_2": "0x16102CA8BEF74fb6214AF352989b664BF0e50498",
                            # Hex encoded formats
                            "ff85b418a988cd2f00725ae1307eef7d272a79c6bfd8c516b8cd82859ff406a7": "0x16102CA8BEF74fb6214AF352989b664BF0e50498",
                            "7375626e6574315f6d696e65725f31": "0xd89fBAbb72190ed22F012ADFC693ad974bAD3005",  # Hex encoded subnet1_miner_1
                            "7375626e6574315f6d696e65725f303031": "0xd89fBAbb72190ed22F012ADFC693ad974bAD3005",  # Hex encoded subnet1_miner_001
                            "7375626e6574315f6d696e65725f303032": "0x16102CA8BEF74fb6214AF352989b664BF0e50498",  # Hex encoded subnet1_miner_002
                        }

                        # Try direct UID lookup
                        miner_address = uid_to_address_map.get(miner_uid)

                        # Try decoded UID lookup
                        if not miner_address and test_uid:
                            miner_address = uid_to_address_map.get(test_uid)

                        if miner_address:
                            logger.info(
                                f"✅ {self.uid_prefix} Using fallback address {miner_address} for miner {miner_uid}"
                            )

                    if not miner_address:
                        logger.warning(
                            f"⚠️ {self.uid_prefix} Miner {miner_uid} address not found (no fallback), skipping..."
                        )
                        continue

                    # Ensure address has 0x prefix and is valid
                    if not miner_address.startswith("0x"):
                        miner_address = "0x" + miner_address

                    # Validate address format
                    if not Web3.is_address(miner_address):
                        logger.warning(
                            f"⚠️ {self.uid_prefix} Invalid address format for {miner_uid}: {miner_address}"
                        )
                        continue

                    # Scale score (0.0-1.0 -> 0-1000000 for 6 decimal precision)
                    # Contract expects uint64 with DIVISOR_64 = 1_000_000
                    trust_score_scaled = int(consensus_score * 1_000_000)
                    performance_scaled = int(consensus_score * 1_000_000)

                    # Ensure scores are within valid range (0 to 1_000_000 for 100%)
                    trust_score_scaled = max(0, min(1_000_000, trust_score_scaled))
                    performance_scaled = max(0, min(1_000_000, performance_scaled))

                    # Submit score update to Core blockchain
                    tx_hash = self.core_client.update_miner_scores(
                        miner_address,  # Positional parameter (not keyword)
                        new_performance=performance_scaled,
                        new_trust_score=trust_score_scaled,
                    )

                    # Track submission (including duplicate and simulation failed transactions)
                    transaction_hashes.append(tx_hash)

                    # Check transaction type and handle accordingly
                    if tx_hash.startswith("duplicate_"):
                        logger.info(
                            f"♻️ {self.uid_prefix} Duplicate transaction for {miner_uid}: {consensus_score:.4f} → TX Hash: {tx_hash} (already in mempool)"
                        )
                    elif tx_hash.startswith("miner_not_registered_"):
                        logger.warning(
                            f"🚫 {self.uid_prefix} Miner not registered for {miner_uid}: {consensus_score:.4f} → TX Hash: {tx_hash} (miner not in contract)"
                        )
                    elif tx_hash.startswith("validator_not_registered_"):
                        logger.warning(
                            f"🚫 {self.uid_prefix} Validator not registered: {consensus_score:.4f} → TX Hash: {tx_hash} (validator lacks permissions)"
                        )
                    elif tx_hash.startswith("simulation_failed_"):
                        logger.warning(
                            f"🚫 {self.uid_prefix} Simulation failed for {miner_uid}: {consensus_score:.4f} → TX Hash: {tx_hash} (would have failed on-chain)"
                        )
                        # Extract and log the simulation error reason
                        parts = tx_hash.split("_", 4)
                        if len(parts) > 4:
                            error_reason = parts[4]
                            logger.warning(
                                f"🔍 {self.uid_prefix} Simulation error reason: {error_reason}"
                            )
                    else:
                        logger.info(
                            f"✅ {self.uid_prefix} Submitted score for {miner_uid}: {consensus_score:.4f} → TX Hash: {tx_hash}"
                        )

                        # Only wait for confirmation on real transactions (not duplicates or simulation failures)
                        try:
                            receipt = self.core_client.wait_for_transaction(
                                tx_hash, timeout=15
                            )  # Short timeout
                            logger.info(
                                f"🎉 {self.uid_prefix} Transaction confirmed for {miner_uid} → TX Hash: {tx_hash}"
                            )
                        except Exception as wait_error:
                            if "timeout" in str(wait_error).lower():
                                logger.warning(
                                    f"⏰ {self.uid_prefix} Transaction confirmation timeout for {miner_uid} → TX Hash: {tx_hash} - continuing anyway"
                                )
                            else:
                                logger.error(
                                    f"❌ {self.uid_prefix} Transaction failed for {miner_uid} → TX Hash: {tx_hash}: {wait_error}"
                                )

                except Exception as e:
                    logger.error(
                        f"❌ {self.uid_prefix} Failed to submit score for {miner_uid}: {e}"
                    )
                    continue

            # Submit ModernTensor incentives if available
            await self._submit_modern_consensus_incentives_to_blockchain()

            logger.info(
                f"🎯 {self.uid_prefix} Core blockchain submission complete: {len(transaction_hashes)}/{len(final_scores)} transactions submitted"
            )
            logger.info(
                f"📋 {self.uid_prefix} Transaction hashes: {transaction_hashes}"
            )

        except Exception as e:
            logger.error(f"❌ {self.uid_prefix} Core blockchain submission error: {e}")
            import traceback

            logger.error(f"{self.uid_prefix} Traceback: {traceback.format_exc()}")

    async def _submit_modern_consensus_incentives_to_blockchain(self):
        """Submit ModernTensor incentives to Core blockchain for reward distribution."""
        if not self.modern_consensus_enabled or not hasattr(
            self, "modern_consensus_incentives"
        ):
            return

        try:
            # Process stored incentives
            current_time = time.time()
            processed_slots = []

            for slot, incentive_data in self.modern_consensus_incentives.items():
                # Skip if too old (older than 1 hour)
                if current_time - incentive_data["timestamp"] > 3600:
                    processed_slots.append(slot)
                    continue

                incentives = incentive_data["incentives"]
                total_rewards = incentive_data["total_rewards"]

                if not incentives:
                    processed_slots.append(slot)
                    continue

                logger.info(
                    f"💰 {self.uid_prefix} Submitting ModernTensor incentives for slot {slot}: {total_rewards:.6f} total CORE"
                )

                # Submit individual incentives to blockchain
                successful_submissions = 0

                for miner_uid, reward_amount in incentives.items():
                    if reward_amount <= 0:
                        continue

                    try:
                        # Find miner address (reuse logic from submit_consensus_to_blockchain)
                        miner_address = self._get_miner_address_from_uid(miner_uid)

                        if not miner_address:
                            logger.warning(
                                f"⚠️ {self.uid_prefix} Cannot find address for miner {miner_uid}, skipping incentive"
                            )
                            continue

                        # Scale reward amount for contract (assuming CORE tokens with 18 decimals)
                        reward_scaled = int(reward_amount * 10**18)

                        # Submit reward transaction (this would need a new contract method)
                        if hasattr(self.core_client, "distribute_modern_tensor_reward"):
                            tx_hash = self.core_client.distribute_modern_tensor_reward(
                                miner_address, reward_scaled
                            )

                            if not tx_hash.startswith(
                                (
                                    "duplicate_",
                                    "simulation_failed_",
                                    "miner_not_registered_",
                                )
                            ):
                                successful_submissions += 1
                                logger.debug(
                                    f"✅ {self.uid_prefix} Submitted ModernTensor reward for {miner_uid}: {reward_amount:.6f} CORE"
                                )
                        else:
                            # Alternative: Add to accumulated rewards in miner scores update
                            logger.debug(
                                f"📊 {self.uid_prefix} ModernTensor reward tracked for {miner_uid}: {reward_amount:.6f} CORE"
                            )
                            successful_submissions += 1

                    except Exception as e:
                        logger.error(
                            f"❌ {self.uid_prefix} Error submitting incentive for {miner_uid}: {e}"
                        )

                logger.info(
                    f"💎 {self.uid_prefix} Submitted {successful_submissions}/{len(incentives)} ModernTensor incentives for slot {slot}"
                )
                processed_slots.append(slot)

            # Clean up processed incentives
            for slot in processed_slots:
                del self.modern_consensus_incentives[slot]

        except Exception as e:
            logger.error(
                f"❌ {self.uid_prefix} Error submitting ModernTensor incentives: {e}"
            )

    def _get_miner_address_from_uid(self, miner_uid: str) -> str:
        """Get miner address from UID (reused logic from submit_consensus_to_blockchain)."""
        try:
            # Try to find in miners_info first
            for uid, miner_info in self.core.miners_info.items():
                if uid == miner_uid:
                    return miner_info.address

            # Fallback to known UID mapping
            uid_to_address_map = {
                "subnet1_miner_001": "0xd89fBAbb72190ed22F012ADFC693ad974bAD3005",
                "subnet1_miner_002": "0x16102CA8BEF74fb6214AF352989b664BF0e50498",
                "subnet1_miner_1": "0xd89fBAbb72190ed22F012ADFC693ad974bAD3005",
                "subnet1_miner_2": "0x16102CA8BEF74fb6214AF352989b664BF0e50498",
                "7375626e6574315f6d696e65725f303031": "0xd89fBAbb72190ed22F012ADFC693ad974bAD3005",
                "7375626e6574315f6d696e65725f303032": "0x16102CA8BEF74fb6214AF352989b664BF0e50498",
            }

            return uid_to_address_map.get(miner_uid)

        except Exception as e:
            logger.error(
                f"❌ {self.uid_prefix} Error getting miner address for {miner_uid}: {e}"
            )
            return None

    async def get_modern_consensus_network_metrics(self) -> Optional[NetworkMetrics]:
        """Get comprehensive network metrics using ModernTensor engine."""
        if not self.modern_consensus_enabled or not self.modern_consensus_engine:
            return None

        try:
            metrics = await self.modern_consensus_engine.get_network_metrics()

            logger.info(f"📊 {self.uid_prefix} ModernTensor Network Metrics:")
            logger.info(f"  • Total Miners: {metrics.total_miners}")
            logger.info(f"  • Total Validators: {metrics.total_validators}")
            logger.info(f"  • Active Miners: {metrics.active_miners}")
            logger.info(f"  • Active Validators: {metrics.active_validators}")
            logger.info(f"  • Average Performance: {metrics.average_performance:.4f}")
            logger.info(f"  • Total CORE Stake: {metrics.total_stake}")
            logger.info(f"  • Total Bitcoin Stake: {metrics.bitcoin_stake}")
            logger.info(f"  • Consensus Rounds: {metrics.consensus_rounds}")

            return metrics

        except Exception as e:
            logger.error(
                f"❌ {self.uid_prefix} Error getting ModernTensor network metrics: {e}"
            )
            return None

    def is_modern_consensus_enabled(self) -> bool:
        """Check if ModernTensor consensus is enabled and functional."""
        return (
            self.modern_consensus_enabled
            and self.modern_consensus_engine is not None
            and self.core_client is not None
        )

    def get_consensus_status_summary(self) -> Dict[str, Any]:
        """Get comprehensive consensus status summary."""
        return {
            "validator_uid": (
                self.core.info.uid if hasattr(self.core, "info") else "unknown"
            ),
            "modern_consensus_enabled": self.is_modern_consensus_enabled(),
            "core_client_status": self.core_client is not None,
            "flexible_mode": self.flexible_mode_enabled,
            "participation_rate": self.consensus_participation_rate,
            "last_successful_consensus": self.last_successful_consensus,
            "flexible_metrics": (
                self.flexible_metrics.copy()
                if hasattr(self, "flexible_metrics")
                else {}
            ),
            "stored_incentives_count": (
                len(self.modern_consensus_incentives)
                if hasattr(self, "modern_consensus_incentives")
                else 0
            ),
            "consensus_engine": (
                "ModernTensor-Enhanced"
                if self.is_modern_consensus_enabled()
                else "Legacy"
            ),
        }

    # === Consensus Finalization ===

    async def finalize_consensus(self, slot: int) -> Dict[str, float]:
        """
        Finalize consensus for a slot by aggregating all validator scores.

        Args:
            slot: Slot number

        Returns:
            Dictionary of final consensus scores
        """
        logger.info(f"{self.uid_prefix} Finalizing consensus for slot {slot}")

        try:
            # Collect local scores
            local_scores = await self._collect_local_scores_for_consensus(slot)

            # Aggregate with P2P received scores
            await self._aggregate_all_scores_for_slot(slot, local_scores)

            # Try synchronized consensus first
            success = await self._coordinate_synchronized_metagraph_update(
                slot, local_scores
            )

            if success:
                # Return the local scores as final if consensus was successful
                return local_scores
            else:
                # Fallback to individual update
                logger.warning(
                    f"{self.uid_prefix} Falling back to individual metagraph update for slot {slot}"
                )
                await self._apply_consensus_scores_to_metagraph(slot, local_scores)
                return local_scores

        except Exception as e:
            logger.error(
                f"{self.uid_prefix} Error finalizing consensus for slot {slot}: {e}"
            )
            return {}

    async def _aggregate_all_scores_for_slot(
        self, slot: int, local_scores: Dict[str, float]
    ):
        """
        Aggregate local scores with P2P received scores into slot_aggregated_scores.

        Args:
            slot: Current slot number
            local_scores: Local validator scores
        """
        try:
            logger.info(f"{self.uid_prefix} Aggregating all scores for slot {slot}")

            # Initialize slot aggregated scores
            if slot not in self.core.slot_aggregated_scores:
                self.core.slot_aggregated_scores[slot] = {}

            # Add local scores
            for miner_uid, score in local_scores.items():
                if miner_uid not in self.core.slot_aggregated_scores[slot]:
                    self.core.slot_aggregated_scores[slot][miner_uid] = {}

                # Add this validator's local score
                self.core.slot_aggregated_scores[slot][miner_uid][
                    self.core.info.uid
                ] = score

            # Add P2P received scores - check both current cycle and slot-based storage
            p2p_scores_added = 0

            # Method 1: Check current cycle based scores
            current_cycle = self.core.current_cycle
            if current_cycle in self.core.received_validator_scores:
                p2p_scores = self.core.received_validator_scores[current_cycle]

                for validator_uid, validator_scores in p2p_scores.items():
                    for task_id, score_obj in validator_scores.items():
                        miner_uid = score_obj.miner_uid
                        score_value = score_obj.score

                        # Initialize miner entry if needed
                        if miner_uid not in self.core.slot_aggregated_scores[slot]:
                            self.core.slot_aggregated_scores[slot][miner_uid] = {}

                        # Add P2P score from this validator
                        self.core.slot_aggregated_scores[slot][miner_uid][
                            validator_uid
                        ] = score_value
                        p2p_scores_added += 1

                        logger.debug(
                            f"{self.uid_prefix} Added P2P score: Miner {miner_uid[:8]}... "
                            f"from Validator {validator_uid[:8]}...: {score_value:.4f}"
                        )

            # Method 2: Check if there's slot-based P2P storage (fallback)
            if (
                hasattr(self.core, "slot_received_scores")
                and slot in self.core.slot_received_scores
            ):
                slot_p2p_scores = self.core.slot_received_scores[slot]

                for validator_uid, validator_scores in slot_p2p_scores.items():
                    for task_id, score_obj in validator_scores.items():
                        miner_uid = score_obj.miner_uid
                        score_value = score_obj.score

                        # Initialize miner entry if needed
                        if miner_uid not in self.core.slot_aggregated_scores[slot]:
                            self.core.slot_aggregated_scores[slot][miner_uid] = {}

                        # Add P2P score from this validator (avoid duplicates)
                        if (
                            validator_uid
                            not in self.core.slot_aggregated_scores[slot][miner_uid]
                        ):
                            self.core.slot_aggregated_scores[slot][miner_uid][
                                validator_uid
                            ] = score_value
                            p2p_scores_added += 1

                            logger.debug(
                                f"{self.uid_prefix} Added slot-based P2P score: Miner {miner_uid[:8]}... "
                                f"from Validator {validator_uid[:8]}...: {score_value:.4f}"
                            )

            # Log P2P aggregation status
            if p2p_scores_added > 0:
                logger.info(
                    f"{self.uid_prefix} Successfully added {p2p_scores_added} P2P scores for slot {slot}"
                )
            else:
                logger.warning(
                    f"{self.uid_prefix} No P2P scores found to aggregate for slot {slot}"
                )

                # Debug: Log what's available
                logger.debug(
                    f"{self.uid_prefix} Debug - current_cycle: {current_cycle}"
                )
                logger.debug(
                    f"{self.uid_prefix} Debug - received_validator_scores keys: {list(self.core.received_validator_scores.keys())}"
                )
                if hasattr(self.core, "slot_received_scores"):
                    logger.debug(
                        f"{self.uid_prefix} Debug - slot_received_scores keys: {list(getattr(self.core, 'slot_received_scores', {}).keys())}"
                    )

            # Log aggregation summary
            # Note: slot_aggregated_scores[slot] is Dict[miner_uid, float] after P2P consensus
            total_miners = len(self.core.slot_aggregated_scores[slot])
            total_scores = len(
                self.core.slot_aggregated_scores[slot]
            )  # Each miner has 1 final score

            logger.info(
                f"{self.uid_prefix} Aggregated scores for slot {slot}: "
                f"{total_miners} miners, {total_scores} total scores"
            )

        except Exception as e:
            logger.error(
                f"{self.uid_prefix} Error aggregating scores for slot {slot}: {e}"
            )

    async def _emergency_aggregate_scores(self, slot: int):
        """
        Emergency aggregation when slot_aggregated_scores is empty.
        This is a fallback mechanism to ensure we always have some scores.
        """
        try:
            logger.warning(f"{self.uid_prefix} Emergency aggregation for slot {slot}")

            # Try to get any available scores
            local_scores = await self._collect_local_scores_for_consensus(slot)

            if local_scores:
                # Use local scores as fallback
                await self._aggregate_all_scores_for_slot(slot, local_scores)
                logger.info(
                    f"{self.uid_prefix} Emergency aggregation completed with {len(local_scores)} local scores"
                )
            else:
                # Last resort: Check if we have any cycle scores or validator scores
                fallback_scores = {}

                # Try cycle_scores
                for task_id, scores_list in self.core.cycle_scores.items():
                    if scores_list:
                        latest_score = scores_list[-1]
                        fallback_scores[latest_score.miner_uid] = latest_score.score

                # Try validator_scores if cycle_scores is empty
                if not fallback_scores and hasattr(self.core, "validator_scores"):
                    for task_id, scores_list in self.core.validator_scores.items():
                        if scores_list:
                            latest_score = scores_list[-1]
                            fallback_scores[latest_score.miner_uid] = latest_score.score

                if fallback_scores:
                    await self._aggregate_all_scores_for_slot(slot, fallback_scores)
                    logger.warning(
                        f"{self.uid_prefix} Emergency aggregation used fallback scores: {len(fallback_scores)} scores"
                    )
                else:
                    logger.error(
                        f"{self.uid_prefix} Emergency aggregation failed: no scores available for slot {slot}"
                    )

        except Exception as e:
            logger.error(f"{self.uid_prefix} Error in emergency aggregation: {e}")

    # === Blockchain Submission ===

    async def submit_to_blockchain(self, slot: int):
        """
        Submit consensus results to the Core blockchain.
        This method is called by the main validator loop.
        """
        try:
            logger.info(
                f"{self.uid_prefix} Submitting consensus results for slot {slot} to blockchain..."
            )

            # Get aggregated scores for this slot from core
            if (
                hasattr(self.core, "slot_aggregated_scores")
                and slot in self.core.slot_aggregated_scores
            ):
                slot_scores = self.core.slot_aggregated_scores[slot]

                # slot_aggregated_scores[slot] is already a flat Dict[miner_uid, final_score]
                # No need to average - scores are already processed by P2P consensus
                final_scores = {}
                for miner_uid, final_score in slot_scores.items():
                    if isinstance(final_score, (int, float)):
                        # Final score is already averaged from P2P consensus
                        final_scores[miner_uid] = final_score
                    elif isinstance(final_score, dict):
                        # Legacy format: Dict[validator_uid, score] - average them
                        if final_score:
                            avg_score = sum(final_score.values()) / len(final_score)
                            final_scores[miner_uid] = avg_score
                    else:
                        logger.warning(
                            f"🚨 {self.uid_prefix} Unexpected score format for miner {miner_uid}: {type(final_score)}"
                        )

                if final_scores:
                    logger.info(
                        f"{self.uid_prefix} Submitting {len(final_scores)} consensus scores to blockchain for slot {slot}"
                    )

                    # Use existing blockchain submission logic
                    await self.submit_consensus_to_blockchain(final_scores)

                    logger.info(
                        f"{self.uid_prefix} Consensus results for slot {slot} submitted to blockchain successfully"
                    )
                else:
                    logger.warning(
                        f"{self.uid_prefix} No consensus scores to submit for slot {slot}"
                    )
            else:
                logger.warning(
                    f"{self.uid_prefix} No aggregated scores found for slot {slot}"
                )

        except Exception as e:
            logger.error(
                f"{self.uid_prefix} Error submitting consensus results for slot {slot}: {e}"
            )

    # === Utility Methods ===

    def get_consensus_statistics(self) -> Dict[str, Any]:
        """Get statistics about consensus state."""
        stats = {
            "cycle_scores_count": sum(
                len(scores) for scores in self.core.cycle_scores.values()
            ),
            "slot_scores_count": sum(
                len(scores) for scores in self.core.slot_scores.values()
            ),
            "received_scores_cycles": len(self.core.received_validator_scores),
            "consensus_cache_size": len(self.core.consensus_results_cache),
        }

        # Add flexible consensus statistics if enabled
        if self.flexible_mode_enabled:
            stats.update(
                {
                    "flexible_mode": True,
                    "consensus_participation_rate": self.consensus_participation_rate,
                    "last_successful_consensus": self.last_successful_consensus,
                    "flexible_metrics": self.flexible_metrics.copy(),
                }
            )

        return stats

    # === FLEXIBLE CONSENSUS METHODS ===

    def enable_flexible_mode(
        self, auto_detect_epoch: bool = True, adaptive_timing: bool = True
    ):
        """
        Enable flexible consensus mode for this validator.

        Args:
            auto_detect_epoch: Whether to auto-detect ongoing slots
            adaptive_timing: Whether to enable adaptive timing
        """
        if not hasattr(self.core, "slot_coordinator"):
            logger.error(
                f"{self.uid_prefix} Cannot enable flexible mode - no slot coordinator"
            )
            self.flexible_mode_enabled = False
            return

        # The coordinator itself doesn't need to be enabled.
        # This flag enables the *consensus handler* to use flexible logic.
        self.flexible_mode_enabled = True
        logger.info(
            f"✅ {self.uid_prefix} ValidatorNodeConsensus flexible mode enabled."
        )

    async def run_flexible_consensus_cycle(self, slot: Optional[int] = None):
        """
        Run a complete flexible consensus cycle.

        This method provides the main entry point for flexible consensus operation,
        allowing validators to join at any time while ensuring critical events
        are synchronized.

        Args:
            slot: Optional slot number (auto-detected if None)
        """
        logger.info(f"🔧 RUN_FLEXIBLE_CONSENSUS_CYCLE called for {self.uid_prefix}")
        logger.info(f"🔧 Flexible mode enabled: {self.flexible_mode_enabled}")

        # Flexible mode with synchronized cutoffs - allow running
        logger.info(
            f"{self.uid_prefix} Running flexible mode with synchronized cutoffs"
        )

        if not self.flexible_mode_enabled:
            logger.warning(
                f"{self.uid_prefix} Flexible mode not enabled - falling back to standard consensus"
            )
            return await self.run_consensus_cycle()

        try:
            # Detect current state if slot not provided
            if slot is None:
                slot = self.core.slot_coordinator.get_current_blockchain_slot()
                current_phase, _, _ = self.core.slot_coordinator.get_slot_phase(slot)

                logger.info(
                    f"🔄 {self.uid_prefix} Joining flexible consensus at slot {slot}, phase {current_phase.value}"
                )

                # Track mid-slot joins
                if current_phase != SlotPhase.TASK_ASSIGNMENT:
                    self.flexible_metrics["mid_slot_joins"] += 1

            # Track consensus attempt
            self.flexible_metrics["total_consensus_attempts"] += 1

            # Run flexible consensus phases (task execution now integrated into task assignment)
            await self._run_flexible_task_phase(
                slot
            )  # Now includes task execution monitoring
            await self._run_flexible_consensus_phase(slot)
            await self._run_flexible_metagraph_phase(slot)

            # Update success metrics
            self.last_successful_consensus = time.time()
            self._update_participation_rate(True)

            logger.info(
                f"✅ {self.uid_prefix} Flexible consensus cycle completed for slot {slot}"
            )

        except Exception as e:
            logger.error(f"❌ {self.uid_prefix} Error in flexible consensus cycle: {e}")
            self._update_participation_rate(False)
            raise

    async def _run_flexible_task_phase(self, slot: int):
        """Run task assignment phase with flexible assignment and strict cutoff"""

        # STEP 1: FLEXIBLE TASK ASSIGNMENT - start immediately, no waiting
        logger.info(
            f"📋 {self.uid_prefix} Starting FLEXIBLE task assignment for slot {slot} (assign anytime)"
        )

        # Calculate exact task assignment cutoff timing based on slot number
        from mt_core.consensus.slot_coordinator import EPOCH_START

        slot_start_time = EPOCH_START + (
            slot * self.core.slot_config.slot_duration_minutes * 60
        )
        task_assignment_end_time = slot_start_time + (
            self.core.slot_config.task_assignment_minutes * 60
        )

        current_time = int(time.time())
        remaining_time = task_assignment_end_time - current_time

        logger.info(
            f"✅ {self.uid_prefix} Flexible task assignment started for slot {slot} (remaining: {remaining_time:.1f}s)"
        )

        # STEP 2: Register participation
        await self.core.slot_coordinator.register_phase_entry(
            slot, SlotPhase.TASK_ASSIGNMENT, {"flexible_join": True}
        )

        # ENFORCE TASK ASSIGNMENT CUTOFF - ensure all validators finish together
        await self.core.slot_coordinator.enforce_task_assignment_cutoff(slot)
        logger.info(
            f"🛑 {self.uid_prefix} Task assignment cutoff enforced for slot {slot}"
        )

        # Wait for miners to be fully ready
        logger.info(f"⏳ {self.uid_prefix} Waiting 5s for miners to be fully ready...")
        await asyncio.sleep(5)
        logger.info(f"🚀 {self.uid_prefix} Starting task assignment after delay")

        # CONTINUOUS TASK ASSIGNMENT LOOP
        try:
            # Select miners for this slot
            selected_miners = await self._get_available_miners_for_slot(slot)

            if selected_miners:
                logger.info(
                    f"📋 {self.uid_prefix} Starting continuous task assignment to {len(selected_miners)} miners"
                )

                # Initialize slot tracking
                if slot not in self.core.slot_scores:
                    self.core.slot_scores[slot] = []

                task_assignment_end_time = time.time() + remaining_time
                task_round = 1

                # BATCH TASK ASSIGNMENT - Giao nhiều task cùng lúc
                logger.info(
                    f"📋 {self.uid_prefix} Starting BATCH task assignment (giao nhiều task cùng lúc)"
                )

                # MINI-BATCH SEQUENTIAL ASSIGNMENT - Giao 5 miners cùng lúc, chờ hoàn thành rồi giao tiếp
                logger.info(
                    f"📋 {self.uid_prefix} Starting MINI-BATCH SEQUENTIAL assignment (5 miners per batch, sequential processing)"
                )

                # MINI-BATCH ASSIGNMENT: Giao 5 miners cùng lúc, chờ hoàn thành rồi giao tiếp
                while time.time() < task_assignment_end_time:
                    remaining_time = task_assignment_end_time - time.time()
                    if remaining_time <= 10:  # Stop if less than 10s remaining
                        logger.info(
                            f"⏰ {self.uid_prefix} Approaching cutoff time, stopping task assignment"
                        )
                        break

                    logger.info(
                        f"📋 {self.uid_prefix} Mini-batch round {task_round} - {remaining_time:.1f}s until cutoff"
                    )

                    # SELECT RANDOM 5 MINERS for this batch
                    import random

                    batch_miners = random.sample(
                        selected_miners, min(5, len(selected_miners))
                    )
                    logger.info(
                        f"🎲 {self.uid_prefix} Selected {len(batch_miners)} random miners for batch {task_round}"
                    )

                    # MINI-BATCH ASSIGNMENT: Giao task cho 5 miners cùng lúc
                    batch_tasks = []
                    batch_scores = 0

                    # STEP 1: Giao task cho tất cả 5 miners trong batch
                    logger.info(
                        f"📤 {self.uid_prefix} Sending tasks to {len(batch_miners)} miners in batch {task_round}"
                    )

                    for miner in batch_miners:
                        try:
                            remaining_in_round = task_assignment_end_time - time.time()
                            if remaining_in_round <= 5:  # Stop 5s before cutoff
                                logger.info(
                                    f"⏰ {self.uid_prefix} Cutoff approaching, stopping batch assignment"
                                )
                                break

                            # Giao task cho miner này
                            task_sent = await self._send_single_task_to_miner(
                                slot, miner, task_round
                            )
                            if task_sent:
                                batch_tasks.append((miner, task_sent))
                                logger.info(
                                    f"📤 {self.uid_prefix} Task sent to miner {getattr(miner, 'uid', 'unknown')} in batch {task_round}"
                                )

                        except Exception as e:
                            logger.error(
                                f"❌ {self.uid_prefix} Error with miner {getattr(miner, 'uid', 'unknown')}: {e}"
                            )
                            continue

                    # STEP 2: Chờ tất cả 5 miners trong batch hoàn thành
                    if batch_tasks:
                        logger.info(
                            f"⏳ {self.uid_prefix} Waiting for {len(batch_tasks)} miners in batch {task_round} to complete..."
                        )

                        # Chờ kết quả cho tất cả miners trong batch (15-30s)
                        result_timeout = min(30.0, remaining_time * 0.7)
                        logger.info(
                            f"⏳ {self.uid_prefix} Waiting {result_timeout:.1f}s for batch {task_round} results..."
                        )
                        await asyncio.sleep(result_timeout)

                        # STEP 3: Chấm điểm tất cả 5 miners trong batch
                        logger.info(
                            f"📊 {self.uid_prefix} Scoring {len(batch_tasks)} miners in batch {task_round}..."
                        )

                        for miner, task_sent in batch_tasks:
                            try:
                                scored = await self._score_single_task_result(
                                    slot, task_sent
                                )
                                if scored:
                                    batch_scores += 1
                                    logger.info(
                                        f"⚡ {self.uid_prefix} Scored task from miner {getattr(miner, 'uid', 'unknown')} in batch {task_round}"
                                    )
                            except Exception as e:
                                logger.error(
                                    f"❌ {self.uid_prefix} Error scoring task from miner {getattr(miner, 'uid', 'unknown')}: {e}"
                                )

                    task_round += 1
                    logger.info(
                        f"✅ {self.uid_prefix} Mini-batch {task_round-1} completed: {batch_scores} scores from {len(batch_tasks)} miners"
                    )

                    # Pause trước batch tiếp theo (3s)
                    if remaining_time > 15:
                        pause_time = min(3.0, remaining_time * 0.1)
                        logger.info(
                            f"⏸️ {self.uid_prefix} Pause {pause_time:.1f}s before next mini-batch..."
                        )
                        await asyncio.sleep(pause_time)

                logger.info(
                    f"✅ {self.uid_prefix} Mini-batch sequential assignment completed: {task_round-1} rounds"
                )

                # CALCULATE AVERAGE SCORES PER MINER after all assignment rounds
                total_scores = len(self.core.slot_scores.get(slot, []))
                averaged_scores = await self._calculate_average_scores_per_miner(slot)

                logger.info(
                    f"✅ {self.uid_prefix} Task assignment phase complete: {task_round-1} rounds, {total_scores} total scores"
                )
                logger.info(
                    f"📊 {self.uid_prefix} Averaged scores: {len(averaged_scores)} miners with avg scores"
                )

                # === INTEGRATED TASK EXECUTION MONITORING ===
                logger.info(
                    f"⚡ {self.uid_prefix} Starting integrated task execution monitoring..."
                )

                # Continue monitoring any pending tasks for remaining time
                remaining_monitor_time = self.core.slot_coordinator.get_slot_phase(
                    slot
                )[2]
                monitor_end_time = time.time() + min(
                    remaining_monitor_time, 30
                )  # Max 30s monitoring

                # Monitor pending tasks without assigning new ones
                while time.time() < monitor_end_time:
                    remaining_time = monitor_end_time - time.time()
                    if remaining_time <= 2:
                        break

                    # Check for late results and score them
                    try:
                        # Use existing task monitoring if available
                        tasks_module = None
                        if hasattr(self.core, "tasks"):
                            tasks_module = self.core.tasks
                        elif hasattr(self.core, "validator_instance") and hasattr(
                            self.core.validator_instance, "tasks"
                        ):
                            tasks_module = self.core.validator_instance.tasks

                        if tasks_module:
                            # Monitor for new results
                            stats_before = len(self.core.slot_scores.get(slot, []))

                            # Brief monitoring sweep
                            await asyncio.sleep(2)

                            # Check if any new results came in and score them
                            unscored_tasks = []
                            for task_id, assignment in self.core.tasks_sent.items():
                                if (
                                    hasattr(assignment, "task_data")
                                    and assignment.task_data.get("slot") == slot
                                    and not any(
                                        score.task_id == task_id
                                        for score in self.core.slot_scores.get(slot, [])
                                    )
                                ):
                                    unscored_tasks.append(task_id)

                            # Score any unscored tasks that have results
                            for task_id in unscored_tasks:
                                await self._score_single_task_result(slot, task_id)

                            stats_after = len(self.core.slot_scores.get(slot, []))
                            if stats_after > stats_before:
                                logger.info(
                                    f"📥 {self.uid_prefix} Late results scored: +{stats_after - stats_before}"
                                )

                        else:
                            await asyncio.sleep(2)

                    except Exception as e:
                        logger.error(
                            f"❌ {self.uid_prefix} Error during task monitoring: {e}"
                        )
                        await asyncio.sleep(2)

                logger.info(
                    f"✅ {self.uid_prefix} Integrated task execution monitoring complete"
                )

                # Keep tasks_sent for late results - DON'T cleanup until consensus phase ends
                logger.debug(
                    f"🔒 {self.uid_prefix} Keeping {len(self.core.tasks_sent)} tasks_sent for late results through consensus phase"
                )

                # DELAY cleanup until after consensus - miners still sending results
                logger.info(
                    f"⏰ {self.uid_prefix} Delaying task cleanup until after consensus phase to allow late results"
                )
            else:
                logger.warning(
                    f"⚠️ {self.uid_prefix} No miners available for task assignment in slot {slot}"
                )

        except Exception as e:
            logger.error(
                f"❌ {self.uid_prefix} Error in continuous task assignment: {e}"
            )

        # Wait for coordination with flexible timeout
        ready_validators = (
            await self.core.slot_coordinator.wait_for_phase_consensus_flexible(
                slot, SlotPhase.TASK_ASSIGNMENT, timeout=30
            )
        )

        logger.info(
            f"✅ {self.uid_prefix} Task assignment coordination complete: {len(ready_validators)} validators"
        )

    async def _run_flexible_execution_phase(self, slot: int):
        """Run task execution phase - continue collecting results"""
        current_phase, _, remaining = self.core.slot_coordinator.get_slot_phase(slot)

        if current_phase in [SlotPhase.TASK_ASSIGNMENT, SlotPhase.TASK_EXECUTION]:
            logger.info(
                f"⚡ {self.uid_prefix} Monitoring task execution for slot {slot} (remaining: {remaining}s)"
            )

            # Register participation early
            await self.core.slot_coordinator.register_phase_entry(
                slot, SlotPhase.TASK_EXECUTION, {"flexible_join": True}
            )

            # UTILIZE EXISTING TASK MONITORING
            try:
                # Check for tasks module same way as assignment phase
                tasks_module = None
                if hasattr(self.core, "tasks"):
                    tasks_module = self.core.tasks
                elif hasattr(self.core, "validator_instance") and hasattr(
                    self.core.validator_instance, "tasks"
                ):
                    tasks_module = self.core.validator_instance.tasks

                if tasks_module:
                    # Use existing task monitoring from tasks module
                    await tasks_module.monitor_task_execution(slot)

                    # Get current status
                    stats = tasks_module.get_task_statistics()
                    logger.info(f"📥 {self.uid_prefix} Task stats: {stats}")
                else:
                    logger.warning(
                        f"⚠️ {self.uid_prefix} No tasks module for monitoring"
                    )
                    await asyncio.sleep(min(10, remaining))

            except Exception as e:
                logger.error(
                    f"❌ {self.uid_prefix} Error during execution monitoring: {e}"
                )

            # Wait for execution coordination
            ready_validators = (
                await self.core.slot_coordinator.wait_for_phase_consensus_flexible(
                    slot, SlotPhase.TASK_EXECUTION, timeout=30
                )
            )

            logger.info(
                f"✅ {self.uid_prefix} Task execution coordination complete: {len(ready_validators)} validators"
            )
        else:
            logger.info(
                f"⏭️ {self.uid_prefix} Skipping task execution (current phase: {current_phase.value})"
            )

    async def _run_flexible_consensus_phase(self, slot: int):
        """Run consensus scoring phase with averaging and P2P"""
        logger.info(
            f"🎯 {self.uid_prefix} Starting flexible consensus scoring for slot {slot}"
        )

        # STEP 0: SLOT-BASED SYNCHRONIZATION - wait for exact slot timing
        logger.info(
            f"🛑 {self.uid_prefix} Waiting for slot-based synchronization for slot {slot}"
        )

        # Calculate exact timing based on slot number
        from mt_core.consensus.slot_coordinator import EPOCH_START

        slot_start_time = EPOCH_START + (
            slot * self.core.slot_config.slot_duration_minutes * 60
        )
        task_cutoff_time = slot_start_time + (
            self.core.slot_config.task_assignment_minutes * 60
        )
        consensus_start_time = task_cutoff_time
        consensus_end_time = consensus_start_time + (
            self.core.slot_config.consensus_minutes * 60
        )
        metagraph_start_time = consensus_end_time
        metagraph_end_time = (
            metagraph_start_time + self.core.slot_config.metagraph_update_seconds
        )

        current_time = int(time.time())

        # Wait for exact task cutoff time
        if current_time < task_cutoff_time:
            wait_time = task_cutoff_time - current_time
            logger.info(
                f"⏰ {self.uid_prefix} Waiting {wait_time}s for SLOT-BASED task cutoff (slot {slot})"
            )
            await asyncio.sleep(wait_time)

        logger.info(
            f"✅ {self.uid_prefix} Slot-based task cutoff reached for slot {slot}"
        )

        # STEP 1: Use scores already generated by tasks module
        slot_scores = self.core.slot_scores.get(slot, [])

        if slot_scores:
            logger.info(
                f"📊 {self.uid_prefix} Found {len(slot_scores)} scores from tasks module for slot {slot}"
            )
            # Aggregate scores if needed (tasks module might have already done this)
            averaged_scores = await self._use_existing_slot_scores(slot, slot_scores)
        else:
            logger.warning(f"⚠️ {self.uid_prefix} No scores available in slot {slot}")
            averaged_scores = {}

        # STEP 2: Register consensus participation
        await self.core.slot_coordinator.register_phase_entry(
            slot,
            SlotPhase.CONSENSUS_SCORING,
            {
                "flexible_join": True,
                "scores_count": len(self.core.slot_scores.get(slot, [])),
                "miners_scored": len(averaged_scores),
            },
        )

        # STEP 3: Wait for consensus coordination
        ready_validators = (
            await self.core.slot_coordinator.wait_for_phase_consensus_flexible(
                slot, SlotPhase.CONSENSUS_SCORING, timeout=60
            )
        )

        if len(ready_validators) < MAJORITY_THRESHOLD:
            self.flexible_metrics["consensus_below_threshold"] += 1

        # STEP 4: Use existing P2P consensus infrastructure
        # DEBUG: Log why P2P might be skipped
        logger.info(
            f"🔍 {self.uid_prefix} DEBUG P2P check - averaged_scores: {len(averaged_scores) if averaged_scores else 'None/Empty'}"
        )
        if not averaged_scores:
            slot_scores_list = self.core.slot_scores.get(slot, [])
            logger.info(
                f"🔍 {self.uid_prefix} DEBUG - slot_scores raw count: {len(slot_scores_list)}"
            )
            for i, score in enumerate(slot_scores_list[:3]):  # Show first 3 scores
                logger.info(
                    f"🔍 {self.uid_prefix} DEBUG - score[{i}]: miner={score.miner_uid}, score={score.score}"
                )

        if averaged_scores:
            # SLOT-BASED P2P CONSENSUS - wait for exact consensus timing
            logger.info(
                f"🤝 {self.uid_prefix} Waiting for slot-based P2P consensus for slot {slot}"
            )

            # Wait for exact consensus start time
            current_time = int(time.time())
            if current_time < consensus_start_time:
                wait_time = consensus_start_time - current_time
                logger.info(
                    f"⏰ {self.uid_prefix} Waiting {wait_time}s for SLOT-BASED P2P consensus start (slot {slot})"
                )
                await asyncio.sleep(wait_time)

            logger.info(
                f"✅ {self.uid_prefix} Slot-based P2P consensus started for slot {slot}"
            )

            # Use existing coordinate_consensus_round from slot_coordinator
            if hasattr(self.core, "slot_coordinator") and hasattr(
                self.core.slot_coordinator, "coordinate_consensus_round"
            ):
                logger.info(
                    f"🤝 {self.uid_prefix} Using existing coordinate_consensus_round for P2P consensus"
                )
                # Convert ValidatorScore list to Dict[miner_uid, score] format
                slot_scores_list = self.core.slot_scores.get(slot, [])
                local_scores = {}
                for score_obj in slot_scores_list:
                    local_scores[score_obj.miner_uid] = score_obj.score

                logger.debug(
                    f"🔄 {self.uid_prefix} Converted {len(slot_scores_list)} ValidatorScore objects to {len(local_scores)} local_scores dict"
                )

                final_scores = (
                    await self.core.slot_coordinator.coordinate_consensus_round(
                        slot, local_scores
                    )
                )
                logger.info(
                    f"✅ {self.uid_prefix} P2P consensus completed: {len(final_scores)} final scores"
                )

                # CRITICAL: Store P2P consensus results for metagraph update
                if final_scores:
                    if not hasattr(self.core, "slot_aggregated_scores"):
                        self.core.slot_aggregated_scores = {}
                    self.core.slot_aggregated_scores[slot] = final_scores
                    logger.info(
                        f"💾 {self.uid_prefix} Stored {len(final_scores)} aggregated scores for slot {slot} metagraph update"
                    )
            else:
                # Fallback to scoring.py broadcast_scores_logic
                logger.info(
                    f"🤝 {self.uid_prefix} Using fallback broadcast_scores_logic"
                )
                fallback_scores = await self._use_existing_broadcast_logic(
                    slot, ready_validators
                )

                # Store fallback results for metagraph update
                if fallback_scores:
                    if not hasattr(self.core, "slot_aggregated_scores"):
                        self.core.slot_aggregated_scores = {}
                    self.core.slot_aggregated_scores[slot] = fallback_scores
                    logger.info(
                        f"💾 {self.uid_prefix} Stored {len(fallback_scores)} fallback scores for slot {slot} metagraph update"
                    )
        else:
            logger.warning(
                f"⚠️ {self.uid_prefix} Skipping P2P consensus - no scores to exchange"
            )

            # CRITICAL FIX: Even if P2P skipped, store any available scores for metagraph
            # Check if we have any scores at all
            slot_scores_list = self.core.slot_scores.get(slot, [])
            if slot_scores_list:
                logger.info(
                    f"💾 {self.uid_prefix} P2P skipped but found {len(slot_scores_list)} local scores - storing for metagraph"
                )

                # Convert local scores to dict format
                local_only_scores = {}
                for score_obj in slot_scores_list:
                    local_only_scores[score_obj.miner_uid] = score_obj.score

                # Store local scores as fallback
                if local_only_scores:
                    if not hasattr(self.core, "slot_aggregated_scores"):
                        self.core.slot_aggregated_scores = {}
                    self.core.slot_aggregated_scores[slot] = local_only_scores
                    logger.info(
                        f"💾 {self.uid_prefix} Stored {len(local_only_scores)} local-only scores for slot {slot} metagraph update"
                    )
            else:
                logger.warning(
                    f"🚨 {self.uid_prefix} No scores available at all for slot {slot}"
                )

        # MOVED CLEANUP TO END OF CONSENSUS PHASE - safer for late results
        logger.info(
            f"🧹 {self.uid_prefix} Now safe to cleanup old tasks after consensus phase..."
        )
        await self._cleanup_old_tasks_sent()

        logger.info(
            f"✅ {self.uid_prefix} Flexible consensus scoring complete for slot {slot}"
        )

    async def _run_flexible_p2p_consensus(self, slot: int, validators: List[str]):
        """Run P2P consensus with flexible validator set"""
        logger.info(
            f"🤝 {self.uid_prefix} Starting P2P consensus with {len(validators)} validators"
        )

        try:
            # Broadcast scores to flexible validator set
            await self.broadcast_scores_to_validators_flexible(slot, validators)

            # Collect scores with adaptive timeout
            await self.collect_validator_scores_flexible(slot, validators)

            # Aggregate results
            await self.aggregate_scores_flexible(slot)

        except Exception as e:
            logger.error(f"❌ {self.uid_prefix} Error in flexible P2P consensus: {e}")
            raise

    async def broadcast_scores_to_validators_flexible(
        self, slot: int, validators: List[str]
    ):
        """Broadcast scores to flexible validator set"""
        if slot not in self.core.slot_scores:
            logger.warning(
                f"⚠️ {self.uid_prefix} No scores to broadcast for slot {slot}"
            )
            return

        scores = self.core.slot_scores[slot]
        logger.info(
            f"📡 {self.uid_prefix} Broadcasting {len(scores)} scores to {len(validators)} validators"
        )

        # Use existing broadcast logic but with flexible validator set
        broadcast_tasks = []
        for validator_uid in validators:
            if validator_uid != self.core.info.uid:  # Don't broadcast to self
                task = self.broadcast_scores_to_validator(validator_uid, scores, slot)
                broadcast_tasks.append(task)

        if broadcast_tasks:
            results = await asyncio.gather(*broadcast_tasks, return_exceptions=True)
            successful = sum(1 for r in results if not isinstance(r, Exception))
            logger.info(
                f"📡 {self.uid_prefix} Broadcast complete: {successful}/{len(broadcast_tasks)} successful"
            )

    async def broadcast_scores_to_validator(
        self, validator_uid: str, scores: List[ValidatorScore], slot: int
    ) -> bool:
        """
        Broadcast scores to a specific validator by UID.

        Args:
            validator_uid: Target validator UID
            scores: List of scores to broadcast
            slot: Current slot number

        Returns:
            True if successfully sent
        """
        try:
            # Get validator info from UID
            validator_info = None

            # Try to find validator in stored validators_info
            if (
                hasattr(self.core, "validators_info")
                and validator_uid in self.core.validators_info
            ):
                validator_info = self.core.validators_info[validator_uid]

            # If not found, try to get from active validators
            if not validator_info:
                active_validators = await self._get_active_validators()
                for validator in active_validators:
                    if validator.uid == validator_uid:
                        validator_info = validator
                        break

            # If still not found, create a minimal ValidatorInfo with API endpoint guess
            if not validator_info:
                # Extract validator number from UID for endpoint guessing
                if "validator_1" in validator_uid.lower() or "1" in validator_uid:
                    api_endpoint = "http://localhost:8001"
                elif "validator_2" in validator_uid.lower() or "2" in validator_uid:
                    api_endpoint = "http://localhost:8002"
                elif "validator_3" in validator_uid.lower() or "3" in validator_uid:
                    api_endpoint = "http://localhost:8003"
                else:
                    # Default fallback
                    api_endpoint = "http://localhost:8001"

                # Create minimal ValidatorInfo
                from ..core.datatypes import ValidatorInfo

                validator_info = ValidatorInfo(
                    uid=validator_uid,
                    api_endpoint=api_endpoint,
                    address="0x0000000000000000000000000000000000000000",
                    stake=0,
                )

                logger.debug(
                    f"📡 {self.uid_prefix} Created minimal ValidatorInfo for {validator_uid} -> {api_endpoint}"
                )

            # Use existing P2P method to send scores
            broadcast_id = f"flexible_broadcast_{slot}_{int(time.time())}"
            success = await self._send_scores_to_validator_p2p(
                validator_info, scores, broadcast_id
            )

            if success:
                logger.debug(
                    f"📡 {self.uid_prefix} Successfully sent scores to {validator_uid}"
                )
            else:
                logger.warning(
                    f"📡 {self.uid_prefix} Failed to send scores to {validator_uid}"
                )

            return success

        except Exception as e:
            logger.error(
                f"📡 {self.uid_prefix} Error broadcasting scores to {validator_uid}: {e}"
            )
            return False

    async def collect_validator_scores_flexible(self, slot: int, validators: List[str]):
        """Collect validator scores with flexible timeout"""
        logger.info(
            f"📥 {self.uid_prefix} Collecting scores from {len(validators)} validators for slot {slot}"
        )

        # Calculate adaptive timeout based on validator count
        base_timeout = SCORE_COLLECTION_TIMEOUT
        if len(validators) < MAJORITY_THRESHOLD:
            # Extend timeout for smaller validator sets (reduced for 3.5min cycles)
            timeout = base_timeout + 20
            logger.info(
                f"🔄 {self.uid_prefix} Extended timeout for smaller validator set: {timeout}s"
            )
        else:
            timeout = base_timeout

        # Use existing collection logic with adaptive timeout
        start_time = time.time()
        expected_validators = [v for v in validators if v != self.core.info.uid]

        while time.time() - start_time < timeout:
            # Check collection progress
            if slot in self.core.received_validator_scores:
                received_count = len(self.core.received_validator_scores[slot])
                logger.debug(
                    f"📥 {self.uid_prefix} Received scores from {received_count}/{len(expected_validators)} validators"
                )

                # Flexible threshold: proceed if we have enough scores
                if received_count >= len(expected_validators) * 0.6:  # 60% threshold
                    logger.info(
                        f"✅ {self.uid_prefix} Sufficient scores collected: {received_count}/{len(expected_validators)}"
                    )
                    break

            await asyncio.sleep(2)

        final_count = len(self.core.received_validator_scores.get(slot, {}))
        logger.info(
            f"📥 {self.uid_prefix} Score collection complete: {final_count}/{len(expected_validators)} received"
        )

    async def aggregate_validator_scores(self, slot: int):
        """
        Aggregate validator scores for a given slot.

        This method aggregates both local scores and P2P received scores
        into the slot_aggregated_scores structure.

        Args:
            slot: Current slot number
        """
        try:
            logger.info(
                f"🔄 {self.uid_prefix} Aggregating validator scores for slot {slot}"
            )

            # Initialize slot aggregated scores if needed
            if slot not in self.core.slot_aggregated_scores:
                self.core.slot_aggregated_scores[slot] = {}

            # Get local scores for this slot
            local_scores = {}
            if slot in self.core.slot_scores:
                for score in self.core.slot_scores[slot]:
                    local_scores[score.miner_uid] = score.score

            # Add local scores to aggregated scores
            for miner_uid, score in local_scores.items():
                if miner_uid not in self.core.slot_aggregated_scores[slot]:
                    self.core.slot_aggregated_scores[slot][miner_uid] = {}

                # Add this validator's local score
                self.core.slot_aggregated_scores[slot][miner_uid][
                    self.core.info.uid
                ] = score

            # Add P2P received scores from other validators
            p2p_scores_added = 0

            # Check if we have received scores for this slot
            if slot in self.core.received_validator_scores:
                p2p_scores = self.core.received_validator_scores[slot]

                for validator_uid, validator_scores in p2p_scores.items():
                    if isinstance(validator_scores, dict):
                        for task_id, score_obj in validator_scores.items():
                            miner_uid = getattr(score_obj, "miner_uid", None)
                            score_value = getattr(score_obj, "score", 0.0)

                            if miner_uid:
                                # Initialize miner entry if needed
                                if (
                                    miner_uid
                                    not in self.core.slot_aggregated_scores[slot]
                                ):
                                    self.core.slot_aggregated_scores[slot][
                                        miner_uid
                                    ] = {}

                                # Add P2P score from this validator
                                self.core.slot_aggregated_scores[slot][miner_uid][
                                    validator_uid
                                ] = score_value
                                p2p_scores_added += 1
                    elif isinstance(validator_scores, list):
                        # Handle list of scores
                        for score_obj in validator_scores:
                            miner_uid = getattr(score_obj, "miner_uid", None)
                            score_value = getattr(score_obj, "score", 0.0)

                            if miner_uid:
                                if (
                                    miner_uid
                                    not in self.core.slot_aggregated_scores[slot]
                                ):
                                    self.core.slot_aggregated_scores[slot][
                                        miner_uid
                                    ] = {}

                                self.core.slot_aggregated_scores[slot][miner_uid][
                                    validator_uid
                                ] = score_value
                                p2p_scores_added += 1

            # Log aggregation results
            total_miners = len(self.core.slot_aggregated_scores[slot])
            total_local_scores = len(local_scores)

            logger.info(
                f"✅ {self.uid_prefix} Aggregated scores for slot {slot}: "
                f"{total_miners} miners, {total_local_scores} local scores, {p2p_scores_added} P2P scores"
            )

            return self.core.slot_aggregated_scores[slot]

        except Exception as e:
            logger.error(
                f"❌ {self.uid_prefix} Error aggregating validator scores for slot {slot}: {e}"
            )
            return {}

    async def aggregate_scores_flexible(self, slot: int):
        """Aggregate scores with flexible validation"""
        logger.info(
            f"🔄 {self.uid_prefix} Aggregating flexible consensus scores for slot {slot}"
        )

        # Use existing aggregation logic
        await self.aggregate_validator_scores(slot)

        # Additional flexible validation
        if slot in self.core.slot_aggregated_scores:
            aggregated = self.core.slot_aggregated_scores[slot]
            logger.info(
                f"✅ {self.uid_prefix} Aggregated scores for {len(aggregated)} miners in slot {slot}"
            )
        else:
            logger.warning(f"⚠️ {self.uid_prefix} No aggregated scores for slot {slot}")

    async def _run_flexible_metagraph_phase(self, slot: int):
        """Run metagraph update phase with flexibility"""
        logger.info(
            f"🌐 {self.uid_prefix} Starting flexible metagraph update for slot {slot}"
        )

        try:
            # STEP 1: SLOT-BASED METAGRAPH SYNCHRONIZATION - wait for exact metagraph timing
            logger.info(
                f"🌐 {self.uid_prefix} Waiting for slot-based metagraph update for slot {slot}"
            )

            # Calculate exact metagraph timing based on slot number
            from mt_core.consensus.slot_coordinator import EPOCH_START

            slot_start_time = EPOCH_START + (
                slot * self.core.slot_config.slot_duration_minutes * 60
            )
            task_cutoff_time = slot_start_time + (
                self.core.slot_config.task_assignment_minutes * 60
            )
            consensus_start_time = task_cutoff_time
            consensus_end_time = consensus_start_time + (
                self.core.slot_config.consensus_minutes * 60
            )
            metagraph_start_time = consensus_end_time

            current_time = int(time.time())

            # Wait for exact metagraph start time
            if current_time < metagraph_start_time:
                wait_time = metagraph_start_time - current_time
                logger.info(
                    f"⏰ {self.uid_prefix} Waiting {wait_time}s for SLOT-BASED metagraph start (slot {slot})"
                )
                await asyncio.sleep(wait_time)

            logger.info(
                f"✅ {self.uid_prefix} Slot-based metagraph update started for slot {slot}"
            )

            # === METAGRAPH UPDATE FIX: Only update when there are transactions ===

            # Check if we have aggregated scores to submit
            has_aggregated_scores = (
                hasattr(self.core, "slot_aggregated_scores")
                and slot in self.core.slot_aggregated_scores
                and len(self.core.slot_aggregated_scores[slot]) > 0
            )

            # Check if we have any scores at all
            has_any_scores = (
                hasattr(self.core, "slot_scores")
                and slot in self.core.slot_scores
                and len(self.core.slot_scores[slot]) > 0
            )

            # DEBUG: Log score status
            if has_aggregated_scores:
                scores_count = len(self.core.slot_aggregated_scores[slot])
                logger.info(
                    f"🔍 {self.uid_prefix} DEBUG: Found {scores_count} aggregated scores for slot {slot}"
                )
            else:
                logger.warning(
                    f"🔍 {self.uid_prefix} DEBUG: No aggregated scores found for slot {slot}"
                )

            # === FIX RULE 1: Skip update when no scores available ===
            if not has_aggregated_scores and not has_any_scores:
                logger.warning(
                    f"🚫 {self.uid_prefix} SKIPPING metagraph update - no scores available for slot {slot}"
                )
                logger.info(
                    f"✅ {self.uid_prefix} Flexible metagraph update skipped for slot {slot} (no scores)"
                )
                return

            # === FIX RULE 2: Check if we already updated this slot ===
            slot_update_key = f"slot_{slot}_updated"
            if hasattr(self, slot_update_key) and getattr(self, slot_update_key, False):
                logger.warning(
                    f"🚫 {self.uid_prefix} SKIPPING metagraph update - already updated slot {slot}"
                )
                logger.info(
                    f"✅ {self.uid_prefix} Flexible metagraph update skipped for slot {slot} (already updated)"
                )
                return

            # === FIX RULE 3: Only proceed if we have minimum scores ===
            if has_aggregated_scores:
                scores_count = len(self.core.slot_aggregated_scores[slot])
                if scores_count < 1:  # require_minimum_scores: 1
                    logger.warning(
                        f"🚫 {self.uid_prefix} SKIPPING metagraph update - insufficient scores ({scores_count}) for slot {slot}"
                    )
                    logger.info(
                        f"✅ {self.uid_prefix} Flexible metagraph update skipped for slot {slot} (insufficient scores)"
                    )
                    return
            elif has_any_scores:
                scores_count = len(self.core.slot_scores[slot])
                if scores_count < 1:  # require_minimum_scores: 1
                    logger.warning(
                        f"🚫 {self.uid_prefix} SKIPPING metagraph update - insufficient scores ({scores_count}) for slot {slot}"
                    )
                    logger.info(
                        f"✅ {self.uid_prefix} Flexible metagraph update skipped for slot {slot} (insufficient scores)"
                    )
                    return
            else:
                logger.warning(
                    f"🚫 {self.uid_prefix} SKIPPING metagraph update - no scores at all for slot {slot}"
                )
                logger.info(
                    f"✅ {self.uid_prefix} Flexible metagraph update skipped for slot {slot} (no scores)"
                )
                return

            # Register metagraph participation
            logger.info(f"📝 {self.uid_prefix} Registering metagraph phase entry...")
            await self.core.slot_coordinator.register_phase_entry(
                slot, SlotPhase.METAGRAPH_UPDATE, {"flexible_join": True}
            )
            logger.info(f"✅ {self.uid_prefix} Metagraph phase entry registered")

            # Wait for metagraph coordination
            logger.info(f"⏳ {self.uid_prefix} Waiting for metagraph coordination...")
            ready_validators = (
                await self.core.slot_coordinator.wait_for_phase_consensus_flexible(
                    slot, SlotPhase.METAGRAPH_UPDATE, timeout=60
                )
            )
            logger.info(
                f"🤝 {self.uid_prefix} Metagraph coordination complete: {len(ready_validators)} validators"
            )

            # Submit to blockchain
            logger.info(f"🔗 {self.uid_prefix} Starting blockchain submission...")
            await self.submit_to_blockchain(slot)
            logger.info(f"✅ {self.uid_prefix} Blockchain submission complete")

            # === FIX RULE 4: Mark slot as updated to prevent duplicate updates ===
            setattr(self, slot_update_key, True)
            logger.info(f"✅ {self.uid_prefix} Marked slot {slot} as updated")

        except Exception as e:
            logger.error(
                f"❌ {self.uid_prefix} Error in metagraph phase for slot {slot}: {e}"
            )
            import traceback

            logger.error(f"❌ {self.uid_prefix} Traceback: {traceback.format_exc()}")

        logger.info(
            f"✅ {self.uid_prefix} Flexible metagraph update complete for slot {slot}"
        )

    def _update_participation_rate(self, success: bool):
        """Update consensus participation rate"""
        decay_factor = 0.95
        self.consensus_participation_rate = (
            self.consensus_participation_rate * decay_factor
            + (1.0 if success else 0.0) * (1 - decay_factor)
        )

    def get_flexible_status(self) -> Dict[str, Any]:
        """Get current flexible consensus status"""
        if not self.flexible_mode_enabled:
            return {"flexible_mode": False}

        current_slot = self.core.slot_coordinator.get_current_blockchain_slot()
        current_phase, phase_time, remaining = (
            self.core.slot_coordinator.get_slot_phase(current_slot)
        )

        return {
            "flexible_mode": True,
            "current_slot": current_slot,
            "current_phase": current_phase.value,
            "phase_time_elapsed": phase_time,
            "phase_time_remaining": remaining,
            "participation_rate": round(self.consensus_participation_rate, 3),
            "last_successful_consensus": self.last_successful_consensus,
            "metrics": self.flexible_metrics.copy(),
            "can_join_mid_slot": self.core.slot_coordinator.slot_config.allow_mid_slot_join,
            "auto_extend_enabled": self.core.slot_coordinator.slot_config.auto_extend_on_consensus,
        }

    # === HELPER METHODS FOR FLEXIBLE TASK ASSIGNMENT ===

    async def _get_available_miners_for_slot(self, slot: int) -> List:
        """
        Get available miners for task assignment in this slot.

        Args:
            slot: Current slot number

        Returns:
            List of available miner info objects
        """
        try:
            # Get all miners from metagraph/storage
            all_miners = []

            # Try to get miners from stored miners_info
            if hasattr(self.core, "miners_info") and self.core.miners_info:
                all_miners = list(self.core.miners_info.values())
                logger.debug(
                    f"📋 {self.uid_prefix} Found {len(all_miners)} miners from stored info"
                )

            # If no stored miners, try to get from metagraph
            if not all_miners:
                try:
                    # Get miners from blockchain/metagraph
                    active_validators = await self._get_active_validators()
                    if hasattr(self.core, "tasks") and hasattr(
                        self.core.tasks, "get_available_miners"
                    ):
                        all_miners = await self.core.tasks.get_available_miners()
                    else:
                        # Create mock miners for testing if no real ones available
                        from ..core.datatypes import MinerInfo

                        all_miners = [
                            MinerInfo(
                                uid="miner_1",
                                address="0x90F79bf6EB2c4f870365E785982E1f101E93b906",
                                stake=0,
                                api_endpoint="http://localhost:8101",
                            ),
                            MinerInfo(
                                uid="miner_2",
                                address="0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65",
                                stake=0,
                                api_endpoint="http://localhost:8102",
                            ),
                        ]
                        logger.info(
                            f"📋 {self.uid_prefix} Using mock miners for testing"
                        )

                except Exception as e:
                    logger.debug(
                        f"📋 {self.uid_prefix} Could not fetch miners from metagraph: {e}"
                    )
                    all_miners = []

            # Filter available miners (not busy)
            available_miners = []
            for miner in all_miners:
                miner_uid = getattr(miner, "uid", None)
                if miner_uid and miner_uid not in self.core.miner_is_busy:
                    available_miners.append(miner)

            logger.info(
                f"📋 {self.uid_prefix} Found {len(available_miners)}/{len(all_miners)} available miners for slot {slot}"
            )

            return available_miners[:5]  # Limit to 5 miners per slot

        except Exception as e:
            logger.error(f"❌ {self.uid_prefix} Error getting available miners: {e}")
            return []

    async def _assign_tasks_to_miners(self, slot: int, miners: List) -> bool:
        """
        Assign tasks to selected miners for this slot.

        Args:
            slot: Current slot number
            miners: List of miners to assign tasks to

        Returns:
            True if tasks were assigned successfully
        """
        try:
            if not miners:
                logger.warning(f"📋 {self.uid_prefix} No miners to assign tasks to")
                return False

            logger.info(
                f"📋 {self.uid_prefix} Assigning tasks to {len(miners)} miners for slot {slot}"
            )

            # Use the tasks module if available
            if hasattr(self.core, "tasks"):
                # Try slot-based task assignment
                if hasattr(self.core.tasks, "assign_tasks_for_slot"):
                    await self.core.tasks.assign_tasks_for_slot(slot, miners)
                elif hasattr(self.core.tasks, "cardano_send_tasks"):
                    await self.core.tasks.cardano_send_tasks(slot, miners)
                else:
                    # Fallback to basic task assignment
                    await self._basic_task_assignment(slot, miners)
            else:
                # Direct task assignment without tasks module
                await self._basic_task_assignment(slot, miners)

            logger.info(
                f"✅ {self.uid_prefix} Successfully assigned tasks for slot {slot}"
            )
            return True

        except Exception as e:
            logger.error(f"❌ {self.uid_prefix} Error assigning tasks to miners: {e}")
            return False

    async def _basic_task_assignment(self, slot: int, miners: List):
        """
        Basic task assignment implementation as fallback.

        Args:
            slot: Current slot number
            miners: List of miners to assign tasks to
        """
        logger.info(
            f"📋 {self.uid_prefix} Using basic task assignment for {len(miners)} miners"
        )

        for miner in miners:
            try:
                miner_uid = getattr(miner, "uid", None)
                if not miner_uid:
                    continue

                # Create basic task data
                task_id = f"slot_{slot}_{miner_uid}_{int(time.time())}"
                task_data = {
                    "slot": slot,
                    "miner_uid": miner_uid,
                    "validator_uid": self.core.info.uid,
                    "prompt": "Generate an image of a beautiful landscape with mountains and a lake",
                    "seed": slot * 42,
                    "created_at": time.time(),
                    "deadline": time.time() + 60,  # 1 minute to complete
                }

                # Create assignment object
                assignment = TaskAssignment(
                    task_id=task_id,
                    task_data=task_data,
                    miner_uid=miner_uid,
                    validator_uid=self.core.info.uid,
                    timestamp_sent=time.time(),
                    expected_result_format={"image": "base64_string"},
                )

                # Store assignment
                self.core.tasks_sent[task_id] = assignment
                self.core.miner_is_busy.add(miner_uid)

                # Try to send task to miner
                miner_endpoint = getattr(miner, "api_endpoint", None)
                if miner_endpoint:
                    # Create task model for sending
                    task_model = TaskModel(task_id=task_id, **task_data)

                    # Send via HTTP (simplified)
                    success = await self._send_task_to_miner(miner_endpoint, task_model)
                    if success:
                        logger.info(
                            f"📋 {self.uid_prefix} Task {task_id} sent to miner {miner_uid}"
                        )
                    else:
                        logger.debug(
                            f"📤 {self.uid_prefix} Could not send task {task_id} to miner {miner_uid}"
                        )
                        self.core.miner_is_busy.discard(miner_uid)
                        if task_id in self.core.tasks_sent:
                            del self.core.tasks_sent[task_id]
                else:
                    logger.warning(
                        f"⚠️ {self.uid_prefix} No API endpoint for miner {miner_uid}"
                    )

            except Exception as e:
                logger.error(
                    f"❌ {self.uid_prefix} Error creating task for miner {getattr(miner, 'uid', 'unknown')}: {e}"
                )

    async def _send_task_to_miner(self, miner_endpoint: str, task: TaskModel) -> bool:
        """
        Send task to miner via HTTP.

        Args:
            miner_endpoint: Miner's API endpoint
            task: Task to send

        Returns:
            True if sent successfully
        """
        try:
            # Create new HTTP client for each request to avoid connection issues
            import httpx

            url = f"{miner_endpoint.rstrip('/')}/receive-task"
            payload = task.dict() if hasattr(task, "dict") else task.__dict__

            # ENHANCED DEBUG: Log detailed information
            logger.info(f"📤 {self.uid_prefix} ATTEMPTING to send task to {url}")
            logger.info(f"📤 {self.uid_prefix} Task payload: {payload}")

            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                logger.info(
                    f"📤 {self.uid_prefix} HTTP client created, sending POST request..."
                )
                response = await client.post(url, json=payload)
                logger.info(
                    f"📤 {self.uid_prefix} HTTP response received: {response.status_code}"
                )

            if response.status_code == 200:
                logger.info(f"✅ {self.uid_prefix} Task sent successfully to miner")
                logger.info(f"✅ {self.uid_prefix} Response: {response.text}")
                return True
            else:
                logger.error(
                    f"❌ {self.uid_prefix} Miner returned status {response.status_code}"
                )
                logger.error(f"❌ {self.uid_prefix} Response text: {response.text}")
                return False

        except Exception as e:
            # Only log as debug since not all miners may be running
            logger.debug(
                f"📤 {self.uid_prefix} Could not send task to {miner_endpoint}: {e}"
            )
            return False

    # === SIMPLIFIED HELPERS USING EXISTING INFRASTRUCTURE ===

    async def _assign_single_task(self, slot: int, miner, round_num: int) -> str:
        """
        Assign a single task to one miner.

        Args:
            slot: Current slot number
            miner: Single miner to assign task to
            round_num: Round number for this task

        Returns:
            Task ID if successful, None if failed
        """
        try:
            miner_uid = getattr(miner, "uid", None)
            if not miner_uid:
                logger.warning(f"📋 {self.uid_prefix} Miner has no UID")
                return None

            # Create unique task ID
            task_id = f"slot_{slot}_round_{round_num}_{miner_uid}_{int(time.time())}"
            task_data = {
                "slot": slot,
                "round": round_num,
                "task_id": task_id,
                "miner_uid": miner_uid,
                "validator_uid": self.core.info.uid,
                "prompt": f"Generate an image of a beautiful landscape (round {round_num})",
                "seed": slot * 42 + round_num,
                "created_at": time.time(),
                "deadline": time.time() + 15,  # 15s to complete
            }

            # Create assignment
            assignment = TaskAssignment(
                task_id=task_id,
                task_data=task_data,
                miner_uid=miner_uid,
                validator_uid=self.core.info.uid,
                timestamp_sent=time.time(),
                expected_result_format={"image": "base64_string"},
            )

            # Store assignment
            self.core.tasks_sent[task_id] = assignment

            # Send task to miner
            miner_endpoint = getattr(miner, "api_endpoint", None)
            if miner_endpoint:
                task_model = TaskModel(task_id=task_id, **task_data)
                success = await self._send_task_to_miner(miner_endpoint, task_model)
                if success:
                    logger.debug(f"📋 Task {task_id} sent to {miner_uid}")
                    return task_id
                else:
                    # Clean up failed task
                    if task_id in self.core.tasks_sent:
                        del self.core.tasks_sent[task_id]
                    return None
            else:
                logger.warning(f"⚠️ No API endpoint for miner {miner_uid}")
                return None

        except Exception as e:
            logger.error(
                f"❌ Error creating task for miner {getattr(miner, 'uid', 'unknown')}: {e}"
            )
            return None

    async def _wait_and_score_single_task(
        self, slot: int, task_id: str, timeout: float = 10
    ):
        """
        Wait for result from specific task and score it immediately.

        Args:
            slot: Current slot number
            task_id: Specific task ID to wait for
            timeout: How long to wait for this task
        """
        try:
            start_time = time.time()

            # Wait for this specific task result
            while time.time() - start_time < timeout:
                # Check if result arrived for this task
                async with self.core.results_buffer_lock:
                    if task_id in self.core.results_buffer:
                        result = self.core.results_buffer[task_id]
                        assignment = self.core.tasks_sent.get(task_id)

                        if assignment:
                            # Score immediately
                            try:
                                if isinstance(
                                    result.result_data, dict
                                ) and result.result_data.get("timeout"):
                                    score_value = 0.0
                                else:
                                    score_value = self._calculate_score(
                                        assignment.task_data, result.result_data
                                    )

                                # Create validator score
                                validator_score = ValidatorScore(
                                    task_id=task_id,
                                    miner_uid=result.miner_uid,
                                    validator_uid=self.core.info.uid,
                                    score=score_value,
                                    timestamp=time.time(),
                                    cycle=slot,
                                )

                                # Store score immediately
                                if slot not in self.core.slot_scores:
                                    self.core.slot_scores[slot] = []
                                self.core.slot_scores[slot].append(validator_score)

                                logger.info(
                                    f"🎯 Scored task {task_id}: {score_value:.3f} for miner {result.miner_uid}"
                                )

                                # Clean up
                                del self.core.results_buffer[task_id]
                                if task_id in self.core.tasks_sent:
                                    del self.core.tasks_sent[task_id]

                                return  # Success - scored the task

                            except Exception as e:
                                logger.error(f"❌ Error scoring task {task_id}: {e}")

                # Brief pause before checking again
                await asyncio.sleep(0.5)

            # Timeout - no result received
            logger.warning(f"⏰ Task {task_id} timed out after {timeout}s")

            # Clean up timed out task
            if task_id in self.core.tasks_sent:
                assignment = self.core.tasks_sent[task_id]
                miner_uid = assignment.miner_uid

                # Score as timeout
                validator_score = ValidatorScore(
                    task_id=task_id,
                    miner_uid=miner_uid,
                    validator_uid=self.core.info.uid,
                    score=0.0,  # Timeout score
                    timestamp=time.time(),
                    cycle=slot,
                )

                if slot not in self.core.slot_scores:
                    self.core.slot_scores[slot] = []
                self.core.slot_scores[slot].append(validator_score)

                logger.info(
                    f"⏰ Scored task {task_id}: 0.0 (timeout) for miner {miner_uid}"
                )

                del self.core.tasks_sent[task_id]

        except Exception as e:
            logger.error(f"❌ Error waiting for task {task_id}: {e}")

    async def _assign_task_batch(self, slot: int, miners: List, round_num: int):
        """
        Assign a batch of tasks to miners in a specific round.

        Args:
            slot: Current slot number
            miners: List of miners to assign tasks to
            round_num: Round number for this batch
        """
        try:
            logger.info(
                f"📋 {self.uid_prefix} Assigning task batch {round_num} to {len(miners)} miners"
            )

            batch_tasks = []
            for miner in miners:
                try:
                    miner_uid = getattr(miner, "uid", None)
                    if not miner_uid:
                        continue

                    # Create unique task for this round
                    task_id = (
                        f"slot_{slot}_round_{round_num}_{miner_uid}_{int(time.time())}"
                    )
                    task_data = {
                        "slot": slot,
                        "round": round_num,
                        "task_id": task_id,
                        "miner_uid": miner_uid,
                        "validator_uid": self.core.info.uid,
                        "prompt": f"Generate an image of a beautiful landscape (round {round_num})",
                        "seed": slot * 42 + round_num,
                        "created_at": time.time(),
                        "deadline": time.time() + 30,  # 30s to complete
                    }

                    # Create assignment
                    assignment = TaskAssignment(
                        task_id=task_id,
                        task_data=task_data,
                        miner_uid=miner_uid,
                        validator_uid=self.core.info.uid,
                        timestamp_sent=time.time(),
                        expected_result_format={"image": "base64_string"},
                    )

                    # Store assignment
                    self.core.tasks_sent[task_id] = assignment

                    # Send task
                    miner_endpoint = getattr(miner, "api_endpoint", None)
                    if miner_endpoint:
                        task_model = TaskModel(task_id=task_id, **task_data)
                        success = await self._send_task_to_miner(
                            miner_endpoint, task_model
                        )
                        if success:
                            batch_tasks.append(task_id)
                            logger.debug(f"📋 Task {task_id} sent to {miner_uid}")
                        else:
                            # Clean up failed task
                            if task_id in self.core.tasks_sent:
                                del self.core.tasks_sent[task_id]

                except Exception as e:
                    logger.error(
                        f"❌ Error creating task for miner {getattr(miner, 'uid', 'unknown')}: {e}"
                    )

            logger.info(
                f"✅ {self.uid_prefix} Batch {round_num}: {len(batch_tasks)} tasks sent successfully"
            )
            return batch_tasks

        except Exception as e:
            logger.error(f"❌ {self.uid_prefix} Error in task batch assignment: {e}")
            return []

    async def _collect_and_score_results(
        self, slot: int, timeout: float = 30
    ):  # Increased from 20s to 30s
        """
        Collect results and score them immediately.

        Args:
            slot: Current slot number
            timeout: How long to wait for results
        """
        try:
            logger.info(
                f"📥 {self.uid_prefix} Collecting and scoring results for slot {slot} (timeout: {timeout}s)"
            )

            start_time = time.time()
            scored_count = 0

            while time.time() - start_time < timeout:
                # Check for new results in buffer
                async with self.core.results_buffer_lock:
                    new_results = []
                    for task_id, result in list(self.core.results_buffer.items()):
                        # Check if this result belongs to current slot
                        if task_id in self.core.tasks_sent:
                            assignment = self.core.tasks_sent[task_id]
                            task_slot = assignment.task_data.get("slot", -1)

                            if task_slot == slot:
                                new_results.append((task_id, result, assignment))
                                # Remove from buffer to avoid re-processing
                                del self.core.results_buffer[task_id]

                # Score new results immediately
                for task_id, result, assignment in new_results:
                    try:
                        # Calculate score
                        if isinstance(
                            result.result_data, dict
                        ) and result.result_data.get("timeout"):
                            score_value = 0.0
                        else:
                            score_value = self._calculate_score(
                                assignment.task_data, result.result_data
                            )

                        # Create validator score
                        validator_score = ValidatorScore(
                            task_id=task_id,
                            miner_uid=result.miner_uid,
                            validator_uid=self.core.info.uid,
                            score=score_value,
                            timestamp=time.time(),
                            cycle=slot,
                        )

                        # Store score immediately
                        if slot not in self.core.slot_scores:
                            self.core.slot_scores[slot] = []
                        self.core.slot_scores[slot].append(validator_score)

                        scored_count += 1
                        logger.debug(f"📊 Scored task {task_id}: {score_value:.3f}")

                        # Clean up task
                        if task_id in self.core.tasks_sent:
                            del self.core.tasks_sent[task_id]

                    except Exception as e:
                        logger.error(f"❌ Error scoring task {task_id}: {e}")

                # Brief pause before checking again
                await asyncio.sleep(1)

            logger.info(
                f"✅ {self.uid_prefix} Collected and scored {scored_count} results in {timeout}s"
            )

        except Exception as e:
            logger.error(
                f"❌ {self.uid_prefix} Error collecting and scoring results: {e}"
            )

    async def _calculate_average_scores_per_miner(self, slot: int) -> Dict[str, float]:
        """
        Calculate average scores per miner from all tasks in this slot.

        Args:
            slot: Current slot number

        Returns:
            Dictionary mapping miner_uid to average score
        """
        try:
            if slot not in self.core.slot_scores:
                logger.warning(f"📊 {self.uid_prefix} No scores found for slot {slot}")
                return {}

            scores = self.core.slot_scores[slot]
            if not scores:
                logger.warning(
                    f"📊 {self.uid_prefix} Empty scores list for slot {slot}"
                )
                return {}

            # Group scores by miner
            miner_scores = defaultdict(list)
            for score in scores:
                miner_scores[score.miner_uid].append(score.score)

            # Calculate averages
            averaged_scores = {}
            for miner_uid, score_list in miner_scores.items():
                avg_score = sum(score_list) / len(score_list)
                averaged_scores[miner_uid] = avg_score

                logger.info(
                    f"📊 {self.uid_prefix} Miner {miner_uid}: {len(score_list)} tasks, avg score: {avg_score:.4f}"
                )

            # Replace slot_scores with averaged scores (one per miner)
            averaged_score_objects = []
            for miner_uid, avg_score in averaged_scores.items():
                averaged_score = ValidatorScore(
                    task_id=f"averaged_slot_{slot}_{miner_uid}",
                    miner_uid=miner_uid,
                    validator_uid=self.core.info.uid,
                    score=avg_score,
                    timestamp=time.time(),
                    cycle=slot,
                )
                averaged_score_objects.append(averaged_score)

            # Replace with averaged scores for P2P
            self.core.slot_scores[slot] = averaged_score_objects

            logger.info(
                f"📊 {self.uid_prefix} Averaged scores for {len(averaged_scores)} miners in slot {slot}"
            )

            return averaged_scores

        except Exception as e:
            logger.error(f"❌ {self.uid_prefix} Error calculating average scores: {e}")
            return {}

    # === SIMPLIFIED HELPERS USING EXISTING INFRASTRUCTURE ===

    async def _fallback_sequential_assignment(
        self, slot: int, miners: List, remaining: float
    ):
        """Fallback assignment if no tasks module available"""
        logger.info(
            f"📋 {self.uid_prefix} Using fallback assignment for {len(miners)} miners"
        )
        # Basic fallback - just use existing assignment methods if available
        await self._basic_task_assignment(slot, miners)

    async def _sequential_fallback_assignment(
        self,
        slot: int,
        miners: List,
        remaining: float,
        task_assignment_end_time: float,
        task_round: int,
    ):
        """Sequential fallback assignment - giao từng task một như main logic"""
        logger.info(
            f"📋 {self.uid_prefix} Starting sequential fallback assignment for {len(miners)} miners"
        )

        # SEQUENTIAL TASK ASSIGNMENT LOOP (fallback version)
        while time.time() < task_assignment_end_time:
            remaining_time = task_assignment_end_time - time.time()
            if remaining_time <= 10:  # Stop if less than 10s remaining
                break

            logger.info(
                f"📋 {self.uid_prefix} Fallback sequential round {task_round} - {remaining_time:.1f}s remaining"
            )

            # SEQUENTIAL ASSIGNMENT: Giao từng miner một task (fallback version)
            round_scores = 0
            for miner in miners:
                try:
                    remaining_in_round = task_assignment_end_time - time.time()
                    if remaining_in_round <= 5:
                        break

                    # Giao 1 task cho 1 miner (fallback method)
                    task_sent = await self._send_single_task_to_miner(
                        slot, miner, task_round
                    )
                    if task_sent:
                        logger.info(
                            f"📤 {self.uid_prefix} Fallback task sent to miner {getattr(miner, 'uid', 'unknown')}"
                        )

                        # Chờ kết quả (3-20s) - Increased timeout for better task completion
                        result_timeout = min(20.0, remaining_in_round * 0.3)
                        await asyncio.sleep(result_timeout)

                        # Chấm điểm ngay lập tức cho task này
                        scored = await self._score_single_task_result(slot, task_sent)
                        if scored:
                            round_scores += 1
                            logger.info(
                                f"⚡ {self.uid_prefix} Fallback scored task from miner {getattr(miner, 'uid', 'unknown')}"
                            )

                        # Brief pause trước khi giao task cho miner tiếp theo
                        await asyncio.sleep(min(1.0, remaining_in_round * 0.05))

                except Exception as e:
                    logger.error(
                        f"❌ {self.uid_prefix} Fallback error with miner {getattr(miner, 'uid', 'unknown')}: {e}"
                    )
                    continue

            task_round += 1
            logger.info(
                f"✅ {self.uid_prefix} Fallback sequential round {task_round-1} completed: {round_scores} scores"
            )

            # Pause trước round tiếp theo
            await asyncio.sleep(min(2.0, remaining_time * 0.1))

        logger.info(
            f"✅ {self.uid_prefix} Sequential fallback completed: {task_round-1} rounds"
        )

    async def _score_immediate_results(self, slot: int):
        """Score any results received immediately"""
        try:
            if not hasattr(self.core, "results_buffer") or not self.core.results_buffer:
                return

            scored_count = 0

            # Check for any unscored results
            for task_id, result in list(self.core.results_buffer.items()):
                if task_id.startswith(f"slot_{slot}_"):
                    try:
                        # Quick scoring using existing logic
                        score = (
                            0.5 + (hash(result.result_data) % 100) / 200.0
                        )  # Score between 0.5-1.0

                        validator_score = ValidatorScore(
                            task_id=task_id,
                            miner_uid=result.miner_uid,
                            validator_uid=self.core.info.uid,
                            score=score,
                            timestamp=time.time(),
                            cycle=slot,
                        )

                        # Add to slot scores
                        if slot not in self.core.slot_scores:
                            self.core.slot_scores[slot] = []
                        self.core.slot_scores[slot].append(validator_score)

                        # Remove from buffer
                        del self.core.results_buffer[task_id]
                        scored_count += 1

                        logger.debug(
                            f"⚡ {self.uid_prefix} Quick scored {task_id}: {score:.3f}"
                        )

                    except Exception as e:
                        logger.error(
                            f"❌ {self.uid_prefix} Error scoring result {task_id}: {e}"
                        )

            if scored_count > 0:
                logger.info(f"⚡ {self.uid_prefix} Quick scored {scored_count} results")

        except Exception as e:
            logger.error(f"❌ {self.uid_prefix} Error in immediate scoring: {e}")

    async def _send_single_task_to_miner(
        self, slot: int, miner, task_round: int
    ) -> str:
        """
        Giao 1 task cho 1 miner và trả về task_id nếu thành công
        """
        try:
            miner_uid = getattr(miner, "uid", None)
            if not miner_uid:
                logger.warning(f"❌ {self.uid_prefix} Miner has no UID: {miner}")
                return None

            # Create unique task for this miner in this round
            task_id = f"slot_{slot}_r{task_round}_{miner_uid}_{int(time.time())}"

            # Task data for TaskModel (miner API expects these fields)
            task_data = {
                "task_id": task_id,
                "description": "Generate an image of a beautiful landscape with mountains and a lake",  # Required by TaskModel
                "deadline": str(int(time.time() + 30)),  # String format as expected
                "priority": 3,  # Optional priority 1-5
                "validator_endpoint": (
                    self.core.info.api_endpoint
                    if hasattr(self.core.info, "api_endpoint")
                    else None
                ),
                # Extra metadata for consensus tracking
                "slot": slot,
                "round": task_round,
                "miner_uid": miner_uid,
                "validator_uid": self.core.info.uid,
                "seed": (slot * 42) + task_round,
                "created_at": time.time(),
            }

            # Create assignment object
            assignment = TaskAssignment(
                task_id=task_id,
                task_data=task_data,
                miner_uid=miner_uid,
                validator_uid=self.core.info.uid,
                timestamp_sent=time.time(),
                expected_result_format={"image": "base64_string"},
            )

            # Store assignment
            self.core.tasks_sent[task_id] = assignment
            self.core.miner_is_busy.add(miner_uid)

            # Send task to miner
            miner_endpoint = getattr(miner, "api_endpoint", None)
            if miner_endpoint:
                logger.info(
                    f"📤 {self.uid_prefix} Attempting to send task to {miner_uid} at {miner_endpoint}"
                )
                # Create TaskModel with all required fields (including task_data)
                task_model = TaskModel(
                    task_id=task_data["task_id"],
                    description=task_data["description"],
                    deadline=task_data["deadline"],
                    priority=task_data["priority"],
                    validator_endpoint=task_data["validator_endpoint"],
                    task_data=task_data,  # Include full task_data dict
                )
                success = await self._send_task_to_miner(miner_endpoint, task_model)
                if success:
                    logger.info(
                        f"📤 {self.uid_prefix} Single task {task_id} sent to {miner_uid}"
                    )
                    return task_id
                else:
                    logger.debug(
                        f"📤 {self.uid_prefix} Could not send task to {miner_uid}"
                    )
                    # Cleanup on failure
                    self.core.miner_is_busy.discard(miner_uid)
                    if task_id in self.core.tasks_sent:
                        del self.core.tasks_sent[task_id]
            else:
                logger.warning(
                    f"❌ {self.uid_prefix} Miner {miner_uid} has no api_endpoint"
                )

            return None

        except Exception as e:
            logger.error(f"❌ {self.uid_prefix} Error sending single task: {e}")
            return None

    async def _score_single_task_result(self, slot: int, task_id: str) -> bool:
        """
        Chấm điểm 1 task - nếu có kết quả thì tính điểm, nếu timeout/no response thì cho 0 điểm
        """
        try:
            if not task_id:
                return False

            # Get task assignment info
            task_assignment = self.core.tasks_sent.get(task_id)
            if not task_assignment:
                logger.warning(
                    f"⚠️ {self.uid_prefix} No task assignment found for {task_id}"
                )
                return False

            miner_uid = task_assignment.miner_uid
            score = 0.0  # Default score for timeout/no response
            score_reason = "timeout/no_response"

            # Check if we have a result
            if task_id in self.core.results_buffer:
                result = self.core.results_buffer[task_id]

                # Check if result indicates error or timeout
                if isinstance(result.result_data, dict):
                    if result.result_data.get("timeout") or result.result_data.get(
                        "error_details"
                    ):
                        score = 0.0  # Error/timeout gets 0 score
                        score_reason = "error_or_timeout"
                    else:
                        # Calculate normal score using hash-based algorithm
                        score = (
                            0.5 + (hash(str(result.result_data)) % 100) / 200.0
                        )  # Score between 0.5-1.0
                        score_reason = "success"

                # Remove from buffer after processing
                del self.core.results_buffer[task_id]
            else:
                # No response from miner - give 0 score
                logger.debug(
                    f"⏰ {self.uid_prefix} Task {task_id} timeout - no response from miner {miner_uid}"
                )

            # Create validator score (always create one, even for 0 scores)
            validator_score = ValidatorScore(
                task_id=task_id,
                miner_uid=miner_uid,
                validator_uid=self.core.info.uid,
                score=score,
                timestamp=time.time(),
                cycle=slot,
            )

            # Add to slot scores
            if slot not in self.core.slot_scores:
                self.core.slot_scores[slot] = []
            self.core.slot_scores[slot].append(validator_score)

            # Cleanup busy state but keep task_sent until end of slot for late results
            self.core.miner_is_busy.discard(miner_uid)
            # Note: Don't delete tasks_sent here - keep for late results

            logger.debug(
                f"⚡ {self.uid_prefix} Scored task {task_id}: {score:.3f} ({score_reason})"
            )
            return True

        except Exception as e:
            logger.error(
                f"❌ {self.uid_prefix} Error scoring single task {task_id}: {e}"
            )
            return False

    async def _cleanup_old_tasks_sent(self):
        """Cleanup tasks_sent older than 5 minutes to prevent memory leak while keeping recent tasks for late results"""
        try:
            current_time = time.time()
            cleanup_threshold = 300  # 5 minutes in seconds
            old_task_ids = []

            for task_id, task_assignment in self.core.tasks_sent.items():
                if hasattr(task_assignment, "timestamp_sent"):
                    task_age = current_time - task_assignment.timestamp_sent
                    if task_age > cleanup_threshold:
                        old_task_ids.append(task_id)
                elif hasattr(task_assignment, "created_at"):
                    task_age = current_time - task_assignment.created_at
                    if task_age > cleanup_threshold:
                        old_task_ids.append(task_id)

            # Remove old tasks
            for task_id in old_task_ids:
                del self.core.tasks_sent[task_id]

            if old_task_ids:
                logger.info(
                    f"🧹 {self.uid_prefix} Cleaned up {len(old_task_ids)} old tasks (>5min)"
                )

        except Exception as e:
            logger.error(f"❌ {self.uid_prefix} Error cleaning up old tasks: {e}")

    async def _use_existing_slot_scores(
        self, slot: int, slot_scores: List
    ) -> Dict[str, float]:
        """Use scores already generated by tasks module"""
        try:
            # Group scores by miner
            miner_scores = defaultdict(list)
            for score in slot_scores:
                if hasattr(score, "miner_uid") and hasattr(score, "score"):
                    miner_scores[score.miner_uid].append(score.score)

            # Calculate averages if multiple scores per miner
            averaged_scores = {}
            for miner_uid, scores in miner_scores.items():
                if scores:
                    avg_score = sum(scores) / len(scores)
                    averaged_scores[miner_uid] = avg_score

                    if len(scores) > 1:
                        logger.info(
                            f"📊 {self.uid_prefix} Miner {miner_uid}: {len(scores)} scores averaged to {avg_score:.4f}"
                        )
                    else:
                        logger.info(
                            f"📊 {self.uid_prefix} Miner {miner_uid}: single score {avg_score:.4f}"
                        )

            return averaged_scores

        except Exception as e:
            logger.error(f"❌ {self.uid_prefix} Error processing existing scores: {e}")
            return {}

    async def _use_existing_broadcast_logic(self, slot: int, validators: List[str]):
        """Use existing broadcast_scores_logic from scoring.py"""
        try:
            logger.info(
                f"🤝 {self.uid_prefix} Using existing broadcast_scores_logic for P2P"
            )

            # Import existing broadcast logic
            from .scoring import broadcast_scores_logic

            # Get local scores for broadcasting
            local_scores = self.core.slot_scores.get(slot, [])

            if local_scores:
                # Use existing broadcast infrastructure
                success = await broadcast_scores_logic(
                    validator_scores=local_scores,
                    validator_info_dict=getattr(self.core, "validators_info", {}),
                    validator_instance=getattr(self.core, "validator_instance", self),
                    uid_prefix=self.uid_prefix,
                )

                if success:
                    logger.info(
                        f"✅ {self.uid_prefix} Successfully used existing broadcast logic"
                    )
                else:
                    logger.warning(
                        f"⚠️ {self.uid_prefix} Existing broadcast logic failed"
                    )
            else:
                logger.warning(f"⚠️ {self.uid_prefix} No local scores to broadcast")

        except Exception as e:
            logger.error(
                f"❌ {self.uid_prefix} Error using existing broadcast logic: {e}"
            )
