#!/usr/bin/env python3
"""
ValidatorNode Tasks Module

This module handles all task-related functionality for ValidatorNode including:
- Task creation and assignment
- Miner selection algorithms
- Task tracking and management
- Result collection and processing

The tasks module manages the complete lifecycle of tasks from creation to result collection.
"""

import asyncio
import logging
import random
import time
from typing import Dict, List, Any, Optional

import httpx

from ..core.datatypes import MinerInfo, TaskAssignment, MinerResult, ValidatorInfo
from ..metagraph.metagraph_datum import STATUS_ACTIVE
from ..network.server import TaskModel
from .selection import select_miners_logic
from .slot_coordinator import SlotPhase

logger = logging.getLogger(__name__)

# Constants
HTTP_TIMEOUT = 20.0  # Increased from 10.0s to 20.0s for better task assignment
MAX_TASK_RETRIES = 3
DEFAULT_TASK_TIMEOUT = 60.0


class ValidatorNodeTasks:
    """
    Task management functionality for ValidatorNode.

    This class handles:
    - Task creation and data generation
    - Miner selection based on various algorithms
    - Task assignment and distribution
    - Result collection and tracking
    """

    def __init__(self, core_node):
        """
        Initialize task management with reference to core node.

        Args:
            core_node: Reference to the ValidatorNodeCore instance
        """
        self.core = core_node
        self.uid_prefix = core_node.uid_prefix

    # === Miner Selection Methods ===

    def select_miners(self) -> List[MinerInfo]:
        """Select miners for task assignment based on configured logic."""
        logger.info(
            f"{self.uid_prefix} Selecting miners for cycle {self.core.current_cycle}"
        )

        num_to_select = self.core.settings.CONSENSUS_NUM_MINERS_TO_SELECT
        beta = self.core.settings.CONSENSUS_PARAM_BETA
        max_time_bonus = self.core.settings.CONSENSUS_PARAM_MAX_TIME_BONUS

        return select_miners_logic(
            miners_info=self.core.miners_info,
            current_cycle=self.core.current_cycle,
            num_to_select=num_to_select,
            beta=beta,
            max_time_bonus=max_time_bonus,
        )

    def select_available_miners_for_batch(self, num_to_select: int) -> List[MinerInfo]:
        """
        Select a batch of available (not busy) and active miners.

        Args:
            num_to_select: Desired number of miners for the batch

        Returns:
            List of selected available miners, up to num_to_select
        """
        # Filter active miners
        active_miners_all = [
            m
            for m in self.core.miners_info.values()
            if getattr(m, "status", STATUS_ACTIVE) == STATUS_ACTIVE
        ]

        if not active_miners_all:
            logger.debug(f"{self.uid_prefix} No active miners found")
            return []

        # Filter available (not busy) miners
        available_miners = [
            m for m in active_miners_all if m.uid not in self.core.miner_is_busy
        ]

        if not available_miners:
            logger.debug(f"{self.uid_prefix} No available miners found at the moment")
            return []

        logger.debug(
            f"{self.uid_prefix} {len(available_miners)} available miners to choose from"
        )

        # Prepare input for selection logic
        available_miners_dict = {m.uid: m for m in available_miners}

        # Get selection parameters
        beta = self.core.settings.CONSENSUS_PARAM_BETA
        max_time_bonus = self.core.settings.CONSENSUS_PARAM_MAX_TIME_BONUS

        # Select miners
        actual_num_to_select = min(num_to_select, len(available_miners))
        if actual_num_to_select <= 0:
            return []

        selected_miners = select_miners_logic(
            miners_info=available_miners_dict,
            current_cycle=self.core.current_cycle,
            num_to_select=actual_num_to_select,
            beta=beta,
            max_time_bonus=max_time_bonus,
        )

        logger.debug(
            f"{self.uid_prefix} Selected {len(selected_miners)} miners for batch: "
            f"{[m.uid for m in selected_miners]}"
        )

        return selected_miners

    def cardano_select_miners(self, slot: int) -> List[MinerInfo]:
        """Select miners for a specific slot using Cardano-style selection."""
        logger.info(f"{self.uid_prefix} Selecting miners for slot {slot}")

        # Filter active miners from blockchain
        active_miners = [
            miner
            for miner in self.core.miners_info.values()
            if getattr(miner, "status", STATUS_ACTIVE) == STATUS_ACTIVE
        ]

        # If no miners from blockchain, use mock miners for testing
        if not active_miners:
            logger.info(f"{self.uid_prefix} Using mock miners for testing")
            active_miners = self._create_mock_miners()

        if not active_miners:
            logger.warning(
                f"{self.uid_prefix} No active miners available for slot {slot}"
            )
            return []

        # Select based on slot and current settings
        num_to_select = min(
            self.core.settings.CONSENSUS_NUM_MINERS_TO_SELECT, len(active_miners)
        )

        # Use deterministic selection based on slot number
        random.seed(slot)
        selected_miners = random.sample(active_miners, num_to_select)
        random.seed()  # Reset seed

        logger.info(
            f"{self.uid_prefix} Selected {len(selected_miners)} miners for slot {slot}: "
            f"{[m.uid[:8] for m in selected_miners]}"
        )

        return selected_miners

    def _create_mock_miners(self) -> List[MinerInfo]:
        """Create mock miners for testing when no real miners are available."""
        mock_miners = []

        # Create 2 mock miners for testing
        for i in range(1, 3):
            miner_info = MinerInfo(
                uid=f"subnet1_miner_{i}",
                address=f"0x{'0' * 40}",  # Mock address
                api_endpoint=f"http://localhost:800{i+1}",
                trust_score=0.8,
                stake=1000.0,
                weight=1.0,
                status=STATUS_ACTIVE,
                performance_history=[],
                last_update_time=time.time(),
            )
            mock_miners.append(miner_info)

            # Add to core miners_info for consistency
            self.core.miners_info[miner_info.uid] = miner_info

        logger.info(
            f"{self.uid_prefix} Created {len(mock_miners)} mock miners for testing"
        )
        return mock_miners

    # === Task Creation Methods ===

    def create_task_data(self, miner_uid: str) -> Any:
        """
        Create specific task data for a miner.

        This is an abstract method that should be overridden by subnet-specific validators.

        Args:
            miner_uid: The UID of the miner receiving the task

        Returns:
            The task data (should be JSON-serializable)

        Raises:
            NotImplementedError: If not overridden by the subclass
        """
        logger.error(
            f"{self.uid_prefix} create_task_data must be implemented by subnet validator for miner {miner_uid}"
        )
        raise NotImplementedError("Subnet Validator must implement task creation logic")

    def cardano_create_task(self, slot: int, miner_uid: str) -> Dict[str, Any]:
        """
        Create task data for Cardano-style slot-based consensus.

        Args:
            slot: Current slot number
            miner_uid: UID of the miner receiving the task

        Returns:
            Dictionary containing task data
        """
        return {
            "description": f"Slot-based consensus task for slot {slot}",  # Required field for TaskModel
            "task_data": {
                "task_type": "slot_based_task",
                "slot": slot,
                "miner_uid": miner_uid,
                "validator_uid": self.core.info.uid,
                "timestamp": time.time(),
                "requirements": {
                    "format": "json",
                    "timeout": DEFAULT_TASK_TIMEOUT,
                },
            },
            "priority": 1,  # Default priority
            "deadline": str(
                int(time.time() + DEFAULT_TASK_TIMEOUT)
            ),  # Optional deadline
            "validator_endpoint": self.core.info.api_endpoint
            or f"http://localhost:{getattr(self.core, 'api_port', 8001)}",  # Use info.api_endpoint or dynamic port
        }

    def create_slot_task_data(self, slot: int, miner_uid: str) -> Dict[str, Any]:
        """
        Create task data for a specific slot.

        Args:
            slot: Slot number
            miner_uid: UID of the miner receiving the task

        Returns:
            Dictionary containing slot-specific task data
        """
        return {
            "slot": slot,
            "miner_uid": miner_uid,
            "validator_uid": self.core.info.uid,
            "task_id": f"slot_{slot}_{miner_uid}_{int(time.time())}",
            "created_at": time.time(),
            "expected_completion_time": time.time() + DEFAULT_TASK_TIMEOUT,
        }

    # === Task Assignment Methods ===

    async def send_task_batch(
        self, miners_for_batch: List[MinerInfo], batch_num: int
    ) -> Dict[str, TaskAssignment]:
        """
        Send a batch of tasks to specified miners.

        Args:
            miners_for_batch: List of miners to send tasks to
            batch_num: Batch number for tracking

        Returns:
            Dictionary of successfully sent task assignments
        """
        if not miners_for_batch:
            return {}

        logger.info(
            f"{self.uid_prefix} Preparing to send task batch {batch_num} to {len(miners_for_batch)} miners"
        )

        tasks_sent_successfully: Dict[str, TaskAssignment] = {}
        send_coroutines = []

        for miner_info in miners_for_batch:
            miner_uid = miner_info.uid

            # Mark miner as busy
            self.core.miner_is_busy.add(miner_uid)

            # Create unique task ID
            task_id = f"task_{self.core.current_cycle}_{self.core.info.uid}_{miner_uid}_b{batch_num}_{random.randint(1000,9999)}"

            try:
                # Create task data
                task_data = self.create_task_data(miner_uid)
                if task_data is None:
                    raise ValueError("create_task_data returned None")

                task = TaskModel(task_id=task_id, **task_data)

                # Create assignment
                assignment = TaskAssignment(
                    task_id=task_id,
                    task_data=task_data,
                    miner_uid=miner_uid,
                    validator_uid=self.core.info.uid,
                    timestamp_sent=time.time(),
                    expected_result_format={},
                )

                # Track the assignment
                self.core.tasks_sent[task_id] = assignment
                tasks_sent_successfully[task_id] = assignment

                # Prepare async send
                send_coroutines.append(
                    self._send_task_via_network_async(miner_info.api_endpoint, task)
                )

            except Exception as e:
                logger.error(
                    f"{self.uid_prefix} Failed to create task for miner {miner_uid}: {e}"
                )
                self.core.miner_is_busy.discard(miner_uid)
                continue

        # Send tasks concurrently
        if send_coroutines:
            logger.info(
                f"{self.uid_prefix} Sending batch of {len(send_coroutines)} tasks concurrently"
            )

            results = await asyncio.gather(*send_coroutines, return_exceptions=True)

            # Process results
            success_count = 0
            failed_assignments = []

            for i, (result, assignment) in enumerate(
                zip(results, tasks_sent_successfully.values())
            ):
                if isinstance(result, bool) and result:
                    success_count += 1
                else:
                    logger.warning(
                        f"{self.uid_prefix} Failed to send task {assignment.task_id} to {assignment.miner_uid}: {result}"
                    )
                    self.core.miner_is_busy.discard(assignment.miner_uid)
                    failed_assignments.append(assignment.task_id)

            # Remove failed assignments
            for task_id in failed_assignments:
                if task_id in self.core.tasks_sent:
                    del self.core.tasks_sent[task_id]
                if task_id in tasks_sent_successfully:
                    del tasks_sent_successfully[task_id]

            logger.info(
                f"{self.uid_prefix} Task batch {batch_num} sent: {success_count}/{len(send_coroutines)} successful"
            )

        return tasks_sent_successfully

    async def cardano_send_tasks(self, slot: int, miners: List[MinerInfo]):
        """
        Send tasks to miners for Cardano-style slot-based consensus.

        Args:
            slot: Current slot number
            miners: List of miners to send tasks to
        """
        logger.info(
            f"{self.uid_prefix} Sending tasks for slot {slot} to {len(miners)} miners"
        )

        send_coroutines = []

        for miner in miners:
            # Create task
            task_data = self.cardano_create_task(slot, miner.uid)
            task_id = f"slot_{slot}_{miner.uid}_{int(time.time())}"

            # Create assignment
            assignment = TaskAssignment(
                task_id=task_id,
                task_data=task_data,
                miner_uid=miner.uid,
                validator_uid=self.core.info.uid,
                timestamp_sent=time.time(),
                expected_result_format={},
            )

            # Track assignment
            self.core.tasks_sent[task_id] = assignment

            # Mark miner as busy
            self.core.miner_is_busy.add(miner.uid)

            # Prepare task model
            task = TaskModel(task_id=task_id, **task_data)

            # Add to send queue
            send_coroutines.append(
                self._cardano_send_single_task(task_id, assignment, miner, task)
            )

        # Send all tasks concurrently
        if send_coroutines:
            results = await asyncio.gather(*send_coroutines, return_exceptions=True)

            success_count = sum(
                1 for result in results if isinstance(result, bool) and result
            )
            logger.info(
                f"{self.uid_prefix} Slot {slot} tasks sent: {success_count}/{len(send_coroutines)} successful"
            )

    async def assign_tasks_for_slot(self, slot: int, miners: List[MinerInfo]):
        """
        Assign tasks for a specific slot.

        Args:
            slot: Slot number
            miners: List of miners to assign tasks to
        """
        logger.info(
            f"{self.uid_prefix} Assigning tasks for slot {slot} to {len(miners)} miners"
        )

        for miner in miners:
            try:
                # Create task data
                task_data = self.create_slot_task_data(slot, miner.uid)
                task_id = task_data["task_id"]

                # Create assignment
                assignment = TaskAssignment(
                    task_id=task_id,
                    task_data=task_data,
                    miner_uid=miner.uid,
                    validator_uid=self.core.info.uid,
                    timestamp_sent=time.time(),
                    expected_result_format={},
                )

                # Track assignment
                self.core.tasks_sent[task_id] = assignment

                # Mark miner as busy
                self.core.miner_is_busy.add(miner.uid)

                logger.debug(
                    f"{self.uid_prefix} Assigned task {task_id} to miner {miner.uid}"
                )

            except Exception as e:
                logger.error(
                    f"{self.uid_prefix} Failed to assign task for slot {slot} to miner {miner.uid}: {e}"
                )

    # === Task Sending Methods ===

    async def _send_task_via_network_async(
        self, miner_endpoint: str, task: TaskModel
    ) -> bool:
        """
        Send task to miner via network asynchronously.

        Args:
            miner_endpoint: Miner's API endpoint
            task: Task to send

        Returns:
            True if task was sent successfully, False otherwise
        """
        try:
            return await self._send_task_implementation(miner_endpoint, task)
        except Exception as e:
            logger.error(
                f"{self.uid_prefix} Error sending task to {miner_endpoint}: {e}"
            )
            return False

    async def _send_task_implementation(
        self, miner_endpoint: str, task: TaskModel
    ) -> bool:
        """
        Implementation of task sending logic.

        Args:
            miner_endpoint: Miner's API endpoint
            task: Task to send

        Returns:
            True if successful, False otherwise
        """
        if not miner_endpoint:
            logger.warning(
                f"{self.uid_prefix} No endpoint provided for task {task.task_id}"
            )
            return False

        try:
            url = f"{miner_endpoint.rstrip('/')}/receive-task"

            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                response = await client.post(
                    url, json=task.dict(), headers={"Content-Type": "application/json"}
                )

                if response.status_code == 200:
                    logger.debug(
                        f"{self.uid_prefix} Task {task.task_id} sent successfully to {miner_endpoint}"
                    )
                    return True
                else:
                    logger.warning(
                        f"{self.uid_prefix} Task {task.task_id} failed: HTTP {response.status_code}"
                    )
                    return False

        except Exception as e:
            logger.error(
                f"{self.uid_prefix} Network error sending task {task.task_id} to {miner_endpoint}: {e}"
            )
            return False

    async def _cardano_send_single_task(
        self,
        task_id: str,
        assignment: TaskAssignment,
        miner: MinerInfo,
        task: TaskModel,
    ) -> bool:
        """
        Send a single task for Cardano-style consensus.

        Args:
            task_id: Task identifier
            assignment: Task assignment object
            miner: Miner information
            task: Task model to send

        Returns:
            True if successful, False otherwise
        """
        success = await self._send_task_via_network_async(miner.api_endpoint, task)

        if not success:
            # Clean up on failure
            self.core.miner_is_busy.discard(miner.uid)
            if task_id in self.core.tasks_sent:
                del self.core.tasks_sent[task_id]

        return success

    # === Result Collection Methods ===

    async def add_miner_result(self, result: MinerResult) -> bool:
        """
        Add a miner result to the results buffer and score it immediately.

        Args:
            result: Miner result to add

        Returns:
            True if result was added successfully, False otherwise
        """
        try:
            async with self.core.results_buffer_lock:
                # Validate result
                if not result.task_id or not result.miner_uid:
                    logger.warning(
                        f"{self.uid_prefix} Invalid result: missing task_id or miner_uid"
                    )
                    return False

                # Check if task exists
                if result.task_id not in self.core.tasks_sent:
                    logger.warning(
                        f"{self.uid_prefix} Received result for unknown task {result.task_id}"
                    )
                    return False

                # Add to buffer
                self.core.results_buffer[result.task_id] = result

                # Mark miner as not busy
                self.core.miner_is_busy.discard(result.miner_uid)

                logger.info(
                    f"✅ {self.uid_prefix} Added result for task {result.task_id} from miner {result.miner_uid}"
                )

                # Score the result immediately
                await self._score_result_immediately(result)

                return True

        except Exception as e:
            logger.error(f"{self.uid_prefix} Error adding miner result: {e}")
            return False

    async def _score_result_immediately(self, result: MinerResult):
        """
        Score a single result immediately upon receipt.

        Args:
            result: The result to score
        """
        try:
            if result.task_id not in self.core.tasks_sent:
                logger.warning(
                    f"{self.uid_prefix} Cannot score result for unknown task {result.task_id}"
                )
                return

            assignment = self.core.tasks_sent[result.task_id]

            # CRITICAL FIX: Use advanced scoring with formulas for immediate scoring too
            from .scoring import calculate_advanced_score
            import time

            current_time_step = int(time.time())

            # Apply formulas-based advanced scoring
            score_value, scoring_metadata = calculate_advanced_score(
                task_data=assignment.task_data,
                result_data=result.result_data,
                miner_uid=result.miner_uid,
                validator_uid=self.core.info.uid,
                validator_instance=getattr(self.core, "validator_instance", None),
                current_time_step=current_time_step,
            )

            logger.info(
                f"🎯 {self.uid_prefix} IMMEDIATE FORMULAS scoring: {score_value:.3f} for task {result.task_id} from miner {result.miner_uid}"
            )

            # Log advanced scoring metadata
            if scoring_metadata.get("performance_improvement", 0) != 0:
                improvement = scoring_metadata["performance_improvement"]
                logger.info(
                    f"🚀 {self.uid_prefix} IMMEDIATE Performance improved by {improvement:+.3f} for {result.miner_uid}"
                )

            # Log trust score evolution
            if "trust_score_new" in scoring_metadata:
                trust_old = scoring_metadata.get("trust_score_old", 0.5)
                trust_new = scoring_metadata["trust_score_new"]
                trust_change = trust_new - trust_old
                logger.info(
                    f"📈 {self.uid_prefix} IMMEDIATE Trust score for {result.miner_uid}: {trust_old:.3f} → {trust_new:.3f} ({trust_change:+.3f})"
                )

            # Create validator score
            from ..core.datatypes import ValidatorScore

            validator_score = ValidatorScore(
                task_id=result.task_id,
                miner_uid=result.miner_uid,
                validator_uid=self.core.info.uid,
                score=score_value,
                timestamp=time.time(),
                cycle=self.core.current_cycle,
            )

            # Store the score in multiple places for different consensus modes
            self.core.cycle_scores[result.task_id].append(validator_score)

            # Also store in slot scores for current slot
            current_slot = self.core.get_current_blockchain_slot()
            if current_slot not in self.core.slot_scores:
                self.core.slot_scores[current_slot] = []
            self.core.slot_scores[current_slot].append(validator_score)

            logger.info(
                f"✨ {self.uid_prefix} IMMEDIATE scoring complete: {score_value:.3f} for task {result.task_id}"
            )

        except Exception as e:
            logger.error(f"{self.uid_prefix} Error scoring result immediately: {e}")
            # Don't fail the result addition if scoring fails
            pass

    async def receive_results(self, timeout: Optional[float] = None):
        """
        Wait for and receive results from miners.

        Args:
            timeout: Maximum time to wait for results
        """
        if timeout is None:
            timeout = DEFAULT_TASK_TIMEOUT

        logger.info(f"{self.uid_prefix} Waiting for results (timeout: {timeout}s)")

        start_time = time.time()

        while time.time() - start_time < timeout:
            async with self.core.results_buffer_lock:
                pending_tasks = len(self.core.tasks_sent) - len(
                    self.core.results_buffer
                )

                if pending_tasks <= 0:
                    logger.info(f"{self.uid_prefix} All results received")
                    break

                logger.debug(
                    f"{self.uid_prefix} Still waiting for {pending_tasks} results"
                )

            await asyncio.sleep(1)

        # Log final status
        async with self.core.results_buffer_lock:
            received = len(self.core.results_buffer)
            total = len(self.core.tasks_sent)
            logger.info(
                f"{self.uid_prefix} Result collection completed: {received}/{total} received"
            )

    # === Continuous Task Assignment Methods ===

    async def _continuous_task_assignment(
        self,
        miners: List[MinerInfo],
        batch_num: int,
        slot: int,
        batch_timeout: float,
        elapsed_time: float,
        assignment_time_limit: float,
    ) -> List[Any]:
        """
        Continuously assign tasks to miners within time window.

        This implements the continuous assignment pattern from moderntensor_aptos
        where multiple task rounds are sent to same miners during assignment phase.
        """
        batch_scores = []
        round_num = 0
        remaining_time = assignment_time_limit - elapsed_time

        logger.info(
            f"{self.uid_prefix} Starting continuous task assignment for batch {batch_num}: "
            f"{remaining_time:.1f}s remaining"
        )

        while remaining_time > batch_timeout:
            round_num += 1
            round_start = time.time()

            logger.info(
                f"{self.uid_prefix} Task round {round_num} for batch {batch_num} "
                f"(remaining time: {remaining_time:.1f}s)"
            )

            try:
                # Send tasks to miners for this round
                task_assignments = await self.send_task_batch(
                    miners, f"{batch_num}_r{round_num}"
                )
                if not task_assignments:
                    logger.warning(
                        f"{self.uid_prefix} No tasks sent for round {round_num}"
                    )
                    break

                # Wait for results with dynamic timeout
                round_timeout = min(batch_timeout, remaining_time * 0.8)
                await self.receive_results(timeout=round_timeout)

                # Score results immediately for this round
                round_scores = await self._score_current_batch(task_assignments)
                batch_scores.extend(round_scores)

                # Update remaining time
                round_duration = time.time() - round_start
                remaining_time -= round_duration

                logger.info(
                    f"{self.uid_prefix} Round {round_num} completed: "
                    f"{len(round_scores)} scores, {remaining_time:.1f}s remaining"
                )

                # Small delay between rounds to avoid overwhelming miners
                if remaining_time > batch_timeout:
                    await asyncio.sleep(2)
                    remaining_time -= 2

            except Exception as e:
                logger.error(f"{self.uid_prefix} Error in task round {round_num}: {e}")
                break

        logger.info(
            f"{self.uid_prefix} Continuous assignment for batch {batch_num} completed: "
            f"{round_num} rounds, {len(batch_scores)} total scores"
        )

        return batch_scores

    async def _aggregate_and_average_scores(
        self, all_scores: List[Any], slot: int
    ) -> Dict[str, Dict[str, float]]:
        """
        Aggregate and average scores per miner-validator pair.

        Returns:
            Dict with structure: {miner_uid: {validator_uid: average_score}}
        """
        logger.info(
            f"{self.uid_prefix} Aggregating {len(all_scores)} scores for slot {slot}"
        )

        # Group scores by miner-validator pairs
        miner_validator_scores = {}

        for score in all_scores:
            if (
                hasattr(score, "miner_uid")
                and hasattr(score, "validator_uid")
                and hasattr(score, "score")
            ):
                miner_uid = score.miner_uid
                validator_uid = score.validator_uid
                score_value = score.score

                if miner_uid not in miner_validator_scores:
                    miner_validator_scores[miner_uid] = {}

                if validator_uid not in miner_validator_scores[miner_uid]:
                    miner_validator_scores[miner_uid][validator_uid] = []

                miner_validator_scores[miner_uid][validator_uid].append(score_value)

        # Calculate averages
        averaged_scores = {}
        for miner_uid, validator_scores in miner_validator_scores.items():
            averaged_scores[miner_uid] = {}
            for validator_uid, scores_list in validator_scores.items():
                if scores_list:
                    avg_score = sum(scores_list) / len(scores_list)
                    averaged_scores[miner_uid][validator_uid] = avg_score

                    logger.debug(
                        f"{self.uid_prefix} Miner {miner_uid[:8]}... -> Validator {validator_uid[:8]}...: "
                        f"{len(scores_list)} scores, average: {avg_score:.4f}"
                    )

        logger.info(
            f"{self.uid_prefix} Aggregation complete: {len(averaged_scores)} miners, "
            f"total pairs: {sum(len(v) for v in averaged_scores.values())}"
        )

        return averaged_scores

    async def _score_current_batch(self, task_assignments: Dict[str, Any]) -> List[Any]:
        """
        Score current batch of task assignments immediately.

        Args:
            task_assignments: Dictionary of task assignments for this batch

        Returns:
            List of ValidatorScore objects
        """
        batch_scores = []

        try:
            # Process each result in current buffer
            async with self.core.results_buffer_lock:
                for task_id, result in self.core.results_buffer.items():
                    if task_id in task_assignments:
                        # Score this result immediately
                        score_value = self._calculate_score(result)

                        # Create ValidatorScore object
                        from ..core.datatypes import ValidatorScore

                        validator_score = ValidatorScore(
                            task_id=task_id,
                            miner_uid=result.miner_uid,
                            validator_uid=self.core.info.uid,
                            score=score_value,
                            timestamp=time.time(),
                        )

                        batch_scores.append(validator_score)

                        logger.debug(
                            f"{self.uid_prefix} Scored task {task_id}: {score_value:.4f}"
                        )

        except Exception as e:
            logger.error(f"{self.uid_prefix} Error scoring batch: {e}")

        return batch_scores

    def _calculate_score(self, result: Any) -> float:
        """
        Calculate score for a miner result.

        This is a simplified scoring function that should be overridden
        by subnet-specific validators.
        """
        try:
            # Simple scoring based on result data presence and validity
            if not hasattr(result, "result_data") or result.result_data is None:
                return 0.0

            # Basic validation scoring
            if isinstance(result.result_data, dict):
                return 0.8 + (len(result.result_data) * 0.02)  # Score between 0.8-1.0
            elif isinstance(result.result_data, str) and len(result.result_data) > 0:
                return 0.7
            else:
                return 0.5

        except Exception as e:
            logger.warning(f"{self.uid_prefix} Error calculating score: {e}")
            return 0.0

    # === Task Monitoring Methods ===

    async def monitor_task_execution(self, slot: int):
        """Monitor task execution for the current slot and handle timeouts."""
        try:
            logger.debug(f"{self.uid_prefix} Monitoring task execution for slot {slot}")

            # Check for timeout tasks that need 0 scores
            current_time = time.time()
            timeout_tasks = []

            for task_id, assignment in self.core.tasks_sent.items():
                # Check if task is older than timeout threshold (60 seconds)
                if hasattr(assignment, "timestamp_sent"):
                    task_age = current_time - assignment.timestamp_sent
                    if (
                        task_age > DEFAULT_TASK_TIMEOUT
                        and task_id not in self.core.results_buffer
                    ):
                        timeout_tasks.append((task_id, assignment))
                        logger.warning(
                            f"{self.uid_prefix} Task {task_id} timeout detected: {task_age:.1f}s > {DEFAULT_TASK_TIMEOUT}s, miner: {assignment.miner_uid}"
                        )

            # Process timeout tasks by creating empty results for scoring
            if timeout_tasks:
                logger.info(
                    f"{self.uid_prefix} Processing {len(timeout_tasks)} timeout tasks for scoring"
                )

                for task_id, assignment in timeout_tasks:
                    # Create timeout result entry to trigger 0 score in scoring
                    async with self.core.results_buffer_lock:
                        if task_id not in self.core.results_buffer:
                            # Create timeout MinerResult object
                            from ..core.datatypes import MinerResult

                            timeout_result = MinerResult(
                                task_id=task_id,
                                miner_uid=assignment.miner_uid,
                                result_data={"error": "timeout", "timeout": True},
                                timestamp_received=current_time,
                            )
                            self.core.results_buffer[task_id] = timeout_result
                            logger.debug(
                                f"{self.uid_prefix} Added timeout result for task {task_id}"
                            )

            # Check if there are active tasks for this slot
            active_tasks = []
            if hasattr(self.core, "active_task_assignments"):
                for task_id, assignment in self.core.active_task_assignments.items():
                    if assignment.get("slot") == slot:
                        active_tasks.append(task_id)

            if active_tasks:
                logger.debug(
                    f"{self.uid_prefix} Found {len(active_tasks)} active tasks for slot {slot}"
                )
            else:
                logger.debug(f"{self.uid_prefix} No active tasks for slot {slot}")

        except Exception as e:
            logger.warning(f"{self.uid_prefix} Error monitoring task execution: {e}")

    # === Utility Methods ===

    def cleanup_completed_tasks(self):
        """Clean up completed tasks and results."""
        try:
            # Remove completed tasks from tracking
            completed_tasks = list(self.core.results_buffer.keys())

            for task_id in completed_tasks:
                if task_id in self.core.tasks_sent:
                    assignment = self.core.tasks_sent[task_id]
                    self.core.miner_is_busy.discard(assignment.miner_uid)
                    del self.core.tasks_sent[task_id]

            # Clear results buffer
            self.core.results_buffer.clear()

            logger.debug(
                f"{self.uid_prefix} Cleaned up {len(completed_tasks)} completed tasks"
            )

        except Exception as e:
            logger.error(f"{self.uid_prefix} Error cleaning up tasks: {e}")

    def get_task_statistics(self) -> Dict[str, Any]:
        """Get statistics about current task status."""
        return {
            "tasks_sent": len(self.core.tasks_sent),
            "results_received": len(self.core.results_buffer),
            "miners_busy": len(self.core.miner_is_busy),
            "pending_tasks": len(self.core.tasks_sent) - len(self.core.results_buffer),
        }

    async def cardano_send_minibatches(self, slot: int, miners: List[MinerInfo]):
        """
        Send tasks to miners using minibatch approach within slot timing.

        This method combines:
        - Slot-based consensus timing
        - Minibatch processing (send batch → wait results → score → next batch)

        Args:
            slot: Current slot number
            miners: List of miners to send tasks to
        """
        logger.info(
            f"{self.uid_prefix} Starting minibatch task assignment for slot {slot} with {len(miners)} miners"
        )

        if not miners:
            logger.warning(f"{self.uid_prefix} No miners provided for slot {slot}")
            return

        # Get minibatch configuration
        batch_size = getattr(
            self.core.settings, "CONSENSUS_MINIBATCH_SIZE", 2
        )  # Default 2 miners per batch
        batch_timeout = getattr(
            self.core.settings, "CONSENSUS_BATCH_TIMEOUT", 45.0
        )  # 45s per batch - Increased from 30s for better task completion

        # Calculate available time for task assignment phase
        slot_config = self.core.slot_config
        assignment_time_limit = (
            slot_config.task_assignment_minutes * 60
        )  # Convert to seconds

        # Split miners into batches
        miner_batches = [
            miners[i : i + batch_size] for i in range(0, len(miners), batch_size)
        ]
        logger.info(
            f"{self.uid_prefix} Created {len(miner_batches)} minibatches of size {batch_size}"
        )

        total_scores = []
        batch_start_time = time.time()

        for batch_num, batch_miners in enumerate(miner_batches):
            # Check if we have enough time for this batch
            elapsed_time = time.time() - batch_start_time
            remaining_time = assignment_time_limit - elapsed_time

            if remaining_time < batch_timeout:
                logger.warning(
                    f"{self.uid_prefix} Insufficient time for batch {batch_num + 1}, skipping remaining batches"
                )
                break

            logger.info(
                f"{self.uid_prefix} Processing minibatch {batch_num + 1}/{len(miner_batches)} with {len(batch_miners)} miners"
            )

            try:
                # Send tasks to this batch
                batch_results = await self._send_cardano_minibatch(
                    slot, batch_miners, batch_num + 1, batch_timeout
                )

                # Score results immediately
                if batch_results:
                    batch_scores = await self._score_minibatch_results(
                        slot, batch_results
                    )
                    total_scores.extend(batch_scores)

                    # CRITICAL FIX: Store scores in slot_scores for consensus to use
                    if slot not in self.core.slot_scores:
                        self.core.slot_scores[slot] = []
                    self.core.slot_scores[slot].extend(batch_scores)

                    # DEBUG: Log detailed score storage
                    logger.info(
                        f"💾 {self.uid_prefix} STORING {len(batch_scores)} scores in slot_scores[{slot}]"
                    )
                    for score in batch_scores:
                        logger.info(
                            f"💾 {self.uid_prefix} Stored: Miner {score.miner_uid} → {score.score:.4f} (Task: {score.task_id})"
                        )
                    logger.info(
                        f"💾 {self.uid_prefix} Total slot_scores[{slot}] now has {len(self.core.slot_scores[slot])} scores"
                    )

                    logger.info(
                        f"{self.uid_prefix} Batch {batch_num + 1} completed: {len(batch_scores)} scores generated and stored in slot_scores"
                    )

                # Clean up batch results
                self._cleanup_batch_results(batch_results)

            except Exception as e:
                logger.error(
                    f"{self.uid_prefix} Error processing batch {batch_num + 1}: {e}"
                )
                continue

        # Store all scores for the slot
        if total_scores:
            self.core.slot_scores[slot] = total_scores
            logger.info(
                f"✅ {self.uid_prefix} Minibatch assignment completed for slot {slot}: {len(total_scores)} total scores"
            )

            # Display detailed score information
            for i, score in enumerate(total_scores):
                logger.info(
                    f"📊 {self.uid_prefix} Score {i+1}: Miner {score.miner_uid} → {score.score:.3f} (Task: {score.task_id})"
                )

        else:
            logger.warning(f"{self.uid_prefix} No scores generated for slot {slot}")

    async def _send_cardano_minibatch(
        self, slot: int, miners: List[MinerInfo], batch_num: int, timeout: float
    ) -> Dict[str, MinerResult]:
        """
        Send tasks to a single minibatch and wait for results.

        Args:
            slot: Current slot number
            miners: Miners in this batch
            batch_num: Batch number for logging
            timeout: Timeout for receiving results

        Returns:
            Dictionary of received results {task_id: MinerResult}
        """
        logger.info(
            f"{self.uid_prefix} Sending batch {batch_num} tasks to {len(miners)} miners"
        )

        # Send tasks to all miners in batch concurrently
        send_coroutines = []
        batch_task_ids = []

        for miner in miners:
            # Create task
            task_data = self.cardano_create_task(slot, miner.uid)
            task_id = f"slot_{slot}_batch_{batch_num}_{miner.uid}_{int(time.time())}"

            # Create assignment
            assignment = TaskAssignment(
                task_id=task_id,
                task_data=task_data,
                miner_uid=miner.uid,
                validator_uid=self.core.info.uid,
                timestamp_sent=time.time(),
                expected_result_format={},
            )

            # Track assignment
            self.core.tasks_sent[task_id] = assignment
            batch_task_ids.append(task_id)

            # Mark miner as busy
            self.core.miner_is_busy.add(miner.uid)

            # Prepare task model
            task = TaskModel(task_id=task_id, **task_data)

            # Add to send queue
            send_coroutines.append(
                self._cardano_send_single_task(task_id, assignment, miner, task)
            )

        # Send all tasks in batch
        if send_coroutines:
            results = await asyncio.gather(*send_coroutines, return_exceptions=True)
            success_count = sum(
                1 for result in results if isinstance(result, bool) and result
            )
            logger.info(
                f"{self.uid_prefix} Batch {batch_num} sent: {success_count}/{len(send_coroutines)} successful"
            )

        # Wait for results with timeout
        return await self._wait_for_batch_results(batch_task_ids, timeout)

    async def _wait_for_batch_results(
        self, task_ids: List[str], timeout: float
    ) -> Dict[str, MinerResult]:
        """
        Wait for results from specific task IDs.

        Args:
            task_ids: List of task IDs to wait for
            timeout: Maximum wait time

        Returns:
            Dictionary of received results
        """
        logger.debug(
            f"{self.uid_prefix} Waiting for {len(task_ids)} batch results (timeout: {timeout}s)"
        )

        start_time = time.time()
        received_results = {}

        while time.time() - start_time < timeout and len(received_results) < len(
            task_ids
        ):
            # Check for new results
            async with self.core.results_buffer_lock:
                for task_id in task_ids:
                    if (
                        task_id in self.core.results_buffer
                        and task_id not in received_results
                    ):
                        received_results[task_id] = self.core.results_buffer[task_id]
                        logger.debug(
                            f"{self.uid_prefix} Received result for task {task_id}"
                        )

            if len(received_results) < len(task_ids):
                await asyncio.sleep(0.5)  # Short polling interval

        # Log results
        success_rate = len(received_results) / len(task_ids) * 100 if task_ids else 0
        logger.info(
            f"{self.uid_prefix} Batch results: {len(received_results)}/{len(task_ids)} received ({success_rate:.1f}%)"
        )

        return received_results

    async def _score_minibatch_results(
        self, slot: int, results: Dict[str, MinerResult]
    ) -> List:
        """
        Score results from a minibatch immediately.

        Args:
            slot: Current slot number
            results: Results to score

        Returns:
            List of scores generated
        """
        logger.debug(
            f"{self.uid_prefix} Scoring {len(results)} minibatch results for slot {slot}"
        )

        scores = []

        for task_id, result in results.items():
            if task_id in self.core.tasks_sent:
                assignment = self.core.tasks_sent[task_id]

                try:
                    # CRITICAL FIX: Use advanced scoring with formulas instead of direct scoring
                    from .scoring import calculate_advanced_score
                    import time

                    current_time_step = int(time.time())

                    # Apply formulas-based advanced scoring
                    score_value, scoring_metadata = calculate_advanced_score(
                        task_data=assignment.task_data,
                        result_data=result.result_data,
                        miner_uid=result.miner_uid,
                        validator_uid=self.core.info.uid,
                        validator_instance=getattr(
                            self.core, "validator_instance", None
                        ),
                        current_time_step=current_time_step,
                    )

                    logger.info(
                        f"🎯 {self.uid_prefix} Used FORMULAS scoring: {score_value:.3f} for {result.miner_uid}"
                    )

                    # Log advanced scoring metadata
                    if scoring_metadata.get("performance_improvement", 0) != 0:
                        improvement = scoring_metadata["performance_improvement"]
                        logger.info(
                            f"🚀 {self.uid_prefix} Performance improved by {improvement:+.3f} for {result.miner_uid}"
                        )

                    # Log trust score evolution
                    if "trust_score_new" in scoring_metadata:
                        trust_old = scoring_metadata.get("trust_score_old", 0.5)
                        trust_new = scoring_metadata["trust_score_new"]
                        trust_change = trust_new - trust_old
                        logger.info(
                            f"📈 {self.uid_prefix} Trust score for {result.miner_uid}: {trust_old:.3f} → {trust_new:.3f} ({trust_change:+.3f})"
                        )

                    # Create validator score
                    from ..core.datatypes import ValidatorScore

                    validator_score = ValidatorScore(
                        task_id=task_id,
                        miner_uid=result.miner_uid,
                        validator_uid=self.core.info.uid,
                        score=score_value,
                        timestamp=time.time(),
                        cycle=slot,  # Use slot as cycle for Cardano consensus
                    )

                    scores.append(validator_score)

                except Exception as e:
                    logger.error(
                        f"{self.uid_prefix} Error scoring result for task {task_id}: {e}"
                    )

        logger.debug(f"{self.uid_prefix} Generated {len(scores)} scores from minibatch")
        return scores

    def _cleanup_batch_results(self, results: Dict[str, MinerResult]):
        """
        Clean up completed batch results and mark miners as available.

        Args:
            results: Results to clean up
        """
        for task_id, result in results.items():
            # Mark miner as not busy
            self.core.miner_is_busy.discard(result.miner_uid)

            # Remove from tasks_sent
            if task_id in self.core.tasks_sent:
                del self.core.tasks_sent[task_id]

            # Remove from results_buffer
            if task_id in self.core.results_buffer:
                del self.core.results_buffer[task_id]

        logger.debug(f"{self.uid_prefix} Cleaned up {len(results)} batch results")
