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
from typing import Dict, List, Optional, Any

import httpx
from web3 import Web3
from eth_account import Account

from ..core.datatypes import ValidatorScore, MinerResult, ValidatorInfo
from ..formulas.incentive import calculate_miner_incentive
from ..formulas.performance import calculate_adjusted_miner_performance
from ..formulas.trust_score import update_trust_score
from .scoring import score_results_logic, broadcast_scores_logic
from .slot_coordinator import SlotPhase
from ..core_client.contract_client import ModernTensorCoreClient

logger = logging.getLogger(__name__)

# Constants
CONSENSUS_TIMEOUT = 120
SCORE_BROADCAST_TIMEOUT = 30
MIN_VALIDATORS_FOR_CONSENSUS = 2
HTTP_TIMEOUT = 10.0

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

        # Initialize Core client if account is available
        if hasattr(core_node, "account") and core_node.account:
            self._initialize_core_client()

    def _initialize_core_client(self):
        """Initialize Core blockchain client for consensus operations."""
        try:
            from web3 import Web3
            from ..core_client.contract_client import ModernTensorCoreClient

            # Get Core network configuration
            core_node_url = getattr(
                self.core, "core_node_url", "https://rpc.test.btcs.network"
            )
            contract_address = getattr(self.core, "contract_address", None)

            if not contract_address:
                logger.warning(
                    f"⚠️ {self.uid_prefix} No contract address configured, Core client not initialized"
                )
                return

            # Initialize Web3 connection
            w3 = Web3(Web3.HTTPProvider(core_node_url))

            if not w3.is_connected():
                logger.error(
                    f"❌ {self.uid_prefix} Failed to connect to Core network: {core_node_url}"
                )
                return

            # Initialize Core client
            self.core_client = ModernTensorCoreClient(
                w3=w3,
                contract_address=contract_address,
                account=self.core.account if hasattr(self.core, "account") else None,
            )

            logger.info(
                f"✅ {self.uid_prefix} Core blockchain client initialized successfully"
            )

        except Exception as e:
            logger.error(f"❌ {self.uid_prefix} Failed to initialize Core client: {e}")
            self.core_client = None

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
            # Use slot coordinator for consensus
            consensus_scores = (
                await self.core.slot_coordinator.coordinate_consensus_round(
                    slot, local_scores
                )
            )

            if consensus_scores:
                # Apply consensus scores to metagraph
                await self._apply_consensus_scores_to_metagraph(slot, consensus_scores)
                logger.info(
                    f"{self.uid_prefix} Synchronized metagraph update completed for slot {slot}"
                )
                return True
            else:
                logger.warning(
                    f"{self.uid_prefix} No consensus reached for slot {slot}"
                )
                return False

        except Exception as e:
            logger.error(
                f"{self.uid_prefix} Error in synchronized metagraph update: {e}"
            )
            return False

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
            # Use the broadcasting logic from the scoring module
            await broadcast_scores_logic(
                http_client=self.core.http_client,
                validators_info=self.core.validators_info,
                scores_to_broadcast=scores_to_broadcast,
                validator_uid=self.core.info.uid,
            )

        except Exception as e:
            logger.error(f"{self.uid_prefix} Error broadcasting scores: {e}")

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

        for validator_info in self.core.validators_info.values():
            if (
                hasattr(validator_info, "status")
                and validator_info.status == "active"
                and validator_info.api_endpoint
            ):
                active_validators.append(validator_info)

        return active_validators

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
                        if uid == miner_uid:
                            miner_address = (
                                miner_info.address
                            )  # Get actual address from MinerInfo object
                            break

                    if not miner_address:
                        logger.warning(
                            f"⚠️ {self.uid_prefix} Miner {miner_uid} address not found, skipping..."
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

                    # Scale score (0.0-1.0 -> 0-10000 for basis points)
                    trust_score_scaled = int(consensus_score * 10_000)
                    performance_scaled = int(consensus_score * 10_000)

                    # Ensure scores are within valid range
                    trust_score_scaled = max(0, min(10_000, trust_score_scaled))
                    performance_scaled = max(0, min(10_000, performance_scaled))

                    # Submit score update to Core blockchain
                    tx_hash = self.core_client.update_miner_scores(
                        miner_address=miner_address,
                        new_performance=performance_scaled,
                        new_trust_score=trust_score_scaled,
                    )

                    # Wait for transaction confirmation
                    receipt = self.core_client.wait_for_transaction(tx_hash)

                    if receipt["status"] == 1:
                        transaction_hashes.append(tx_hash)
                        logger.info(
                            f"✅ {self.uid_prefix} Submitted score for {miner_uid}: {consensus_score:.4f} → TX: {tx_hash}"
                        )
                    else:
                        logger.error(
                            f"❌ {self.uid_prefix} Transaction failed for {miner_uid}: {tx_hash}"
                        )

                except Exception as e:
                    logger.error(
                        f"❌ {self.uid_prefix} Failed to submit score for {miner_uid}: {e}"
                    )
                    continue

            logger.info(
                f"🎯 {self.uid_prefix} Core blockchain submission complete: {len(transaction_hashes)}/{len(final_scores)} transactions submitted"
            )

        except Exception as e:
            logger.error(f"❌ {self.uid_prefix} Core blockchain submission error: {e}")
            import traceback

            logger.error(f"{self.uid_prefix} Traceback: {traceback.format_exc()}")

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

    # === Utility Methods ===

    def get_consensus_statistics(self) -> Dict[str, Any]:
        """Get statistics about consensus state."""
        return {
            "cycle_scores_count": sum(
                len(scores) for scores in self.core.cycle_scores.values()
            ),
            "slot_scores_count": sum(
                len(scores) for scores in self.core.slot_scores.values()
            ),
            "received_scores_cycles": len(self.core.received_validator_scores),
            "consensus_cache_size": len(self.core.consensus_results_cache),
        }
