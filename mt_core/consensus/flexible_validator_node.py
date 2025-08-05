#!/usr/bin/env python3
"""
Flexible Validator Node - Enhanced validator that can start anytime

This module provides enhanced validator functionality that allows:
- Starting validators at any time during a slot
- Dynamic phase detection and adaptation
- Event-driven consensus coordination
- Graceful handling of mid-slot joins
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any

from .flexible_slot_coordinator import (
    FlexibleSlotCoordinator,
    FlexibleSlotPhase,
    FlexibleSlotConfig,
)
from .validator_node_core import ValidatorNodeCore
from .validator_node_consensus import ValidatorNodeConsensus
from ..core.datatypes import ValidatorInfo

logger = logging.getLogger(__name__)


class FlexibleValidatorNode:
    """
    Enhanced validator node that can start anytime and adapt to ongoing consensus.

    Key features:
    - Flexible start time (can join mid-slot)
    - Dynamic phase detection
    - Event-driven synchronization
    - Graceful degradation when validators are offline
    """

    def __init__(
        self,
        validator_core: ValidatorNodeCore,
        flexible_config: Optional[FlexibleSlotConfig] = None,
        auto_adapt_timing: bool = True,
    ):
        """
        Initialize flexible validator node.

        Args:
            validator_core: Existing ValidatorNodeCore instance
            flexible_config: Optional flexible timing configuration
            auto_adapt_timing: Whether to automatically adapt timing based on network
        """
        self.core = validator_core
        self.auto_adapt_timing = auto_adapt_timing

        # Enhanced flexible coordinator
        self.flexible_coordinator = FlexibleSlotCoordinator(
            validator_uid=self.core.info.uid, slot_config=flexible_config
        )

        # State tracking
        self.current_mode = "flexible"  # vs "rigid"
        self.network_sync_status = "unknown"  # unknown, synced, behind, ahead
        self.last_successful_consensus = None
        self.consensus_participation_rate = 0.0

        # Performance metrics
        self.startup_time = time.time()
        self.phases_completed = 0
        self.successful_transitions = 0

        logger.info(f"🔄 FlexibleValidatorNode initialized for {self.core.info.uid}")
        logger.info(
            f"📊 Mode: {self.current_mode}, Auto-adapt: {self.auto_adapt_timing}"
        )

    async def start_flexible_consensus(self):
        """
        Start the flexible consensus process.

        This method allows the validator to start at any time and automatically
        detect the current network state to join ongoing consensus.
        """
        logger.info(f"🚀 Starting flexible consensus for {self.core.info.uid}")

        try:
            # Step 1: Detect current network state
            current_slot, current_phase, phase_info = (
                self.flexible_coordinator.get_current_slot_and_phase()
            )

            logger.info(f"📊 Network state detected:")
            logger.info(f"   - Current slot: {current_slot}")
            logger.info(f"   - Current phase: {current_phase.value}")
            logger.info(
                f"   - Joined mid-slot: {phase_info.get('joined_mid_slot', False)}"
            )

            # Step 2: Load metagraph if not already loaded
            if not self.core.miners_info:
                logger.info("📊 Loading metagraph data...")
                await self.core.load_metagraph_data()

            # Step 3: Adapt to current phase
            await self._adapt_to_current_phase(current_slot, current_phase, phase_info)

            # Step 4: Start the main consensus loop
            await self._run_flexible_consensus_loop(current_slot)

        except Exception as e:
            logger.error(f"❌ Error starting flexible consensus: {e}")
            raise

    async def _adapt_to_current_phase(
        self, slot: int, phase: FlexibleSlotPhase, phase_info: Dict
    ):
        """
        Adapt validator behavior to the current phase when starting mid-slot.
        """
        logger.info(f"🔄 Adapting to current phase: {phase.value}")

        if phase_info.get("joined_mid_slot", False):
            # We're joining an ongoing slot
            await self._handle_mid_slot_join(slot, phase, phase_info)
        else:
            # We're starting at a natural slot boundary
            await self._handle_slot_boundary_start(slot, phase)

        # Register our entry into this phase
        await self.flexible_coordinator.register_phase_entry_flexible(slot, phase)

    async def _handle_mid_slot_join(
        self, slot: int, phase: FlexibleSlotPhase, phase_info: Dict
    ):
        """Handle joining an ongoing slot mid-phase."""
        logger.info(f"🔄 Handling mid-slot join for slot {slot}, phase {phase.value}")

        active_validators = phase_info.get("active_validators", [])
        logger.info(
            f"📊 Found {len(active_validators)} active validators: {active_validators}"
        )

        if phase == FlexibleSlotPhase.TASK_ASSIGNMENT:
            # We can still participate in task assignment
            logger.info("✅ Joining task assignment phase")
            await self._start_task_assignment_phase(slot)

        elif phase == FlexibleSlotPhase.TASK_EXECUTION:
            # Tasks are being executed, we can prepare for consensus
            logger.info("⏳ Tasks in execution, preparing for consensus phase")
            await self._prepare_for_consensus_phase(slot)

        elif phase == FlexibleSlotPhase.CONSENSUS_SCORING:
            # Try to participate in ongoing consensus if not too late
            logger.info("🤝 Joining ongoing consensus phase")
            await self._join_ongoing_consensus(slot)

        elif phase == FlexibleSlotPhase.METAGRAPH_UPDATE:
            # Wait for next slot or participate in metagraph update
            logger.info("📊 Joining metagraph update phase")
            await self._join_metagraph_update(slot)

        # Mark that we joined mid-slot for analytics
        self.network_sync_status = "joined_mid_slot"

    async def _handle_slot_boundary_start(self, slot: int, phase: FlexibleSlotPhase):
        """Handle starting at a natural slot boundary."""
        logger.info(f"🎯 Starting at slot boundary: slot {slot}, phase {phase.value}")

        # This is the normal case - start from the beginning
        self.network_sync_status = "synced"

        if phase == FlexibleSlotPhase.TASK_ASSIGNMENT:
            await self._start_task_assignment_phase(slot)
        else:
            # Even at slot boundary, we might be in a later phase due to timing
            logger.info(f"⚠️ Slot boundary but in {phase.value} phase - adapting")
            await self._adapt_to_current_phase(slot, phase, {"joined_mid_slot": False})

    async def _run_flexible_consensus_loop(self, starting_slot: int):
        """
        Main flexible consensus loop that handles phase transitions gracefully.
        """
        current_slot = starting_slot
        logger.info(f"🔄 Starting flexible consensus loop from slot {current_slot}")

        while True:
            try:
                # Check current network state
                detected_slot, detected_phase, phase_info = (
                    self.flexible_coordinator.get_current_slot_and_phase()
                )

                # Handle slot transitions
                if detected_slot > current_slot:
                    logger.info(
                        f"🔄 Slot transition detected: {current_slot} → {detected_slot}"
                    )
                    current_slot = detected_slot

                    # Clean up old coordination files
                    self.flexible_coordinator.cleanup_old_coordination_files()

                # Execute phase-specific logic
                await self._execute_phase_logic(current_slot, detected_phase)

                # Check for phase transitions
                next_phase = self._get_next_phase(detected_phase)
                if next_phase:
                    transition_success = await self.flexible_coordinator.handle_flexible_phase_transition(
                        current_slot, detected_phase, next_phase
                    )

                    if transition_success:
                        self.successful_transitions += 1

                    # Update metrics
                    self.phases_completed += 1

                # Adaptive sleep based on phase and network activity
                sleep_time = self._calculate_adaptive_sleep(detected_phase)
                await asyncio.sleep(sleep_time)

            except Exception as e:
                logger.error(f"❌ Error in consensus loop: {e}")
                await asyncio.sleep(10)  # Error recovery delay

    async def _execute_phase_logic(self, slot: int, phase: FlexibleSlotPhase):
        """Execute the logic specific to each phase."""

        if phase == FlexibleSlotPhase.TASK_ASSIGNMENT:
            await self._handle_task_assignment(slot)

        elif phase == FlexibleSlotPhase.TASK_EXECUTION:
            await self._handle_task_execution(slot)

        elif phase == FlexibleSlotPhase.CONSENSUS_SCORING:
            await self._handle_consensus_scoring(slot)

        elif phase == FlexibleSlotPhase.METAGRAPH_UPDATE:
            await self._handle_metagraph_update(slot)

    async def _handle_task_assignment(self, slot: int):
        """Handle task assignment phase with flexible timing."""
        logger.debug(f"📋 Handling task assignment for slot {slot}")

        # Check if we should assign new tasks
        if not self._should_assign_tasks(slot):
            return

        # Use existing task assignment logic from core
        try:
            # Assign tasks to miners
            tasks_assigned = await self._assign_tasks_to_miners(slot)
            logger.info(f"✅ Assigned {tasks_assigned} tasks in slot {slot}")

        except Exception as e:
            logger.error(f"❌ Error in task assignment: {e}")

    async def _handle_task_execution(self, slot: int):
        """Handle task execution phase - wait for miner results."""
        logger.debug(f"⚡ Handling task execution for slot {slot}")

        # Wait for miner results with flexible timeout
        deadline = self.flexible_coordinator.get_deadline_for_phase(
            slot, FlexibleSlotPhase.TASK_EXECUTION
        )
        remaining_time = max(0, deadline - time.time())

        if remaining_time > 0:
            logger.info(
                f"⏳ Waiting for miner results ({remaining_time:.1f}s remaining)"
            )
            # Collect results as they come in
            await self._collect_miner_results(slot, timeout=remaining_time)

    async def _handle_consensus_scoring(self, slot: int):
        """Handle consensus scoring phase with P2P coordination."""
        logger.debug(f"🤝 Handling consensus scoring for slot {slot}")

        try:
            # Score the results we have
            if hasattr(self.core, "consensus"):
                await self.core.consensus.core_score_results(slot)

            # Participate in P2P consensus
            await self._participate_in_p2p_consensus(slot)

            # Wait for consensus deadline
            ready_validators = (
                await self.flexible_coordinator.wait_for_consensus_deadline(
                    slot, FlexibleSlotPhase.CONSENSUS_SCORING
                )
            )

            if len(ready_validators) >= 2:  # Majority threshold
                logger.info(
                    f"✅ Consensus reached with {len(ready_validators)} validators"
                )
                self.last_successful_consensus = time.time()
                self.consensus_participation_rate = len(ready_validators) / max(
                    len(ready_validators), 3
                )

        except Exception as e:
            logger.error(f"❌ Error in consensus scoring: {e}")

    async def _handle_metagraph_update(self, slot: int):
        """Handle metagraph update phase."""
        logger.debug(f"📊 Handling metagraph update for slot {slot}")

        try:
            # Wait for other validators to be ready for metagraph update
            ready_validators = (
                await self.flexible_coordinator.wait_for_consensus_deadline(
                    slot, FlexibleSlotPhase.METAGRAPH_UPDATE
                )
            )

            if len(ready_validators) >= 1:  # At least one other validator
                logger.info(
                    f"📊 Updating metagraph with {len(ready_validators)} validators"
                )
                await self.core.load_metagraph_data()

        except Exception as e:
            logger.error(f"❌ Error in metagraph update: {e}")

    def _get_next_phase(
        self, current_phase: FlexibleSlotPhase
    ) -> Optional[FlexibleSlotPhase]:
        """Get the next phase in the sequence."""
        phase_sequence = [
            FlexibleSlotPhase.TASK_ASSIGNMENT,  # includes execution
            FlexibleSlotPhase.CONSENSUS_SCORING,
            FlexibleSlotPhase.METAGRAPH_UPDATE,
        ]

        try:
            current_index = phase_sequence.index(current_phase)
            if current_index < len(phase_sequence) - 1:
                return phase_sequence[current_index + 1]
            else:
                return FlexibleSlotPhase.TASK_ASSIGNMENT  # Next slot
        except ValueError:
            return FlexibleSlotPhase.TASK_ASSIGNMENT

    def _calculate_adaptive_sleep(self, phase: FlexibleSlotPhase) -> float:
        """Calculate adaptive sleep time based on phase and network activity."""
        base_sleep = {
            FlexibleSlotPhase.TASK_ASSIGNMENT: 5.0,
            FlexibleSlotPhase.TASK_EXECUTION: 8.0,
            FlexibleSlotPhase.CONSENSUS_SCORING: 3.0,
            FlexibleSlotPhase.METAGRAPH_UPDATE: 2.0,
        }

        sleep_time = base_sleep.get(phase, 5.0)

        # Adjust based on network sync status
        if self.network_sync_status == "joined_mid_slot":
            sleep_time *= 0.7  # More frequent checks when catching up
        elif self.network_sync_status == "ahead":
            sleep_time *= 1.5  # Less frequent checks when ahead

        return sleep_time

    def _should_assign_tasks(self, slot: int) -> bool:
        """Determine if we should assign new tasks in this slot."""
        # Don't assign tasks if we joined very late in the assignment phase
        current_time = time.time()
        deadline = self.flexible_coordinator.get_deadline_for_phase(
            slot, FlexibleSlotPhase.TASK_ASSIGNMENT
        )

        time_remaining = deadline - current_time
        return time_remaining > 10  # At least 10 seconds remaining

    async def _assign_tasks_to_miners(self, slot: int) -> int:
        """Assign tasks to miners using existing core logic."""
        # Use existing task assignment logic from ValidatorNodeCore
        # This is a placeholder - integrate with actual task assignment
        return 0

    async def _collect_miner_results(self, slot: int, timeout: float):
        """Collect miner results during task execution phase."""
        # Use existing result collection logic
        # This is a placeholder - integrate with actual result collection
        pass

    async def _participate_in_p2p_consensus(self, slot: int):
        """Participate in P2P consensus scoring."""
        # Use existing P2P consensus logic
        # This is a placeholder - integrate with actual P2P consensus
        pass

    async def _start_task_assignment_phase(self, slot: int):
        """Initialize task assignment phase."""
        logger.info(f"📋 Starting task assignment phase for slot {slot}")
        await self.flexible_coordinator.register_phase_entry_flexible(
            slot, FlexibleSlotPhase.TASK_ASSIGNMENT
        )

    async def _prepare_for_consensus_phase(self, slot: int):
        """Prepare for upcoming consensus phase."""
        logger.info(f"🤝 Preparing for consensus phase in slot {slot}")
        # Pre-load any data needed for consensus

    async def _join_ongoing_consensus(self, slot: int):
        """Join an ongoing consensus phase."""
        logger.info(f"🤝 Joining ongoing consensus for slot {slot}")
        await self.flexible_coordinator.register_phase_entry_flexible(
            slot, FlexibleSlotPhase.CONSENSUS_SCORING
        )

    async def _join_metagraph_update(self, slot: int):
        """Join metagraph update phase."""
        logger.info(f"📊 Joining metagraph update for slot {slot}")
        await self.flexible_coordinator.register_phase_entry_flexible(
            slot, FlexibleSlotPhase.METAGRAPH_UPDATE
        )

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this flexible validator."""
        uptime = time.time() - self.startup_time

        return {
            "validator_uid": self.core.info.uid,
            "uptime_seconds": uptime,
            "current_mode": self.current_mode,
            "network_sync_status": self.network_sync_status,
            "phases_completed": self.phases_completed,
            "successful_transitions": self.successful_transitions,
            "consensus_participation_rate": self.consensus_participation_rate,
            "last_successful_consensus": self.last_successful_consensus,
            "auto_adapt_timing": self.auto_adapt_timing,
        }
