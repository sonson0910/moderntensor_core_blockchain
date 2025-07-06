#!/usr/bin/env python3
"""
Slot Coordinator for Synchronized Validator Consensus

This module provides SlotCoordinator class that ensures all validators:
- Stop task assignment at synchronized cutoff times
- Coordinate phase transitions (task assignment → execution → consensus → metagraph update)
- Perform P2P consensus with proper waiting mechanisms
- Update metagraph together after reaching consensus

Key Features:
- File-based coordination using JSON files
- Majority consensus (2/3 validators)
- Precise timing based on blockchain epochs
- Automatic cleanup of old coordination files
"""

import asyncio
import time
import json
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Constants
EPOCH_START = 1735689600  # Jan 1, 2025 00:00:00 UTC
EXPECTED_VALIDATORS = ['validator_1', 'validator_2', 'validator_3']
MAJORITY_THRESHOLD = 2  # Need 2 out of 3 validators
CONSENSUS_CHECK_INTERVAL = 5  # Check every 5 seconds


class SlotPhase(Enum):
    """Phases within each consensus slot"""
    TASK_ASSIGNMENT = "task_assignment"
    TASK_EXECUTION = "task_execution"
    CONSENSUS_SCORING = "consensus_scoring"
    METAGRAPH_UPDATE = "metagraph_update"


@dataclass
class SlotConfig:
    """Configuration for slot timing and phase boundaries"""
    slot_duration_minutes: int = 15  # Total slot duration
    task_assignment_minutes: int = 10  # 0-10min: Task assignment
    task_execution_minutes: int = 2   # 10-12min: Task execution
    consensus_minutes: int = 2        # 12-14min: Consensus scoring
    metagraph_update_minutes: int = 1 # 14-15min: Metagraph update
    
    def get_phase_boundaries(self) -> Dict[SlotPhase, Tuple[int, int]]:
        """Get start/end minutes for each phase"""
        return {
            SlotPhase.TASK_ASSIGNMENT: (0, self.task_assignment_minutes),
            SlotPhase.TASK_EXECUTION: (
                self.task_assignment_minutes, 
                self.task_assignment_minutes + self.task_execution_minutes
            ),
            SlotPhase.CONSENSUS_SCORING: (
                self.task_assignment_minutes + self.task_execution_minutes,
                self.slot_duration_minutes - self.metagraph_update_minutes
            ),
            SlotPhase.METAGRAPH_UPDATE: (
                self.slot_duration_minutes - self.metagraph_update_minutes, 
                self.slot_duration_minutes
            )
        }


class SlotCoordinator:
    """
    Coordinates slot-based consensus between validators
    
    This class provides the main coordination mechanism for ensuring validators
    synchronize their phase transitions and consensus activities.
    """
    
    def __init__(self, validator_uid: str, coordination_dir: str = "slot_coordination"):
        """
        Initialize SlotCoordinator
        
        Args:
            validator_uid: Unique identifier for this validator
            coordination_dir: Directory for coordination files
        """
        self.validator_uid = validator_uid
        self.coordination_dir = Path(coordination_dir)
        self.coordination_dir.mkdir(exist_ok=True)
        self.slot_config = SlotConfig()
        
        logger.debug(f"SlotCoordinator initialized for {validator_uid}")
        
    def get_current_blockchain_slot(self) -> int:
        """Get current blockchain slot number based on timestamp"""
        current_time = int(time.time())
        slot_duration_seconds = self.slot_config.slot_duration_minutes * 60
        return (current_time - EPOCH_START) // slot_duration_seconds
    
    def get_slot_phase(self, slot_number: int) -> Tuple[SlotPhase, int, int]:
        """
        Get current phase within a slot and time remaining
        
        Args:
            slot_number: The slot number to check
            
        Returns:
            Tuple of (phase, minutes_into_slot, minutes_remaining_in_phase)
        """
        current_time = int(time.time())
        slot_duration_seconds = self.slot_config.slot_duration_minutes * 60
        
        slot_start_time = EPOCH_START + (slot_number * slot_duration_seconds)
        minutes_into_slot = (current_time - slot_start_time) // 60
        
        boundaries = self.slot_config.get_phase_boundaries()
        
        for phase, (start_min, end_min) in boundaries.items():
            if start_min <= minutes_into_slot < end_min:
                minutes_remaining = end_min - minutes_into_slot
                return phase, minutes_into_slot, minutes_remaining
        
        # Default to task assignment if outside boundaries
        return SlotPhase.TASK_ASSIGNMENT, minutes_into_slot, 0
    
    def _get_time_until_next_phase(self, slot_number: int) -> Tuple[SlotPhase, int]:
        """Get next phase and seconds until it starts"""
        current_time = int(time.time())
        slot_duration_seconds = self.slot_config.slot_duration_minutes * 60
        
        slot_start_time = EPOCH_START + (slot_number * slot_duration_seconds)
        minutes_into_slot = (current_time - slot_start_time) // 60
        
        boundaries = self.slot_config.get_phase_boundaries()
        
        for phase, (start_min, end_min) in boundaries.items():
            if minutes_into_slot < start_min:
                # This phase hasn't started yet
                time_until_phase = (slot_start_time + start_min * 60) - current_time
                return phase, time_until_phase
        
        # All phases passed, next phase is task assignment of next slot
        next_slot_start = slot_start_time + slot_duration_seconds
        time_until_next_slot = next_slot_start - current_time
        return SlotPhase.TASK_ASSIGNMENT, time_until_next_slot
    
    async def register_phase_entry(self, slot: int, phase: SlotPhase, extra_data: Dict = None):
        """
        Register that this validator has entered a specific phase
        
        Args:
            slot: Slot number
            phase: Phase being entered
            extra_data: Optional additional data to store
        """
        phase_file = self.coordination_dir / f"slot_{slot}_{phase.value}_{self.validator_uid}.json"
        
        phase_data = {
            'validator_uid': self.validator_uid,
            'slot': slot,
            'phase': phase.value,
            'timestamp': time.time(),
            'extra_data': extra_data or {}
        }
        
        try:
            with open(phase_file, 'w') as f:
                json.dump(phase_data, f, indent=2)
            logger.info(f"✅ [V:{self.validator_uid}] Registered entry to {phase.value} phase of slot {slot}")
        except Exception as e:
            logger.error(f"❌ [V:{self.validator_uid}] Failed to register phase entry: {e}")
            raise
    
    async def wait_for_phase_consensus(self, slot: int, phase: SlotPhase, timeout: int = 120) -> List[str]:
        """
        Wait for majority of validators to enter the same phase
        
        Args:
            slot: Slot number
            phase: Phase to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            List of validator UIDs that are ready
        """
        start_time = time.time()
        logger.info(f"⏳ [V:{self.validator_uid}] Waiting for validators to enter {phase.value} phase of slot {slot}")
        
        while time.time() - start_time < timeout:
            ready_validators = self._get_ready_validators(slot, phase)
            
            logger.debug(f"🔍 [V:{self.validator_uid}] Slot {slot} {phase.value}: "
                        f"{len(ready_validators)}/{len(EXPECTED_VALIDATORS)} validators ready: {ready_validators}")
            
            # Need majority for consensus
            if len(ready_validators) >= MAJORITY_THRESHOLD:
                logger.info(f"✅ [V:{self.validator_uid}] Sufficient validators in {phase.value} phase: {ready_validators}")
                return ready_validators
            
            await asyncio.sleep(CONSENSUS_CHECK_INTERVAL)
        
        logger.warning(f"⚠️ [V:{self.validator_uid}] Timeout waiting for {phase.value} phase. "
                      f"Only {len(ready_validators)} ready")
        return ready_validators
    
    def _get_ready_validators(self, slot: int, phase: SlotPhase) -> List[str]:
        """Get list of validators ready for given slot and phase"""
        ready_validators = []
        
        for validator_uid in EXPECTED_VALIDATORS:
            phase_file = self.coordination_dir / f"slot_{slot}_{phase.value}_{validator_uid}.json"
            if phase_file.exists():
                try:
                    with open(phase_file, 'r') as f:
                        data = json.load(f)
                        if data.get('slot') == slot and data.get('phase') == phase.value:
                            ready_validators.append(validator_uid)
                except Exception as e:
                    logger.debug(f"Error reading phase file {phase_file}: {e}")
        
        return ready_validators
    
    async def synchronized_phase_transition(self, slot: int, current_phase: SlotPhase, next_phase: SlotPhase) -> bool:
        """
        Coordinate synchronized transition from current phase to next phase
        
        Args:
            slot: Slot number
            current_phase: Current phase
            next_phase: Phase to transition to
            
        Returns:
            True if transition was successful
        """
        logger.info(f"🔄 [V:{self.validator_uid}] Initiating synchronized transition: "
                   f"{current_phase.value} → {next_phase.value}")
        
        try:
            # Step 1: Wait for all validators to finish current phase
            await self.wait_for_phase_consensus(slot, current_phase)
            
            # Step 2: Wait for the correct time to start next phase
            next_phase_start, seconds_until = self._get_time_until_next_phase(slot)
            
            if next_phase_start == next_phase and seconds_until > 0:
                logger.info(f"⏰ [V:{self.validator_uid}] Waiting {seconds_until}s for {next_phase.value} phase")
                await asyncio.sleep(seconds_until)
            
            # Step 3: Register entry to next phase
            await self.register_phase_entry(slot, next_phase)
            
            # Step 4: Wait for other validators to join next phase
            ready_validators = await self.wait_for_phase_consensus(slot, next_phase)
            
            if len(ready_validators) >= MAJORITY_THRESHOLD:
                logger.info(f"✅ [V:{self.validator_uid}] Synchronized transition completed: "
                           f"{current_phase.value} → {next_phase.value}")
                return True
            else:
                logger.warning(f"⚠️ [V:{self.validator_uid}] Failed synchronized transition: insufficient validators")
                return False
                
        except Exception as e:
            logger.error(f"❌ [V:{self.validator_uid}] Error in synchronized transition: {e}")
            return False
    
    async def enforce_task_assignment_cutoff(self, slot: int) -> bool:
        """
        Ensure all validators stop task assignment at the same time
        
        Args:
            slot: Slot number
            
        Returns:
            True if cutoff was enforced successfully
        """
        logger.info(f"🛑 [V:{self.validator_uid}] Enforcing task assignment cutoff for slot {slot}")
        
        try:
            # Get current phase
            current_phase, minutes_into_slot, minutes_remaining = self.get_slot_phase(slot)
            
            if current_phase != SlotPhase.TASK_ASSIGNMENT:
                logger.info(f"✅ [V:{self.validator_uid}] Already past task assignment phase")
                return True
            
            # Calculate exact cutoff time
            slot_start_time = EPOCH_START + (slot * self.slot_config.slot_duration_minutes * 60)
            cutoff_time = slot_start_time + (self.slot_config.task_assignment_minutes * 60)
            current_time = int(time.time())
            
            if current_time < cutoff_time:
                wait_time = cutoff_time - current_time
                logger.info(f"⏰ [V:{self.validator_uid}] Waiting {wait_time}s for task assignment cutoff")
                await asyncio.sleep(wait_time)
            
            # Register that we've stopped task assignment
            await self.register_phase_entry(slot, SlotPhase.TASK_EXECUTION, {'task_assignment_stopped': True})
            
            logger.info(f"✅ [V:{self.validator_uid}] Task assignment cutoff enforced for slot {slot}")
            return True
            
        except Exception as e:
            logger.error(f"❌ [V:{self.validator_uid}] Error enforcing task assignment cutoff: {e}")
            return False
    
    async def coordinate_consensus_round(self, slot: int, local_scores: Dict[str, float]) -> Dict[str, float]:
        """
        Coordinate consensus round with other validators
        
        Args:
            slot: Slot number
            local_scores: This validator's local scores
            
        Returns:
            Dictionary of consensus scores (averaged across validators)
        """
        logger.info(f"🤝 [V:{self.validator_uid}] Starting consensus coordination for slot {slot}")
        
        try:
            # Step 1: Register consensus readiness with scores
            await self.register_phase_entry(slot, SlotPhase.CONSENSUS_SCORING, {'scores': local_scores})
            
            # Step 2: Wait for other validators to be ready
            ready_validators = await self.wait_for_phase_consensus(slot, SlotPhase.CONSENSUS_SCORING)
            
            if len(ready_validators) < MAJORITY_THRESHOLD:
                logger.warning(f"⚠️ [V:{self.validator_uid}] Insufficient validators for consensus: {len(ready_validators)}")
                return {}
            
            # Step 3: Calculate consensus scores
            consensus_scores = self._calculate_consensus_scores(slot, ready_validators)
            
            logger.info(f"✅ [V:{self.validator_uid}] Consensus completed for slot {slot}: {len(consensus_scores)} scores")
            return consensus_scores
            
        except Exception as e:
            logger.error(f"❌ [V:{self.validator_uid}] Error in consensus coordination: {e}")
            return {}
    
    def _calculate_consensus_scores(self, slot: int, participating_validators: List[str]) -> Dict[str, float]:
        """Calculate consensus scores from all participating validators"""
        all_scores = {}
        
        # Collect scores from all participating validators
        for validator_uid in participating_validators:
            score_file = self.coordination_dir / f"slot_{slot}_consensus_scoring_{validator_uid}.json"
            if score_file.exists():
                try:
                    with open(score_file, 'r') as f:
                        data = json.load(f)
                        scores = data.get('extra_data', {}).get('scores', {})
                        
                        # Aggregate scores per miner
                        for miner_uid, score in scores.items():
                            if miner_uid not in all_scores:
                                all_scores[miner_uid] = []
                            all_scores[miner_uid].append(score)
                            
                except Exception as e:
                    logger.error(f"Error reading scores from {validator_uid}: {e}")
        
        # Calculate consensus (simple average)
        consensus_scores = {}
        for miner_uid, score_list in all_scores.items():
            if score_list:
                consensus_score = sum(score_list) / len(score_list)
                consensus_scores[miner_uid] = consensus_score
                logger.info(f"📊 [V:{self.validator_uid}] Miner {miner_uid}: "
                           f"{consensus_score:.4f} (from {len(score_list)} validators)")
        
        return consensus_scores
    
    def cleanup_old_coordination_files(self, current_slot: int, keep_slots: int = 5):
        """
        Clean up old coordination files to prevent directory bloat
        
        Args:
            current_slot: Current slot number
            keep_slots: Number of recent slots to keep files for
        """
        try:
            cleaned_count = 0
            for file_path in self.coordination_dir.glob("slot_*.json"):
                try:
                    # Extract slot number from filename
                    parts = file_path.name.split('_')
                    if len(parts) >= 2:
                        slot_num = int(parts[1])
                        if slot_num < current_slot - keep_slots:
                            file_path.unlink()
                            cleaned_count += 1
                except (ValueError, IndexError):
                    continue
            
            if cleaned_count > 0:
                logger.debug(f"Cleaned up {cleaned_count} old coordination files")
                
        except Exception as e:
            logger.debug(f"Error cleaning up coordination files: {e}") 