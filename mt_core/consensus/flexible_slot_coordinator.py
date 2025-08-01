#!/usr/bin/env python3
"""
Flexible Slot Coordinator - Hybrid Consensus Mode

Allows validators to start anytime while maintaining synchronization for critical events.
Key improvements:
- Validators can join mid-slot
- Event-driven synchronization instead of rigid timing
- Consensus deadlines with buffer times
- Dynamic phase detection and adjustment
"""

import asyncio
import time
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Flexible timing constants
CONSENSUS_CHECK_INTERVAL = 3  # Check every 3 seconds
MAJORITY_THRESHOLD = 2  # Need 2 out of 3 validators
DEFAULT_BUFFER_SECONDS = 30  # Buffer time for late validators
MIN_TASK_EXECUTION_TIME = 45  # Minimum 45 seconds for task execution


class FlexibleSlotPhase(Enum):
    """Flexible phases with event-driven transitions"""

    TASK_ASSIGNMENT = "task_assignment"
    TASK_EXECUTION = "task_execution"
    CONSENSUS_SCORING = "consensus_scoring"
    METAGRAPH_UPDATE = "metagraph_update"
    CYCLE_TRANSITION = "cycle_transition"


@dataclass
class FlexibleSlotConfig:
    """Flexible configuration allowing validators to start anytime"""

    # Core timing (more flexible)
    slot_duration_minutes: float = 4.0  # Longer slots for flexibility

    # Minimum phase durations (not fixed boundaries)
    min_task_assignment_seconds: int = 30  # At least 30s for task assignment
    min_task_execution_seconds: int = 60  # At least 60s for task execution
    min_consensus_seconds: int = 45  # At least 45s for consensus
    min_metagraph_update_seconds: int = 15  # At least 15s for metagraph

    # Buffer times for late joiners
    task_deadline_buffer: int = 20  # 20s buffer for task completion
    consensus_deadline_buffer: int = 30  # 30s buffer for consensus
    metagraph_deadline_buffer: int = 10  # 10s buffer for metagraph

    # Dynamic adjustment parameters
    allow_mid_slot_join: bool = True  # Allow validators to join mid-slot
    auto_extend_on_consensus: bool = True  # Auto-extend if consensus not reached
    max_auto_extension_seconds: int = 60  # Max auto-extension time


class FlexibleSlotCoordinator:
    """
    Flexible Slot Coordinator that allows validators to start anytime
    while maintaining synchronization for critical events.
    """

    def __init__(
        self,
        validator_uid: str,
        coordination_dir: str = "slot_coordination",
        slot_config: Optional[FlexibleSlotConfig] = None,
    ):
        self.validator_uid = validator_uid
        self.coordination_dir = Path(coordination_dir)
        self.coordination_dir.mkdir(exist_ok=True)
        self.slot_config = slot_config or FlexibleSlotConfig()

        # Dynamic state tracking
        self.current_slot = None
        self.current_phase = None
        self.phase_start_time = None
        self.slot_start_time = None
        self.joined_mid_slot = False

        # Event tracking
        self.phase_events = {}  # slot -> phase -> event_timestamp
        self.validator_readiness = {}  # slot -> phase -> [validator_list]

        logger.info(f"🔄 FlexibleSlotCoordinator initialized for {validator_uid}")
        logger.info(
            f"📊 Config: {self.slot_config.slot_duration_minutes}min slots, mid-join: {self.slot_config.allow_mid_slot_join}"
        )

    def get_current_slot_and_phase(self) -> Tuple[int, FlexibleSlotPhase, dict]:
        """
        Get current slot and phase, with the ability to join mid-slot.

        Returns:
            Tuple of (slot_number, current_phase, phase_info)
        """
        current_time = time.time()

        # Try to detect ongoing slot from coordination files
        active_slot, active_phase = self._detect_active_slot_from_coordination()

        if active_slot is not None and self.slot_config.allow_mid_slot_join:
            # Join the active slot if mid-slot joining is allowed
            self.joined_mid_slot = True
            phase_info = {
                "joined_mid_slot": True,
                "active_validators": self._get_active_validators_in_slot(active_slot),
                "phase_start_estimate": self._estimate_phase_start_time(
                    active_slot, active_phase
                ),
            }

            logger.info(
                f"🔄 {self.validator_uid} joining active slot {active_slot} in {active_phase.value} phase"
            )
            return active_slot, active_phase, phase_info

        # Calculate slot based on flexible timing
        if not hasattr(self, "_epoch_start"):
            self._epoch_start = current_time  # Dynamic epoch start

        slot_duration_seconds = self.slot_config.slot_duration_minutes * 60
        calculated_slot = int(
            (current_time - self._epoch_start) // slot_duration_seconds
        )

        # Determine phase based on slot progress and coordination files
        phase = self._calculate_current_phase(calculated_slot, current_time)

        phase_info = {
            "joined_mid_slot": False,
            "calculated_slot": True,
            "epoch_start": self._epoch_start,
        }

        return calculated_slot, phase, phase_info

    def _detect_active_slot_from_coordination(
        self,
    ) -> Tuple[Optional[int], Optional[FlexibleSlotPhase]]:
        """Detect active slot by scanning coordination files"""
        coordination_files = list(self.coordination_dir.glob("slot_*_*.json"))

        if not coordination_files:
            return None, None

        # Find the most recent slot with active validators
        active_slots = {}
        current_time = time.time()

        for file_path in coordination_files:
            try:
                parts = file_path.stem.split("_")
                if len(parts) >= 4:  # slot_X_phase_validator.json
                    slot_num = int(parts[1])
                    phase = parts[2]

                    # Check if file is recent (within last 10 minutes)
                    if file_path.stat().st_mtime > current_time - 600:
                        if slot_num not in active_slots:
                            active_slots[slot_num] = []
                        active_slots[slot_num].append(phase)

            except (ValueError, IndexError, OSError):
                continue

        if not active_slots:
            return None, None

        # Return the highest slot number with recent activity
        latest_slot = max(active_slots.keys())
        phases = active_slots[latest_slot]

        # Determine most common phase
        phase_counts = {}
        for phase in phases:
            phase_counts[phase] = phase_counts.get(phase, 0) + 1

        most_common_phase = max(phase_counts.keys(), key=lambda x: phase_counts[x])

        try:
            detected_phase = FlexibleSlotPhase(most_common_phase)
            return latest_slot, detected_phase
        except ValueError:
            return latest_slot, FlexibleSlotPhase.TASK_ASSIGNMENT

    def _calculate_current_phase(
        self, slot: int, current_time: float
    ) -> FlexibleSlotPhase:
        """Calculate current phase based on flexible timing"""
        slot_duration_seconds = self.slot_config.slot_duration_minutes * 60
        slot_start = self._epoch_start + (slot * slot_duration_seconds)
        seconds_into_slot = current_time - slot_start

        # Flexible phase calculation
        if seconds_into_slot < self.slot_config.min_task_assignment_seconds:
            return FlexibleSlotPhase.TASK_ASSIGNMENT
        elif seconds_into_slot < (
            self.slot_config.min_task_assignment_seconds
            + self.slot_config.min_task_execution_seconds
        ):
            return FlexibleSlotPhase.TASK_EXECUTION
        elif seconds_into_slot < (
            self.slot_config.min_task_assignment_seconds
            + self.slot_config.min_task_execution_seconds
            + self.slot_config.min_consensus_seconds
        ):
            return FlexibleSlotPhase.CONSENSUS_SCORING
        else:
            return FlexibleSlotPhase.METAGRAPH_UPDATE

    async def register_phase_entry_flexible(
        self, slot: int, phase: FlexibleSlotPhase, extra_data: Dict = None
    ):
        """Register phase entry with flexible timing support"""
        phase_file = (
            self.coordination_dir
            / f"slot_{slot}_{phase.value}_{self.validator_uid}.json"
        )

        phase_data = {
            "validator_uid": self.validator_uid,
            "slot": slot,
            "phase": phase.value,
            "timestamp": time.time(),
            "joined_mid_slot": getattr(self, "joined_mid_slot", False),
            "extra_data": extra_data or {},
        }

        try:
            with open(phase_file, "w") as f:
                json.dump(phase_data, f, indent=2)

            logger.info(
                f"✅ {self.validator_uid} registered {phase.value} phase for slot {slot}"
            )

        except Exception as e:
            logger.error(f"❌ Error registering phase: {e}")

    async def wait_for_consensus_deadline(
        self, slot: int, phase: FlexibleSlotPhase, deadline_buffer: Optional[int] = None
    ) -> List[str]:
        """
        Wait for consensus with flexible deadline management.

        Instead of fixed timing, wait for either:
        1. Majority consensus reached
        2. Deadline + buffer time reached
        3. All known validators ready
        """
        if deadline_buffer is None:
            deadline_buffer = getattr(
                self.slot_config, f"{phase.value}_deadline_buffer", 30
            )

        start_time = time.time()
        max_wait_time = deadline_buffer

        logger.info(
            f"⏳ {self.validator_uid} waiting for {phase.value} consensus (max {max_wait_time}s)"
        )

        while time.time() - start_time < max_wait_time:
            ready_validators = self._get_ready_validators_flexible(slot, phase)

            logger.debug(
                f"🔍 Slot {slot} {phase.value}: {len(ready_validators)} validators ready"
            )

            # Check for majority consensus
            if len(ready_validators) >= MAJORITY_THRESHOLD:
                logger.info(
                    f"✅ Consensus reached for {phase.value}: {ready_validators}"
                )
                return ready_validators

            # Check if all known active validators are ready
            active_validators = self._get_active_validators_in_slot(slot)
            if active_validators and len(ready_validators) >= len(active_validators):
                logger.info(
                    f"✅ All active validators ready for {phase.value}: {ready_validators}"
                )
                return ready_validators

            await asyncio.sleep(CONSENSUS_CHECK_INTERVAL)

        # Handle auto-extension if enabled
        if (
            self.slot_config.auto_extend_on_consensus
            and len(ready_validators) > 0
            and len(ready_validators) < MAJORITY_THRESHOLD
        ):

            extension_time = min(self.slot_config.max_auto_extension_seconds, 60)
            logger.info(
                f"🔄 Auto-extending {phase.value} deadline by {extension_time}s"
            )

            # Wait for auto-extension period
            while time.time() - start_time < max_wait_time + extension_time:
                ready_validators = self._get_ready_validators_flexible(slot, phase)
                if len(ready_validators) >= MAJORITY_THRESHOLD:
                    return ready_validators
                await asyncio.sleep(CONSENSUS_CHECK_INTERVAL)

        logger.warning(
            f"⚠️ Consensus deadline reached with {len(ready_validators)} validators"
        )
        return ready_validators

    def _get_ready_validators_flexible(
        self, slot: int, phase: FlexibleSlotPhase
    ) -> List[str]:
        """Get ready validators with flexible file detection"""
        ready_validators = []
        current_time = time.time()

        # Look for any coordination files for this slot/phase
        pattern = f"slot_{slot}_{phase.value}_*.json"
        coordination_files = list(self.coordination_dir.glob(pattern))

        for file_path in coordination_files:
            try:
                # Check if file is recent (within last 5 minutes)
                if file_path.stat().st_mtime < current_time - 300:
                    continue

                with open(file_path, "r") as f:
                    data = json.load(f)

                if data.get("slot") == slot and data.get("phase") == phase.value:

                    validator_uid = data.get("validator_uid")
                    if validator_uid:
                        ready_validators.append(validator_uid)

            except (json.JSONDecodeError, OSError):
                continue

        return ready_validators

    def _get_active_validators_in_slot(self, slot: int) -> List[str]:
        """Get list of validators active in the given slot"""
        active_validators = set()

        # Scan all coordination files for this slot
        pattern = f"slot_{slot}_*.json"
        coordination_files = list(self.coordination_dir.glob(pattern))

        for file_path in coordination_files:
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    if data.get("slot") == slot:
                        validator_uid = data.get("validator_uid")
                        if validator_uid:
                            active_validators.add(validator_uid)
            except:
                continue

        return list(active_validators)

    def _estimate_phase_start_time(self, slot: int, phase: FlexibleSlotPhase) -> float:
        """Estimate when the current phase started"""
        # Look for the earliest coordination file for this slot/phase
        pattern = f"slot_{slot}_{phase.value}_*.json"
        coordination_files = list(self.coordination_dir.glob(pattern))

        earliest_time = time.time()

        for file_path in coordination_files:
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    timestamp = data.get("timestamp", time.time())
                    if timestamp < earliest_time:
                        earliest_time = timestamp
            except:
                continue

        return earliest_time

    async def handle_flexible_phase_transition(
        self,
        current_slot: int,
        from_phase: FlexibleSlotPhase,
        to_phase: FlexibleSlotPhase,
    ) -> bool:
        """
        Handle flexible phase transition with event-driven coordination.

        This allows validators to transition at their own pace while
        maintaining synchronization for critical events.
        """
        logger.info(
            f"🔄 {self.validator_uid} transitioning from {from_phase.value} to {to_phase.value}"
        )

        try:
            # Step 1: Complete current phase activities
            await self._complete_phase_activities(current_slot, from_phase)

            # Step 2: Register entry to next phase
            await self.register_phase_entry_flexible(current_slot, to_phase)

            # Step 3: Wait for consensus deadline (flexible)
            ready_validators = await self.wait_for_consensus_deadline(
                current_slot, to_phase
            )

            if len(ready_validators) >= MAJORITY_THRESHOLD:
                logger.info(
                    f"✅ Flexible transition completed: {from_phase.value} → {to_phase.value}"
                )
                return True
            else:
                logger.info(f"⚠️ Proceeding with {len(ready_validators)} validators")
                return True  # Proceed anyway for flexibility

        except Exception as e:
            logger.error(f"❌ Error in flexible transition: {e}")
            return False

    async def _complete_phase_activities(self, slot: int, phase: FlexibleSlotPhase):
        """Complete any pending activities for the current phase"""
        # This is a hook for validators to complete their phase-specific work
        # before transitioning to the next phase
        pass

    def get_deadline_for_phase(self, slot: int, phase: FlexibleSlotPhase) -> float:
        """Calculate flexible deadline for a phase"""
        if not hasattr(self, "_epoch_start"):
            return time.time() + 300  # Default 5 minute deadline

        slot_duration_seconds = self.slot_config.slot_duration_minutes * 60
        slot_start = self._epoch_start + (slot * slot_duration_seconds)

        # Calculate phase deadline with buffers
        if phase == FlexibleSlotPhase.TASK_ASSIGNMENT:
            deadline = slot_start + self.slot_config.min_task_assignment_seconds
        elif phase == FlexibleSlotPhase.TASK_EXECUTION:
            deadline = (
                slot_start
                + self.slot_config.min_task_assignment_seconds
                + self.slot_config.min_task_execution_seconds
                + self.slot_config.task_deadline_buffer
            )
        elif phase == FlexibleSlotPhase.CONSENSUS_SCORING:
            deadline = (
                slot_start
                + self.slot_config.min_task_assignment_seconds
                + self.slot_config.min_task_execution_seconds
                + self.slot_config.min_consensus_seconds
                + self.slot_config.consensus_deadline_buffer
            )
        else:  # METAGRAPH_UPDATE
            deadline = (
                slot_start
                + slot_duration_seconds
                - self.slot_config.metagraph_deadline_buffer
            )

        return deadline

    def cleanup_old_coordination_files(self, keep_slots: int = 5):
        """Clean up old coordination files to prevent disk buildup"""
        current_time = time.time()
        cutoff_time = current_time - (
            keep_slots * self.slot_config.slot_duration_minutes * 60
        )

        for file_path in self.coordination_dir.glob("slot_*.json"):
            try:
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
            except OSError:
                pass
