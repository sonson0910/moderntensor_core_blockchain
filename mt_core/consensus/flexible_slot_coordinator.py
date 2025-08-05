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


class FlexibleJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle ValidatorScore and other Pydantic objects"""

    def default(self, obj):
        # Handle Pydantic BaseModel objects (like ValidatorScore)
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        elif hasattr(obj, "dict"):
            return obj.dict()
        elif hasattr(obj, "__dict__"):
            return obj.__dict__
        elif isinstance(obj, (list, tuple)):
            return [self.default(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: self.default(v) for k, v in obj.items()}
        else:
            # Let the base class default method handle other types
            return super().default(obj)


class FlexibleSlotPhase(Enum):
    """Flexible phases with event-driven transitions - SIMPLIFIED TO 3 PHASES"""

    TASK_ASSIGNMENT = "task_assignment"  # Includes task execution
    CONSENSUS_SCORING = "consensus_scoring"
    METAGRAPH_UPDATE = "metagraph_update"
    CYCLE_TRANSITION = "cycle_transition"


@dataclass
class FlexibleSlotConfig:
    """Flexible configuration allowing validators to start anytime"""

    # Core timing (ULTRA FAST - for rapid testing)
    slot_duration_minutes: float = 1.0  # 60s total - ultra fast cycles for testing

    # Minimum phase durations - SIMPLIFIED 3 PHASES (ULTRA FAST FOR TESTING)
    min_task_assignment_seconds: int = (
        35  # 35 seconds for task assignment + execution (3 rounds + buffer)
    )
    min_consensus_seconds: int = 15  # 15 seconds - P2P consensus
    min_metagraph_update_seconds: int = 10  # 10 seconds for metagraph

    # Buffer times for late joiners (REDUCED FOR TESTING)
    task_deadline_buffer: int = 5  # 5s buffer for task completion
    consensus_deadline_buffer: int = 5  # 5s buffer for consensus
    metagraph_deadline_buffer: int = 5  # 5s buffer for metagraph

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

        # Clean up old coordination files on initialization
        self._cleanup_old_coordination_files()

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

        # Calculate slot based on flexible timing FIRST
        if not hasattr(self, "_epoch_start"):
            self._epoch_start = current_time  # Dynamic epoch start

        slot_duration_seconds = self.slot_config.slot_duration_minutes * 60
        calculated_slot = int(
            (current_time - self._epoch_start) // slot_duration_seconds
        )
        calculated_phase = self._calculate_current_phase(calculated_slot, current_time)

        # CRITICAL FIX: If validator starts late in slot (progress > 50s), force next slot
        original_slot = calculated_slot
        slot_start = self._epoch_start + (calculated_slot * slot_duration_seconds)
        seconds_into_slot = current_time - slot_start

        # DEBUG: Always log slot timing check
        logger.info(
            f"🔍 {self.validator_uid} SLOT TIMING CHECK: slot {calculated_slot}, progress {seconds_into_slot:.1f}s, threshold 50.0s"
        )

        if seconds_into_slot > 50.0:  # If past metagraph phase start
            logger.warning(
                f"🚨 {self.validator_uid} Starting late in slot {calculated_slot} (progress: {seconds_into_slot:.1f}s/60s)"
            )
            logger.warning(
                f"⚡ {self.validator_uid} FORCING progression to next slot {calculated_slot + 1} to ensure full cycle"
            )
            calculated_slot += 1
            calculated_phase = (
                FlexibleSlotPhase.TASK_ASSIGNMENT
            )  # Start fresh from task assignment
            # Recalculate timing for the NEW slot
            slot_start = self._epoch_start + (calculated_slot * slot_duration_seconds)
            seconds_into_slot = current_time - slot_start

        # PRIORITIZE TIME-BASED CALCULATION for phase progression
        # Only use coordination files for slot detection, not phase determination

        # Enhanced timing debug (slot_start and seconds_into_slot already calculated above)

        # Less frequent timing debug (every 30s instead of 5s)
        if int(seconds_into_slot) % 30 == 0 or seconds_into_slot < 10:
            logger.info(
                f"📊 {self.validator_uid} TIMING: slot {calculated_slot}, phase {calculated_phase.value}, progress {seconds_into_slot:.0f}s/{slot_duration_seconds:.0f}s"
            )

            # Phase boundaries debug - SIMPLIFIED 3 PHASES
            task_end = self.slot_config.min_task_assignment_seconds
            cons_end = task_end + self.slot_config.min_consensus_seconds

            logger.info(
                f"🎯 {self.validator_uid} Phase boundaries: Task(0-{task_end}s), Cons({task_end}-{cons_end}s), Meta({cons_end}s+)"
            )
        else:
            logger.debug(
                f"📊 {self.validator_uid} TIMING: slot {calculated_slot}, phase {calculated_phase.value}, progress {seconds_into_slot:.0f}s/{slot_duration_seconds:.0f}s"
            )

        # Try to detect ongoing slot from coordination files for reference only
        active_slot, active_phase = self._detect_active_slot_from_coordination()

        if active_slot is not None:
            logger.debug(
                f"📂 {self.validator_uid} Coordination files suggest: slot {active_slot}, phase {active_phase.value if active_phase else 'None'}"
            )

        # TEMPORARY FIX: DISABLE coordination file joining to force time-based progression
        # This prevents jumping to stale slots like 100 and ensures proper P2P/metagraph
        if (
            False
        ):  # DISABLED - was: active_slot > (calculated_slot + 2) and allow_mid_slot_join

            # Join newer slot detected from coordination (only if significantly newer)
            self.joined_mid_slot = True
            phase_info = {
                "joined_mid_slot": True,
                "active_validators": self._get_active_validators_in_slot(active_slot),
                "phase_start_estimate": self._estimate_phase_start_time(
                    active_slot, active_phase
                ),
            }

            logger.info(
                f"🔄 {self.validator_uid} joining SIGNIFICANTLY NEWER slot {active_slot} from coordination (time-based was {calculated_slot})"
            )
            return active_slot, active_phase, phase_info
        elif active_slot is not None and active_slot <= (calculated_slot + 2):
            logger.debug(
                f"🗑️ {self.validator_uid} ignoring stale coordination slot {active_slot} (time-based is {calculated_slot})"
            )

        # Force cleanup stale files when using time-based calculation
        self._force_cleanup_stale_coordination_files(calculated_slot)

        # Use time-based calculation as fallback
        phase_info = {
            "joined_mid_slot": False,
            "calculated_slot": True,
            "epoch_start": self._epoch_start,
            "preferred_method": "time_based",
        }

        logger.debug(
            f"📊 {self.validator_uid} using time-based calculation: slot {calculated_slot}, phase {calculated_phase.value}"
        )
        return calculated_slot, calculated_phase, phase_info

    def _cleanup_old_coordination_files(self):
        """Clean up old coordination files to prevent confusion - AGGRESSIVE CLEANUP"""
        try:
            current_time = time.time()
            cutoff_time = current_time - (5 * 60)  # 5 minutes ago (more aggressive)

            for file_path in self.coordination_dir.glob("slot_*.json"):
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    logger.debug(
                        f"🗑️ Cleaned up old coordination file: {file_path.name}"
                    )

        except Exception as e:
            logger.warning(f"Error cleaning up coordination files: {e}")

    def _force_cleanup_stale_coordination_files(self, current_slot: int):
        """Force cleanup of coordination files for slots older than current"""
        try:
            for file_path in self.coordination_dir.glob("slot_*.json"):
                filename = file_path.name
                # Extract slot number from filename like "slot_5_task_assignment_uid.json"
                if filename.startswith("slot_"):
                    try:
                        slot_part = filename.split("_")[1]
                        file_slot = int(slot_part)
                        if file_slot < current_slot:  # Remove files for older slots
                            file_path.unlink()
                            logger.debug(
                                f"🗑️ Force cleaned stale slot {file_slot} file: {filename}"
                            )
                    except (IndexError, ValueError):
                        continue  # Skip files with unexpected format
        except Exception as e:
            logger.warning(f"Error force cleaning stale coordination files: {e}")

    def _cleanup_old_coordination_files_original(self):
        """Clean up old coordination files to prevent getting stuck in old states"""
        try:
            coordination_files = list(self.coordination_dir.glob("slot_*_*.json"))
            current_time = time.time()

            # Remove files older than 30 minutes
            cleanup_threshold = current_time - 1800  # 30 minutes
            cleaned_count = 0

            for file_path in coordination_files:
                try:
                    if file_path.stat().st_mtime < cleanup_threshold:
                        file_path.unlink()
                        cleaned_count += 1
                except OSError:
                    continue

            if cleaned_count > 0:
                logger.info(f"🧹 Cleaned up {cleaned_count} old coordination files")

        except Exception as e:
            logger.warning(f"⚠️ Failed to cleanup coordination files: {e}")

    def get_current_blockchain_slot(self) -> int:
        """
        Get current blockchain slot number (compatibility method).

        Returns:
            Current slot number as integer
        """
        current_slot, _, _ = self.get_current_slot_and_phase()
        return current_slot

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
        """Calculate current phase based on flexible timing - SIMPLIFIED 3 PHASES"""
        slot_duration_seconds = self.slot_config.slot_duration_minutes * 60
        slot_start = self._epoch_start + (slot * slot_duration_seconds)
        seconds_into_slot = current_time - slot_start

        # SIMPLIFIED 3-phase calculation (removed task_execution)
        if seconds_into_slot < self.slot_config.min_task_assignment_seconds:
            return FlexibleSlotPhase.TASK_ASSIGNMENT  # Includes execution
        elif seconds_into_slot < (
            self.slot_config.min_task_assignment_seconds
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
                json.dump(phase_data, f, indent=2, cls=FlexibleJSONEncoder)

            logger.info(
                f"✅ {self.validator_uid} registered {phase.value} phase for slot {slot}"
            )

        except Exception as e:
            logger.error(f"❌ Error registering phase: {e}")
            logger.debug(f"❌ Phase data: {phase_data}")

            # Try to serialize with basic data types only as fallback
            try:
                safe_phase_data = {
                    "validator_uid": self.validator_uid,
                    "slot": slot,
                    "phase": phase.value,
                    "timestamp": time.time(),
                    "joined_mid_slot": getattr(self, "joined_mid_slot", False),
                    "extra_data": self._sanitize_extra_data(extra_data or {}),
                }
                with open(phase_file, "w") as f:
                    json.dump(safe_phase_data, f, indent=2)
                logger.warning(f"⚠️ Used fallback serialization for phase registration")
            except Exception as fallback_error:
                logger.error(f"❌ Fallback serialization also failed: {fallback_error}")

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

    async def enforce_task_assignment_cutoff(self, slot: int) -> bool:
        """
        Flexible version of task assignment cutoff enforcement.

        For flexible mode, task assignment cutoff is already handled
        in the continuous assignment loop, so this is mostly a no-op
        but maintains API compatibility.
        """
        import asyncio

        logger.info(
            f"🔄 {self.validator_uid} Flexible cutoff check for slot {slot} (already handled in continuous assignment)"
        )

        # Calculate current phase to verify we're past task assignment
        current_time = time.time()
        if hasattr(self, "_epoch_start"):
            slot_duration_seconds = self.slot_config.slot_duration_minutes * 60
            slot_start = self._epoch_start + (slot * slot_duration_seconds)
            seconds_into_slot = current_time - slot_start

            if seconds_into_slot < self.slot_config.min_task_assignment_seconds:
                # Still in task assignment phase
                wait_time = (
                    self.slot_config.min_task_assignment_seconds - seconds_into_slot
                )
                logger.info(
                    f"⏰ {self.validator_uid} Still in task assignment phase, waiting {wait_time:.1f}s for cutoff"
                )
                await asyncio.sleep(wait_time)
            else:
                logger.info(
                    f"✅ {self.validator_uid} Already past task assignment phase for slot {slot}"
                )

        # Register phase transition if needed
        # Task execution is now included in task assignment phase - no separate registration needed

        return True

    async def coordinate_consensus_round(self, slot: int, local_scores: dict) -> dict:
        """
        Flexible P2P consensus coordination using actual P2P logic.

        REAL P2P CONSENSUS - reuses existing SlotCoordinator logic.
        """
        logger.info(
            f"🤝 {self.validator_uid} Starting REAL P2P consensus for slot {slot} with {len(local_scores)} local scores"
        )

        try:
            # Step 1: Register consensus readiness with scores (using flexible phase)
            await self.register_phase_entry_flexible(
                slot, FlexibleSlotPhase.CONSENSUS_SCORING, {"scores": local_scores}
            )

            # Step 2: Wait for other validators to be ready with timeout
            timeout_seconds = 30  # Reduced from original for faster flexible consensus
            ready_validators = await self._wait_for_flexible_consensus(
                slot, timeout_seconds
            )

            # Step 3: Calculate consensus if we have enough validators
            MINIMUM_VALIDATORS = 1  # Single validator can proceed (flexible mode)
            if len(ready_validators) >= MINIMUM_VALIDATORS:
                logger.info(
                    f"📊 {self.validator_uid} Computing consensus with {len(ready_validators)} validators: {ready_validators}"
                )
                consensus_scores = self._calculate_flexible_consensus_scores(
                    slot, ready_validators
                )
            else:
                logger.warning(
                    f"⚠️ {self.validator_uid} Using local scores only - no other validators found"
                )
                consensus_scores = local_scores.copy()

            logger.info(
                f"✅ {self.validator_uid} REAL P2P consensus completed for slot {slot}: {len(consensus_scores)} final scores"
            )
            return consensus_scores

        except Exception as e:
            logger.error(
                f"❌ {self.validator_uid} Error in P2P consensus: {e}, falling back to local scores"
            )
            return local_scores.copy()

    async def _wait_for_flexible_consensus(
        self, slot: int, timeout_seconds: int
    ) -> list:
        """Wait for other validators to register consensus scores"""
        start_time = time.time()
        ready_validators = [self.validator_uid]  # Always include self

        while time.time() - start_time < timeout_seconds:
            # Look for consensus scoring files from other validators
            consensus_files = list(
                self.coordination_dir.glob(f"slot_{slot}_consensus_scoring_*.json")
            )

            for file_path in consensus_files:
                try:
                    # Extract validator UID from filename
                    filename = file_path.name
                    # slot_0_consensus_scoring_validator_001.json
                    parts = (
                        filename.replace("slot_", "").replace(".json", "").split("_")
                    )
                    if len(parts) >= 3:
                        validator_uid = "_".join(
                            parts[2:]
                        )  # Everything after "consensus_scoring"
                        if validator_uid not in ready_validators:
                            ready_validators.append(validator_uid)
                            logger.info(
                                f"🔗 {self.validator_uid} Found validator {validator_uid} ready for consensus"
                            )
                except Exception:
                    continue

            if len(ready_validators) > 1:  # Found other validators
                break

            await asyncio.sleep(2)  # Check every 2 seconds

        logger.info(
            f"📊 {self.validator_uid} Ready validators for consensus: {ready_validators}"
        )
        return ready_validators

    def _calculate_flexible_consensus_scores(
        self, slot: int, participating_validators: list
    ) -> dict:
        """Calculate consensus scores using existing SlotCoordinator logic"""
        all_scores = {}

        # Collect scores from all participating validators
        for validator_uid in participating_validators:
            score_file = (
                self.coordination_dir
                / f"slot_{slot}_consensus_scoring_{validator_uid}.json"
            )
            if score_file.exists():
                try:
                    with open(score_file, "r") as f:
                        data = json.load(f)
                        scores = data.get("extra_data", {}).get("scores", {})

                        # Handle both dict and list formats (copied from SlotCoordinator)
                        if isinstance(scores, dict):
                            # Standard dict format: {miner_uid: score}
                            for miner_uid, score in scores.items():
                                if miner_uid not in all_scores:
                                    all_scores[miner_uid] = []
                                all_scores[miner_uid].append(score)
                        elif isinstance(scores, list):
                            # List format: [{"miner_uid": "...", "score": 0.5}]
                            for score_entry in scores:
                                if (
                                    isinstance(score_entry, dict)
                                    and "miner_uid" in score_entry
                                    and "score" in score_entry
                                ):
                                    miner_uid = score_entry["miner_uid"]
                                    score = score_entry["score"]
                                    if miner_uid not in all_scores:
                                        all_scores[miner_uid] = []
                                    all_scores[miner_uid].append(score)
                        else:
                            logger.warning(
                                f"⚠️ Invalid scores format from {validator_uid}: {type(scores)}"
                            )

                except Exception as e:
                    logger.error(f"❌ Error reading scores from {validator_uid}: {e}")

        # Calculate consensus (simple average) - same logic as SlotCoordinator
        consensus_scores = {}
        for miner_uid, score_list in all_scores.items():
            if score_list:
                consensus_score = sum(score_list) / len(score_list)
                consensus_scores[miner_uid] = consensus_score
                logger.info(
                    f"📊 {self.validator_uid} Miner {miner_uid}: "
                    f"{consensus_score:.4f} (averaged from {len(score_list)} validators)"
                )

        return consensus_scores

    # === LEGACY COMPATIBILITY METHODS ===
    # These methods provide compatibility with SlotCoordinator API

    async def register_phase_entry(
        self, slot: int, phase, extra_data: dict = None
    ) -> bool:
        """
        Legacy compatibility method for register_phase_entry.
        Converts SlotPhase to FlexibleSlotPhase and delegates to register_phase_entry_flexible.
        """
        # Import here to avoid circular imports
        from .slot_coordinator import SlotPhase

        # Convert SlotPhase to FlexibleSlotPhase
        phase_mapping = {
            SlotPhase.TASK_ASSIGNMENT: FlexibleSlotPhase.TASK_ASSIGNMENT,
            # SlotPhase.TASK_EXECUTION: removed (merged into task_assignment)
            SlotPhase.CONSENSUS_SCORING: FlexibleSlotPhase.CONSENSUS_SCORING,
            SlotPhase.METAGRAPH_UPDATE: FlexibleSlotPhase.METAGRAPH_UPDATE,
        }

        flexible_phase = phase_mapping.get(phase, phase)

        logger.info(
            f"🔄 {self.validator_uid} Legacy register_phase_entry: {phase} → {flexible_phase} for slot {slot}"
        )

        return await self.register_phase_entry_flexible(
            slot, flexible_phase, extra_data or {}
        )

    async def wait_for_phase_consensus(
        self, slot: int, phase, timeout: int = 120
    ) -> list:
        """
        Legacy compatibility method for wait_for_phase_consensus.

        For flexible mode, we wait for coordination files from other validators.
        This is a simplified version that checks for active validators.
        """
        # Import here to avoid circular imports
        from .slot_coordinator import SlotPhase

        phase_mapping = {
            SlotPhase.TASK_ASSIGNMENT: FlexibleSlotPhase.TASK_ASSIGNMENT,
            # SlotPhase.TASK_EXECUTION: removed (merged into task_assignment)
            SlotPhase.CONSENSUS_SCORING: FlexibleSlotPhase.CONSENSUS_SCORING,
            SlotPhase.METAGRAPH_UPDATE: FlexibleSlotPhase.METAGRAPH_UPDATE,
        }

        flexible_phase = phase_mapping.get(phase, phase)

        logger.info(
            f"🔍 {self.validator_uid} Waiting for phase consensus: {phase} → {flexible_phase} (timeout: {timeout}s)"
        )

        start_time = time.time()
        ready_validators = [self.validator_uid]  # Always include self

        while time.time() - start_time < timeout:
            # Look for phase files from other validators
            phase_files = list(
                self.coordination_dir.glob(f"slot_{slot}_{flexible_phase.value}_*.json")
            )

            for file_path in phase_files:
                try:
                    # Extract validator UID from filename
                    filename = file_path.name
                    # slot_0_task_assignment_validator_001.json
                    parts = (
                        filename.replace("slot_", "").replace(".json", "").split("_")
                    )
                    if len(parts) >= 3:
                        validator_uid = "_".join(
                            parts[2:]
                        )  # Everything after phase name
                        if validator_uid not in ready_validators:
                            ready_validators.append(validator_uid)
                            logger.info(
                                f"🔗 {self.validator_uid} Found validator {validator_uid} in phase {flexible_phase.value}"
                            )
                except Exception:
                    continue

            # For flexible mode, don't require majority - any validator is good
            if len(ready_validators) >= 1:
                break

            await asyncio.sleep(2)  # Check every 2 seconds

        logger.info(
            f"📊 {self.validator_uid} Phase consensus complete: {len(ready_validators)} validators ready"
        )
        return ready_validators

    def get_slot_phase(self, slot: int) -> tuple:
        """
        Legacy compatibility method for get_slot_phase.
        Returns (SlotPhase, seconds_into_slot, seconds_remaining) format.
        """
        # Import here to avoid circular imports
        from .slot_coordinator import SlotPhase

        # Get current phase from flexible coordinator
        current_slot, current_flexible_phase, metadata = (
            self.get_current_slot_and_phase()
        )

        # Convert FlexibleSlotPhase back to SlotPhase
        phase_mapping = {
            FlexibleSlotPhase.TASK_ASSIGNMENT: SlotPhase.TASK_ASSIGNMENT,
            # FlexibleSlotPhase.TASK_EXECUTION: removed (merged into task assignment)
            FlexibleSlotPhase.CONSENSUS_SCORING: SlotPhase.CONSENSUS_SCORING,
            FlexibleSlotPhase.METAGRAPH_UPDATE: SlotPhase.METAGRAPH_UPDATE,
        }

        legacy_phase = phase_mapping.get(
            current_flexible_phase, SlotPhase.TASK_ASSIGNMENT
        )

        # Calculate timing information
        if hasattr(self, "_epoch_start"):
            slot_duration_seconds = self.slot_config.slot_duration_minutes * 60
            slot_start = self._epoch_start + (slot * slot_duration_seconds)
            current_time = time.time()
            seconds_into_slot = current_time - slot_start
            seconds_remaining = slot_duration_seconds - seconds_into_slot
        else:
            seconds_into_slot = 0
            seconds_remaining = 180  # Default 3 minutes

        logger.debug(
            f"📊 {self.validator_uid} get_slot_phase({slot}): {legacy_phase}, "
            f"{seconds_into_slot:.1f}s in, {seconds_remaining:.1f}s remaining"
        )

        return legacy_phase, seconds_into_slot, seconds_remaining

    def _sanitize_extra_data(self, extra_data: Dict) -> Dict:
        """Sanitize extra_data to be JSON serializable"""
        sanitized = {}

        for key, value in extra_data.items():
            try:
                if hasattr(value, "model_dump"):
                    # Pydantic v2 BaseModel
                    sanitized[key] = value.model_dump()
                elif hasattr(value, "dict"):
                    # Pydantic v1 BaseModel
                    sanitized[key] = value.dict()
                elif hasattr(value, "__dict__"):
                    # Regular Python object
                    sanitized[key] = value.__dict__
                elif isinstance(value, (list, tuple)):
                    # Handle lists/tuples of objects
                    sanitized[key] = [
                        (
                            item.model_dump()
                            if hasattr(item, "model_dump")
                            else (
                                item.dict()
                                if hasattr(item, "dict")
                                else (
                                    item.__dict__ if hasattr(item, "__dict__") else item
                                )
                            )
                        )
                        for item in value
                    ]
                elif isinstance(value, dict):
                    # Recursively sanitize nested dicts
                    sanitized[key] = self._sanitize_extra_data(value)
                else:
                    # Basic JSON-serializable types
                    json.dumps(value)  # Test if it's serializable
                    sanitized[key] = value
            except Exception:
                # If all else fails, convert to string
                sanitized[key] = str(value)

        return sanitized
