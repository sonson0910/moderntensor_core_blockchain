#!/usr/bin/env python3
"""
Global Consensus Cycle Beacon for ModernTensor Core

This module provides a global timing beacon that ensures all validators
participate in synchronized consensus cycles, regardless of when they start.

Key Features:
- Global consensus cycle timing (e.g., every 5 minutes)
- Validators can start anytime but must wait for next cycle
- Synchronized consensus windows for all participants
- Flexible validator participation while maintaining timing discipline
"""

import time
import logging
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CyclePhase(Enum):
    """Global consensus cycle phases"""

    TASK_ASSIGNMENT = "task_assignment"  # 0-2 min: Assign tasks to miners
    TASK_EXECUTION = "task_execution"  # 2-4 min: Miners execute tasks
    CONSENSUS_SCORING = "consensus_scoring"  # 4-4.5 min: Validators score & consensus
    METAGRAPH_UPDATE = "metagraph_update"  # 4.5-5 min: Update blockchain state


@dataclass
class CycleConfig:
    """Configuration for global consensus cycles"""

    cycle_duration_minutes: int = 5  # Total cycle time
    task_assignment_minutes: float = 2.0  # Task assignment phase
    task_execution_minutes: float = 2.0  # Task execution phase
    consensus_minutes: float = 0.5  # Consensus scoring phase
    metagraph_update_minutes: float = 0.5  # Metagraph update phase

    # Global epoch start (fixed timestamp for all validators)
    global_epoch_start: int = 1735200000  # Fixed epoch start for synchronization


class GlobalConsensusBeacon:
    """
    Global beacon that provides synchronized consensus cycle timing.

    All validators sync to this global timing regardless of when they start.
    This ensures consensus happens in synchronized windows while maintaining
    flexibility for validators to join at any time.
    """

    def __init__(self, config: Optional[CycleConfig] = None):
        """
        Initialize the global consensus beacon.

        Args:
            config: Cycle configuration (uses default if None)
        """
        self.config = config or CycleConfig()

        logger.info("🌐 Global Consensus Beacon initialized")
        logger.info(f"🌐 Cycle duration: {self.config.cycle_duration_minutes} minutes")
        logger.info(f"🌐 Global epoch start: {self.config.global_epoch_start}")

    def get_current_cycle_number(self) -> int:
        """Get the current global consensus cycle number"""
        current_time = int(time.time())
        cycle_duration_seconds = self.config.cycle_duration_minutes * 60

        cycle_number = (
            current_time - self.config.global_epoch_start
        ) // cycle_duration_seconds
        return max(0, cycle_number)

    def get_cycle_start_time(self, cycle_number: int) -> int:
        """Get the start timestamp for a specific cycle"""
        cycle_duration_seconds = self.config.cycle_duration_minutes * 60
        return self.config.global_epoch_start + (cycle_number * cycle_duration_seconds)

    def get_current_phase_info(self) -> Tuple[int, CyclePhase, Dict]:
        """
        Get current cycle number, phase, and timing information.

        Returns:
            Tuple of (cycle_number, current_phase, phase_info_dict)
        """
        current_time = int(time.time())
        cycle_number = self.get_current_cycle_number()
        cycle_start = self.get_cycle_start_time(cycle_number)
        cycle_elapsed = current_time - cycle_start

        # Convert to minutes for easier calculation
        elapsed_minutes = cycle_elapsed / 60.0

        # Determine current phase based on elapsed time
        if elapsed_minutes < self.config.task_assignment_minutes:
            phase = CyclePhase.TASK_ASSIGNMENT
            phase_elapsed = elapsed_minutes
            phase_duration = self.config.task_assignment_minutes

        elif elapsed_minutes < (
            self.config.task_assignment_minutes + self.config.task_execution_minutes
        ):
            phase = CyclePhase.TASK_EXECUTION
            phase_elapsed = elapsed_minutes - self.config.task_assignment_minutes
            phase_duration = self.config.task_execution_minutes

        elif elapsed_minutes < (
            self.config.task_assignment_minutes
            + self.config.task_execution_minutes
            + self.config.consensus_minutes
        ):
            phase = CyclePhase.CONSENSUS_SCORING
            phase_elapsed = (
                elapsed_minutes
                - self.config.task_assignment_minutes
                - self.config.task_execution_minutes
            )
            phase_duration = self.config.consensus_minutes

        else:
            phase = CyclePhase.METAGRAPH_UPDATE
            phase_elapsed = (
                elapsed_minutes
                - self.config.task_assignment_minutes
                - self.config.task_execution_minutes
                - self.config.consensus_minutes
            )
            phase_duration = self.config.metagraph_update_minutes

        # Calculate timing info
        phase_info = {
            "cycle_start_time": cycle_start,
            "cycle_elapsed_seconds": cycle_elapsed,
            "phase_elapsed_seconds": phase_elapsed * 60,
            "phase_duration_seconds": phase_duration * 60,
            "phase_remaining_seconds": (phase_duration - phase_elapsed) * 60,
            "next_cycle_start": cycle_start + (self.config.cycle_duration_minutes * 60),
            "can_join_consensus": phase
            in [CyclePhase.TASK_ASSIGNMENT, CyclePhase.TASK_EXECUTION],
        }

        return cycle_number, phase, phase_info

    def get_next_consensus_window(self) -> Tuple[int, int]:
        """
        Get the next consensus scoring window timing.

        Returns:
            Tuple of (consensus_start_time, consensus_end_time)
        """
        cycle_number, current_phase, phase_info = self.get_current_phase_info()

        # If we're already in or past consensus phase, get next cycle
        if current_phase in [CyclePhase.CONSENSUS_SCORING, CyclePhase.METAGRAPH_UPDATE]:
            cycle_number += 1

        cycle_start = self.get_cycle_start_time(cycle_number)
        consensus_start = cycle_start + int(
            (self.config.task_assignment_minutes + self.config.task_execution_minutes)
            * 60
        )
        consensus_end = consensus_start + int(self.config.consensus_minutes * 60)

        return consensus_start, consensus_end

    def wait_for_next_consensus_phase(self) -> Tuple[int, int, int]:
        """
        Calculate how long to wait until the next consensus phase.

        Returns:
            Tuple of (cycle_number, consensus_start_time, wait_seconds)
        """
        cycle_number, current_phase, phase_info = self.get_current_phase_info()
        current_time = int(time.time())

        if current_phase == CyclePhase.CONSENSUS_SCORING:
            # In consensus phase - check if there's still time left
            cycle_start = phase_info["cycle_start_time"]
            consensus_end = cycle_start + int(
                (
                    self.config.task_assignment_minutes
                    + self.config.task_execution_minutes
                    + self.config.consensus_minutes
                )
                * 60
            )

            if current_time < consensus_end:
                # Still time in current consensus
                consensus_start = current_time
                wait_seconds = 0
            else:
                # Current consensus ended, wait for next cycle
                cycle_number += 1
                cycle_start = self.get_cycle_start_time(cycle_number)
                consensus_start = cycle_start + int(
                    (
                        self.config.task_assignment_minutes
                        + self.config.task_execution_minutes
                    )
                    * 60
                )
                wait_seconds = max(0, consensus_start - current_time)

        elif current_phase in [CyclePhase.TASK_ASSIGNMENT, CyclePhase.TASK_EXECUTION]:
            # Wait for consensus phase in current cycle
            cycle_start = phase_info["cycle_start_time"]
            consensus_start = cycle_start + int(
                (
                    self.config.task_assignment_minutes
                    + self.config.task_execution_minutes
                )
                * 60
            )
            wait_seconds = max(0, consensus_start - current_time)

        else:
            # In metagraph update phase, wait for next cycle's consensus
            cycle_number += 1
            cycle_start = self.get_cycle_start_time(cycle_number)
            consensus_start = cycle_start + int(
                (
                    self.config.task_assignment_minutes
                    + self.config.task_execution_minutes
                )
                * 60
            )
            wait_seconds = max(0, consensus_start - current_time)

        return cycle_number, consensus_start, wait_seconds

    def is_consensus_window_active(self) -> bool:
        """Check if the current time is within a consensus scoring window"""
        _, current_phase, _ = self.get_current_phase_info()
        return current_phase == CyclePhase.CONSENSUS_SCORING

    def get_cycle_summary(self) -> Dict:
        """Get a comprehensive summary of current cycle status"""
        cycle_number, current_phase, phase_info = self.get_current_phase_info()
        consensus_start, consensus_end = self.get_next_consensus_window()
        next_cycle_num, next_consensus_start, wait_seconds = (
            self.wait_for_next_consensus_phase()
        )

        return {
            "current_cycle": cycle_number,
            "current_phase": current_phase.value,
            "phase_remaining_seconds": phase_info["phase_remaining_seconds"],
            "next_consensus_cycle": next_cycle_num,
            "next_consensus_start": next_consensus_start,
            "wait_for_consensus_seconds": wait_seconds,
            "is_consensus_active": self.is_consensus_window_active(),
            "can_join_current_cycle": phase_info["can_join_consensus"],
            "cycle_start_time": phase_info["cycle_start_time"],
            "next_cycle_start": phase_info["next_cycle_start"],
        }


# Global beacon instance - all validators use this
global_beacon = GlobalConsensusBeacon()


def get_global_beacon() -> GlobalConsensusBeacon:
    """Get the global consensus beacon instance"""
    return global_beacon


def log_cycle_status(validator_uid: str = "validator"):
    """Log current cycle status for debugging"""
    beacon = get_global_beacon()
    summary = beacon.get_cycle_summary()

    logger.info(f"🌐 {validator_uid} Global Cycle Status:")
    logger.info(f"   📊 Current cycle: {summary['current_cycle']}")
    logger.info(f"   📊 Current phase: {summary['current_phase']}")
    logger.info(f"   📊 Phase remaining: {summary['phase_remaining_seconds']:.1f}s")
    logger.info(f"   📊 Next consensus cycle: {summary['next_consensus_cycle']}")
    logger.info(
        f"   📊 Wait for consensus: {summary['wait_for_consensus_seconds']:.1f}s"
    )
    logger.info(f"   📊 Consensus active: {summary['is_consensus_active']}")
    logger.info(f"   📊 Can join current: {summary['can_join_current_cycle']}")
