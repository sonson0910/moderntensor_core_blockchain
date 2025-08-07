#!/usr/bin/env python3
"""
Refactored ValidatorNode for Core Blockchain

This is the main ValidatorNode class that orchestrates all validator operations
using the modular architecture:
- ValidatorNodeCore: Core functionality and state management
- ValidatorNodeTasks: Task creation and management
- ValidatorNodeConsensus: Consensus scoring and coordination
- ValidatorNodeNetwork: Network communication and API endpoints

The refactored node provides the same functionality as the original but with
better organization, maintainability, and testability.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any

from web3 import Web3
from eth_account import Account

from ..core.datatypes import ValidatorInfo, MinerInfo, MinerResult, ValidatorScore
from .validator_node_core import ValidatorNodeCore
from .validator_node_tasks import ValidatorNodeTasks
from .validator_node_consensus import ValidatorNodeConsensus
from .validator_node_network import ValidatorNodeNetwork
from .slot_coordinator import SlotPhase
from .flexible_slot_coordinator import (
    FlexibleSlotCoordinator,
    FlexibleSlotPhase,
    get_fixed_epoch_start,
)
from ..config.config_loader import get_config

logger = logging.getLogger(__name__)


class ValidatorNode:
    """
    Refactored ValidatorNode with modular architecture for Core blockchain.

    This class acts as the main orchestrator that coordinates between:
    - Core: State management and basic operations
    - Tasks: Task assignment and tracking
    - Consensus: Scoring and coordination
    - Network: P2P communication and API endpoints
    """

    def __init__(
        self,
        validator_info: ValidatorInfo,
        core_client: Web3,
        account: Account,
        contract_address: str,
        state_file: str = "validator_state.json",
        consensus_mode: str = "flexible",  # Flexible mode with synchronized cutoffs
        batch_wait_time: float = 30.0,
        api_port: Optional[int] = None,
        enable_flexible_consensus: bool = True,  # Enable flexible mode with synchronized cutoffs
        flexible_mode: str = "balanced",
    ):
        """
        Initialize the refactored ValidatorNode.

        Args:
            validator_info: Information about this validator
            core_client: Core blockchain Web3 client
            account: Core blockchain account for transactions
            contract_address: ModernTensor contract address
            state_file: Path to state persistence file
            consensus_mode: "continuous" or "sequential"
            batch_wait_time: Wait time between batches
            api_port: Port for API server (optional, extracted from validator_info if not provided)
        """
        # Extract port from validator_info if not provided
        if api_port is None and hasattr(validator_info, "api_endpoint"):
            try:
                import re

                endpoint = validator_info.api_endpoint
                port_match = re.search(r":(\d+)", endpoint) if endpoint else None
                api_port = int(port_match.group(1)) if port_match else None
            except (AttributeError, ValueError):
                api_port = None

        # Initialize core module
        self.core = ValidatorNodeCore(
            validator_info=validator_info,
            core_client=core_client,
            account=account,
            contract_address=contract_address,
            state_file=state_file,
            consensus_mode=consensus_mode,
            batch_wait_time=batch_wait_time,
            api_port=api_port,
        )

        # Initialize functional modules
        self.tasks = ValidatorNodeTasks(self.core)
        self.consensus = ValidatorNodeConsensus(self.core)
        self.network = ValidatorNodeNetwork(self.core)

        # Cross-reference tasks module in core for consensus access
        self.core.tasks = self.tasks
        self.core.validator_instance = self

        # Aliases for backward compatibility
        self.uid_prefix = self.core.uid_prefix
        self.info = self.core.info

        # Background tasks
        self.main_task = None
        self.health_monitor_task = None

        # === FLEXIBLE CONSENSUS INTEGRATION ===
        self.enable_flexible_consensus = enable_flexible_consensus
        self.flexible_mode = flexible_mode
        self.flexible_consensus_enabled = False

        if enable_flexible_consensus:
            try:
                logger.info(f"🔄 {self.uid_prefix} Initializing Flexible Consensus...")
                # Correctly initialize and assign the Slot Coordinator
                self.core.slot_coordinator = FlexibleSlotCoordinator(
                    validator_uid=self.core.info.uid,
                    # coordination_dir can be customized if needed, default is fine
                )
                logger.info(f"   - FlexibleSlotCoordinator initialized and assigned.")

                # Now, enable the mode in the consensus handler
                self.consensus.enable_flexible_mode()
                self.flexible_consensus_enabled = True
                logger.info(f"   - Flexible mode enabled in consensus handler.")

            except Exception as e:
                logger.error(
                    f"❌ {self.uid_prefix} Failed to initialize flexible consensus: {e}",
                    exc_info=True,
                )
                self.flexible_consensus_enabled = False

        logger.info(
            f"✅ {self.uid_prefix} Refactored ValidatorNode initialized successfully"
            f" (Flexible Consensus: {'✅' if self.flexible_consensus_enabled else '❌'})"
        )

    # === Core Properties (Backward Compatibility) ===

    @property
    def current_cycle(self) -> int:
        """Get current cycle number."""
        return self.core.current_cycle

    @property
    def miners_info(self) -> Dict[str, MinerInfo]:
        """Get miners information."""
        return self.core.miners_info

    @property
    def validators_info(self) -> Dict[str, ValidatorInfo]:
        """Get validators information."""
        return self.core.validators_info

    @property
    def results_buffer(self) -> Dict[str, MinerResult]:
        """Get results buffer."""
        return self.core.results_buffer

    @property
    def tasks_sent(self) -> Dict[str, Any]:
        """Get tasks sent tracking."""
        return self.core.tasks_sent

    # === Main Operation Methods ===

    async def start(self, api_port: Optional[int] = None):
        """
        Start the validator node with all services.

        Args:
            api_port: Port for API server (optional)
        """
        logger.info(f"{self.uid_prefix} Starting refactored ValidatorNode")
        logger.debug(
            f"{self.uid_prefix} start() received api_port parameter: {api_port}"
        )

        try:
            # Load initial metagraph data
            await self.core.load_metagraph_data()

            # Start network services
            logger.debug(
                f"{self.uid_prefix} Calling network.start_api_server with api_port: {api_port}"
            )
            await self.network.start_api_server(api_port)

            # Start health monitoring
            self.health_monitor_task = asyncio.create_task(
                self.network.start_health_monitor()
            )

            # Start main operation loop
            self.main_task = asyncio.create_task(self._main_operation_loop())

            logger.info(f"{self.uid_prefix} ValidatorNode started successfully")

        except Exception as e:
            logger.error(f"{self.uid_prefix} Error starting ValidatorNode: {e}")
            await self.shutdown()
            raise

    async def shutdown(self):
        """Shutdown the validator node gracefully."""
        logger.info(f"{self.uid_prefix} Shutting down ValidatorNode")

        # Cancel background tasks
        if self.main_task:
            self.main_task.cancel()

        if self.health_monitor_task:
            self.health_monitor_task.cancel()

        # Shutdown network services
        await self.network.shutdown()

        # Save state
        self.core.save_state()

        logger.info(f"{self.uid_prefix} ValidatorNode shutdown complete")

    async def _main_operation_loop(self):
        """Main operation loop for the validator node."""
        logger.info(f"{self.uid_prefix} Starting main operation loop")

        # FLEXIBLE MODE WITH SYNCHRONIZED CUTOFFS
        if self.flexible_consensus_enabled:
            logger.info(
                f"{self.uid_prefix} Using flexible mode with synchronized cutoffs"
            )
            await self._flexible_consensus_loop()
        else:
            await self._traditional_slot_loop()

    async def _flexible_consensus_loop(self):
        """Flexible consensus operation loop with synchronized cutoffs."""
        # 🔥 CYBERPUNK CONSENSUS STARTUP 🔥
        from rich.console import Console

        cyber_console = Console(force_terminal=True, color_system="truecolor")
        cyber_console.print(
            f"🔥 [bold bright_cyan]{self.uid_prefix}[/] [bright_green]NEURAL CONSENSUS MATRIX:[/] [bright_yellow]ACTIVATED[/] ⚡"
        )
        logger.info(
            f"{self.uid_prefix} Starting flexible consensus loop with synchronized cutoffs"
        )

        last_processed_slot = -1
        last_processed_phase = None
        task_assignment_completed_slots = (
            set()
        )  # Track slots where task assignment was completed

        while True:
            try:
                # Get current slot and phase from the flexible coordinator
                current_slot, current_phase, phase_info = (
                    self.core.slot_coordinator.get_current_slot_and_phase()
                )

                # Determine if we should process this slot/phase combination
                should_process = False

                if current_slot > last_processed_slot:
                    # New slot - always process
                    should_process = True
                    logger.info(
                        f"🔄 {self.uid_prefix} New slot detected: {current_slot} (last: {last_processed_slot})"
                    )
                elif (
                    current_slot == last_processed_slot
                    and current_phase != last_processed_phase
                ):
                    # Same slot but different phase - process if we haven't done this phase
                    should_process = True
                    logger.info(
                        f"🔄 {self.uid_prefix} Phase transition in slot {current_slot}: {last_processed_phase} → {current_phase.value}"
                    )

                    # 🔥 CYBERPUNK UI: Phase Transition
                    try:
                        from ..cli.cyberpunk_ui_extended import (
                            print_cyberpunk_phase_transition,
                        )

                        from_phase = (
                            last_processed_phase.value
                            if last_processed_phase
                            else "startup"
                        )
                        print_cyberpunk_phase_transition(
                            from_phase, current_phase.value, current_slot
                        )
                    except ImportError:
                        pass
                elif (
                    current_slot == last_processed_slot
                    and current_phase == last_processed_phase
                ):
                    # Same slot and same phase - check if enough time has passed to force progression
                    # INFINITE LOOP FIX: Add time-based progression check
                    time_in_phase = self._get_time_in_current_phase()
                    min_phase_duration = self._get_min_phase_duration(current_phase)

                    if time_in_phase >= (
                        min_phase_duration + 10
                    ):  # 10s buffer for progression
                        # Force progression if we've been in phase too long
                        should_process = True
                        logger.info(
                            f"🚀 {self.uid_prefix} FORCING progression: {time_in_phase:.1f}s in {current_phase.value} (min: {min_phase_duration}s)"
                        )
                    else:
                        # Normal case - already processed, don't repeat
                        should_process = False
                        logger.debug(
                            f"⏭️ {self.uid_prefix} Already processed slot {current_slot} phase {current_phase.value}, skipping"
                        )

                if should_process:
                    logger.info(
                        f"▶️ {self.uid_prefix} Processing slot {current_slot} in phase {current_phase.value}"
                    )

                    # Handle phase-specific operations - SIMPLIFIED 3 PHASES
                    if current_phase == FlexibleSlotPhase.TASK_ASSIGNMENT:
                        # Prevent duplicate task assignments for same slot
                        if current_slot not in task_assignment_completed_slots:
                            await self._handle_task_assignment_phase(current_slot)
                            # Task execution is now included in task assignment phase
                            await self._handle_task_execution_phase(current_slot)
                            task_assignment_completed_slots.add(current_slot)
                            logger.info(
                                f"✅ {self.uid_prefix} Task assignment + execution completed for slot {current_slot}"
                            )
                        else:
                            logger.debug(
                                f"⏭️ {self.uid_prefix} Task assignment + execution already completed for slot {current_slot}, skipping"
                            )

                    elif current_phase == FlexibleSlotPhase.CONSENSUS_SCORING:
                        result = await self._handle_consensus_scoring_phase(
                            current_slot
                        )
                        if result and result.get("skipped"):
                            logger.info(
                                f"⏭️ {self.uid_prefix} Skipped consensus for slot {current_slot} ({result.get('reason')})"
                            )
                    elif current_phase == FlexibleSlotPhase.METAGRAPH_UPDATE:
                        # Prevent reprocessing same slot in metagraph phase
                        if (
                            current_slot == last_processed_slot
                            and last_processed_phase
                            == FlexibleSlotPhase.METAGRAPH_UPDATE
                        ):
                            logger.debug(
                                f"⏭️ {self.uid_prefix} Skipping already completed metagraph phase for slot {current_slot}"
                            )
                            await asyncio.sleep(5)  # Wait for next slot
                            continue

                        await self._handle_metagraph_update_phase(current_slot)

                        # Clean up old task assignment tracking when slot is fully completed
                        old_slots = {
                            s
                            for s in task_assignment_completed_slots
                            if s < current_slot - 2
                        }
                        task_assignment_completed_slots -= old_slots
                        if old_slots:
                            logger.debug(
                                f"🧹 {self.uid_prefix} Cleaned up task assignment tracking for old slots: {old_slots}"
                            )

                    # Update tracking - update slot tracking IMMEDIATELY to prevent infinite loops
                    if current_phase == FlexibleSlotPhase.METAGRAPH_UPDATE:
                        # Final phase completed - WAIT FOR NEXT SLOT TIME-BASED PROGRESSION
                        logger.info(
                            f"✅ {self.uid_prefix} Completed ALL phases for slot {current_slot}"
                        )
                        logger.info(
                            f"⏰ {self.uid_prefix} Waiting for natural time progression to next slot..."
                        )
                        # Mark this slot as fully completed
                        last_processed_slot = current_slot
                        last_processed_phase = FlexibleSlotPhase.METAGRAPH_UPDATE
                        # Let natural timing take over - wait for coordinator to detect next slot
                        await asyncio.sleep(
                            10
                        )  # Wait for time progression instead of forcing
                    else:
                        logger.info(
                            f"🔄 {self.uid_prefix} Completed phase {current_phase.value} for slot {current_slot}"
                        )
                        last_processed_phase = current_phase
                        last_processed_slot = current_slot

                else:
                    # Already processed this slot/phase combination
                    logger.debug(
                        f"⏳ {self.uid_prefix} Waiting for progression (slot: {current_slot}, phase: {current_phase.value}, last_slot: {last_processed_slot}, last_phase: {last_processed_phase})"
                    )

                # Wait before next cycle
                await asyncio.sleep(5)  # Reduced sleep for better responsiveness

            except Exception as e:
                logger.error(
                    f"{self.uid_prefix} Error in flexible consensus loop: {e}",
                    exc_info=True,
                )
                await asyncio.sleep(30)  # Wait before retrying

    def _get_time_in_current_phase(self) -> float:
        """Get seconds elapsed in current phase to prevent infinite loops"""
        if not hasattr(self.core, "slot_coordinator"):
            return 0.0

        try:
            current_slot, current_phase, metadata = (
                self.core.slot_coordinator.get_current_slot_and_phase()
            )

            # Get phase timing info from coordinator
            slot_duration = (
                self.core.slot_coordinator.slot_config.slot_duration_minutes * 60
            )
            task_duration = (
                self.core.slot_coordinator.slot_config.min_task_assignment_seconds
            )
            exec_duration = (
                self.core.slot_coordinator.slot_config.min_task_execution_seconds
            )
            cons_duration = self.core.slot_coordinator.slot_config.min_consensus_seconds

            # Use FIXED EPOCH START if not already set
            if hasattr(self.core.slot_coordinator, "_epoch_start"):
                epoch_start = self.core.slot_coordinator._epoch_start
            else:
                epoch_start = get_fixed_epoch_start()
                self.core.slot_coordinator._epoch_start = epoch_start
            slot_start = epoch_start + (current_slot * slot_duration)
            time_in_slot = time.time() - slot_start

            # Calculate time in current phase - SIMPLIFIED 3 PHASES
            if current_phase.value == "task_assignment":
                return time_in_slot  # Includes execution time
            elif current_phase.value == "consensus_scoring":
                return max(0, time_in_slot - task_duration)  # After task assignment
            elif current_phase.value == "metagraph_update":
                return max(
                    0, time_in_slot - task_duration - cons_duration
                )  # After consensus
            else:
                return time_in_slot

        except Exception:
            return 0.0

    def _get_min_phase_duration(self, phase) -> int:
        """Get minimum duration for a phase"""
        if not hasattr(self.core, "slot_coordinator"):
            return 30  # Default 30s

        config = self.core.slot_coordinator.slot_config

        if phase.value == "task_assignment":
            return config.min_task_assignment_seconds  # Includes execution
        elif phase.value == "consensus_scoring":
            return config.min_consensus_seconds
        elif phase.value == "metagraph_update":
            return config.min_metagraph_update_seconds
        else:
            return 30  # Default

    async def _traditional_slot_loop(self):
        """Traditional slot-based operation loop."""
        logger.info(f"{self.uid_prefix} Starting traditional slot-based loop")

        while True:
            try:
                # Get current slot and phase
                current_slot = self.core.get_current_blockchain_slot()
                phase, time_in_phase, time_remaining = self.core.get_slot_phase(
                    current_slot
                )

                logger.debug(
                    f"{self.uid_prefix} Slot {current_slot}, Phase: {phase}, "
                    f"Time in phase: {time_in_phase}s, Remaining: {time_remaining}s"
                )

                # Handle phase-specific operations
                if phase == SlotPhase.TASK_ASSIGNMENT:
                    await self._handle_task_assignment_phase(current_slot)
                elif phase == SlotPhase.TASK_EXECUTION:
                    await self._handle_task_execution_phase(current_slot)
                elif phase == SlotPhase.CONSENSUS_SCORING:
                    result = await self._handle_consensus_scoring_phase(current_slot)
                    if result and result.get("skipped"):
                        logger.info(
                            f"⏭️ {self.uid_prefix} Skipped consensus for slot {current_slot} ({result.get('reason')})"
                        )
                        continue  # Skip to next iteration
                elif phase == SlotPhase.METAGRAPH_UPDATE:
                    await self._handle_metagraph_update_phase(current_slot)

                # Wait before next iteration
                await asyncio.sleep(10)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"{self.uid_prefix} Error in main operation loop: {e}")
                await asyncio.sleep(30)  # Wait before retrying

    # === Phase Handlers ===

    async def _handle_task_assignment_phase(self, slot: int):
        """Handle task assignment phase."""
        logger.debug(
            f"{self.uid_prefix} Handling task assignment phase for slot {slot}"
        )

        try:
            # Check consensus mode for coordination
            if self.core.consensus_mode == "continuous":
                # Continuous mode: Assign tasks immediately without coordination
                logger.info(
                    f"{self.uid_prefix} Continuous mode: assigning tasks for slot {slot}"
                )

                # Select miners for this slot
                selected_miners = self.tasks.cardano_select_miners(slot)
                logger.info(
                    f"{self.uid_prefix} Selected {len(selected_miners)} miners for slot {slot}"
                )

                if selected_miners:
                    # Send tasks to selected miners using minibatch approach
                    await self.tasks.cardano_send_minibatches(slot, selected_miners)
                    logger.info(
                        f"{self.uid_prefix} Minibatch tasks completed for {len(selected_miners)} miners in slot {slot}"
                    )
                else:
                    logger.warning(
                        f"{self.uid_prefix} No miners selected for slot {slot} - check miner availability"
                    )

            elif self.core.consensus_mode == "flexible":
                # FLEXIBLE MODE: CONTINUOUS TASK ASSIGNMENT WITH SYNCHRONIZED CUTOFF
                await self._run_continuous_flexible_task_assignment(slot)

            elif self.core.consensus_mode == "synchronized":
                # Synchronized mode: Wait for all validators
                await self.core.slot_coordinator.register_phase_entry_flexible(
                    slot, FlexibleSlotPhase.TASK_ASSIGNMENT
                )

                # Wait for consensus to proceed
                await self.core.slot_coordinator.wait_for_phase_consensus(
                    slot, SlotPhase.TASK_ASSIGNMENT
                )

                # Select miners for this slot
                selected_miners = self.tasks.cardano_select_miners(slot)

                if selected_miners:
                    # Send tasks to selected miners using minibatch approach
                    await self.tasks.cardano_send_minibatches(slot, selected_miners)
                    logger.info(
                        f"{self.uid_prefix} Minibatch tasks completed for {len(selected_miners)} miners in slot {slot}"
                    )

                # ENFORCE TASK ASSIGNMENT CUTOFF - ensure all validators finish together
                await self.core.slot_coordinator.enforce_task_assignment_cutoff(slot)
                logger.info(
                    f"{self.uid_prefix} Task assignment cutoff enforced for slot {slot}"
                )

        except Exception as e:
            logger.error(f"{self.uid_prefix} Error in task assignment phase: {e}")

    async def _run_continuous_flexible_task_assignment(self, slot: int):
        """
        CONTINUOUS TASK ASSIGNMENT: Lặp đi lặp lại trong suốt task assignment phase.

        - Giao mini batch (5 miners) → Chấm điểm → Giao tiếp tục
        - Lặp liên tục đến khi hết thời gian phase
        - Synchronized cutoff như Bittensor
        """
        logger.info(
            f"🔄 {self.uid_prefix} Starting CONTINUOUS flexible task assignment for slot {slot}"
        )

        try:
            # Step 1: Register phase entry
            await self.core.slot_coordinator.register_phase_entry_flexible(
                slot, FlexibleSlotPhase.TASK_ASSIGNMENT
            )

            # Step 2: Calculate phase timing using FIXED EPOCH START
            if hasattr(self.core.slot_coordinator, "_epoch_start"):
                epoch_start = self.core.slot_coordinator._epoch_start
            else:
                # FIXED EPOCH START: Same as FlexibleSlotCoordinator
                epoch_start = get_fixed_epoch_start()
                self.core.slot_coordinator._epoch_start = epoch_start
                logger.info(
                    f"🔒 {self.uid_prefix} Task assignment using FIXED EPOCH START: {epoch_start}"
                )

            slot_config = self.core.slot_coordinator.slot_config
            slot_duration_seconds = slot_config.slot_duration_minutes * 60
            task_assignment_duration = slot_config.min_task_assignment_seconds

            slot_start_time = epoch_start + (slot * slot_duration_seconds)
            task_assignment_end_time = slot_start_time + task_assignment_duration
            current_time = time.time()

            # Enhanced timing debug
            slot_progress = current_time - slot_start_time
            assignment_duration = task_assignment_end_time - slot_start_time
            remaining_in_assignment = task_assignment_end_time - current_time

            logger.info(f"📊 {self.uid_prefix} DETAILED TIMING DEBUG:")
            logger.info(
                f"   Slot {slot}: start={slot_start_time}, current={current_time}, progress={slot_progress:.1f}s"
            )
            logger.info(
                f"   Task assignment: duration={assignment_duration}s, remaining={remaining_in_assignment:.1f}s"
            )
            logger.info(
                f"   Assignment window: {slot_start_time} → {task_assignment_end_time}"
            )

            # Step 3: Get available miners
            selected_miners = self.tasks.cardano_select_miners(slot)
            if not selected_miners:
                logger.warning(f"{self.uid_prefix} No miners available for slot {slot}")
                return

            logger.info(
                f"🎯 {self.uid_prefix} Available miners: {len(selected_miners)} for continuous assignment"
            )

            # Step 4: CONTINUOUS MINI-BATCH LOOP - TARGET 3 ROUNDS
            batch_round = 1
            batch_size = 5  # Mini batch size
            batch_timeout = 22.0  # Extended batch timeout for miners
            max_rounds = 3  # TARGET: Exactly 3 rounds for testing

            logger.info(
                f"🎯 {self.uid_prefix} Starting 3-round continuous assignment (60s window)"
            )

            while time.time() < task_assignment_end_time and batch_round <= max_rounds:
                remaining_time = task_assignment_end_time - time.time()

                # Stop if less than 10 seconds remaining OR reached max rounds
                if remaining_time <= 10:
                    logger.info(
                        f"⏰ {self.uid_prefix} Approaching cutoff time ({remaining_time:.1f}s), stopping task assignment"
                    )
                    break

                if batch_round > max_rounds:
                    logger.info(
                        f"🎯 {self.uid_prefix} Completed target {max_rounds} rounds, stopping task assignment"
                    )
                    break

                logger.info(
                    f"📋 {self.uid_prefix} Mini-batch round {batch_round}/{max_rounds} - {remaining_time:.1f}s until cutoff"
                )

                # Select random 5 miners for this batch
                import random

                batch_miners = random.sample(
                    selected_miners, min(batch_size, len(selected_miners))
                )

                logger.info(
                    f"🎲 {self.uid_prefix} Selected {len(batch_miners)} miners for batch {batch_round}: {[m.uid for m in batch_miners]}"
                )

                # Send mini-batch with quick timeout
                try:
                    batch_start_time = time.time()
                    await asyncio.wait_for(
                        self.tasks.cardano_send_minibatches(slot, batch_miners),
                        timeout=min(
                            batch_timeout, remaining_time - 5
                        ),  # Leave 5s buffer
                    )
                    batch_duration = time.time() - batch_start_time

                    logger.info(
                        f"✅ {self.uid_prefix} Batch {batch_round} completed in {batch_duration:.1f}s"
                    )

                except asyncio.TimeoutError:
                    logger.warning(
                        f"⏰ {self.uid_prefix} Batch {batch_round} timed out after {batch_timeout}s"
                    )
                except Exception as e:
                    logger.error(
                        f"❌ {self.uid_prefix} Error in batch {batch_round}: {e}"
                    )

                batch_round += 1

                # Small delay between batches
                await asyncio.sleep(2)

            actual_rounds = batch_round - 1
            logger.info(
                f"🏁 {self.uid_prefix} Completed {actual_rounds}/{max_rounds} mini-batch rounds in task assignment phase"
            )

            # Step 5: ENFORCE SYNCHRONIZED CUTOFF - CRITICAL FOR BITTENSOR BEHAVIOR
            logger.info(
                f"🛑 {self.uid_prefix} ENFORCING SYNCHRONIZED CUTOFF for slot {slot} - ALL validators must stop together!"
            )
            await self._enforce_flexible_task_assignment_cutoff(slot)

            logger.info(
                f"✅ {self.uid_prefix} Ready for P2P consensus and metagraph update (slot {slot})"
            )

        except Exception as e:
            logger.error(
                f"❌ {self.uid_prefix} Error in continuous flexible task assignment: {e}"
            )

    async def _enforce_flexible_task_assignment_cutoff(self, slot: int):
        """
        Enforce synchronized task assignment cutoff for flexible mode.
        This ensures all validators stop task assignment at the same time,
        providing Bittensor-like synchronized behavior.
        """
        try:
            # Calculate exact cutoff time based on slot number and FIXED EPOCH
            if hasattr(self.core.slot_coordinator, "_epoch_start"):
                epoch_start = self.core.slot_coordinator._epoch_start
            else:
                # FIXED EPOCH START: Same as FlexibleSlotCoordinator
                epoch_start = get_fixed_epoch_start()
                self.core.slot_coordinator._epoch_start = epoch_start
                logger.info(
                    f"🔒 {self.uid_prefix} Cutoff calculation using FIXED EPOCH START: {epoch_start}"
                )

            # Get slot configuration from flexible coordinator
            slot_config = self.core.slot_coordinator.slot_config
            slot_duration_seconds = slot_config.slot_duration_minutes * 60
            task_assignment_duration = slot_config.min_task_assignment_seconds

            slot_start_time = epoch_start + (slot * slot_duration_seconds)
            cutoff_time = slot_start_time + task_assignment_duration
            current_time = time.time()

            logger.info(
                f"{self.uid_prefix} Flexible cutoff calculation: slot_start={slot_start_time}, cutoff={cutoff_time}, current={current_time}"
            )

            # STRICT SYNCHRONIZED CUTOFF - BITTENSOR BEHAVIOR
            if current_time < cutoff_time:
                wait_time = cutoff_time - current_time

                # For testing, allow reasonable wait times (up to 70s)
                if wait_time > 70:
                    logger.warning(
                        f"⚠️ {self.uid_prefix} Cutoff wait time too long ({wait_time:.1f}s), using immediate cutoff"
                    )
                    wait_time = 0

                if wait_time > 0:
                    logger.info(
                        f"⏰ {self.uid_prefix} SYNCHRONIZED WAIT: {wait_time:.1f}s until ALL validators stop task assignment (slot {slot})"
                    )
                    logger.info(
                        f"🔒 {self.uid_prefix} This ensures Bittensor-like synchronized cutoff behavior"
                    )
                    await asyncio.sleep(wait_time)
                    logger.info(
                        f"🛑 {self.uid_prefix} CUTOFF REACHED! All validators stopping task assignment now"
                    )
                else:
                    logger.info(
                        f"✅ {self.uid_prefix} Using immediate cutoff for slot {slot}"
                    )
            else:
                logger.info(
                    f"✅ {self.uid_prefix} Already past cutoff time for slot {slot}"
                )

            # Register that we've stopped task assignment
            await self.core.slot_coordinator.register_phase_entry_flexible(
                slot,
                FlexibleSlotPhase.TASK_ASSIGNMENT,  # Fixed: add missing phase parameter
                {"task_assignment_stopped": True},
            )

            logger.info(
                f"🛑 {self.uid_prefix} Task assignment SYNCHRONIZED CUTOFF enforced for slot {slot}"
            )

        except Exception as e:
            logger.error(f"❌ {self.uid_prefix} Error enforcing flexible cutoff: {e}")

    async def _handle_task_execution_phase(self, slot: int):
        """Handle task execution phase."""
        logger.debug(f"{self.uid_prefix} Handling task execution phase for slot {slot}")

        try:
            # Monitor task execution and collect results
            await self.tasks.monitor_task_execution(slot)

        except Exception as e:
            logger.error(f"{self.uid_prefix} Error in task execution phase: {e}")

    async def _handle_consensus_scoring_phase(self, slot: int):
        """Handle consensus scoring phase."""
        logger.debug(
            f"{self.uid_prefix} Handling consensus scoring phase for slot {slot}"
        )

        try:
            # FLEXIBLE MODE: This phase MUST be synchronized for all modes
            if self.core.consensus_mode in ["flexible", "synchronized"]:
                # Force synchronization for consensus (both flexible and synchronized)
                logger.info(
                    f"{self.uid_prefix} {self.core.consensus_mode.title()} mode: Enforcing consensus coordination"
                )

                # Wait for task assignment cutoff first
                await self.core.slot_coordinator.enforce_task_assignment_cutoff(slot)

                # CRITICAL: Set current_slot for score_miner_results to find slot_scores
                self.core.current_slot = slot

                # CRITICAL FIX: Wait for all tasks to complete and scores to be stored
                logger.info(
                    f"⏳ {self.uid_prefix} Waiting for all tasks to complete and scores to be stored..."
                )
                await asyncio.sleep(5)  # Give time for async tasks to complete

                # Check if scores are available, wait more if needed
                max_wait_attempts = 3  # Reduced to 15 seconds for late joiners
                for attempt in range(max_wait_attempts):
                    if (
                        hasattr(self.core, "slot_scores")
                        and slot in self.core.slot_scores
                        and len(self.core.slot_scores[slot]) > 0
                    ):
                        logger.info(
                            f"✅ {self.uid_prefix} Found {len(self.core.slot_scores[slot])} scores in slot_scores[{slot}]"
                        )
                        break
                    else:
                        # Check if we're a late joiner (past task assignment phase)
                        slot_progress = (
                            await self.core.slot_coordinator.get_slot_progress(slot)
                        )
                        if (
                            slot_progress > 35.0
                        ):  # If more than 35s into slot (past task assignment)
                            logger.warning(
                                f"⚠️ {self.uid_prefix} Late joiner detected (slot progress: {slot_progress:.1f}s). Skipping consensus for slot {slot}"
                            )
                            break

                        logger.info(
                            f"⏳ {self.uid_prefix} Attempt {attempt+1}/{max_wait_attempts}: No scores found yet, waiting 5s more..."
                        )
                        await asyncio.sleep(5)

                # Score local results
                local_scores_list = self.consensus.score_miner_results()

                # CRITICAL FIX: Handle late joiner case
                if not local_scores_list:
                    # Check if we're a late joiner again
                    slot_progress = await self.core.slot_coordinator.get_slot_progress(
                        slot
                    )
                    if (
                        slot_progress > 140.0
                    ):  # Late joiner (after 2min 20s in 4min cycle - past task assignment)
                        logger.warning(
                            f"🏃‍♂️ {self.uid_prefix} Late joiner - skipping consensus for slot {slot}, waiting for next slot..."
                        )
                        # Skip to next cycle
                        return {"skipped": True, "reason": "late_joiner", "slot": slot}

                    # Not a late joiner, try fallback scoring
                    logger.warning(
                        f"⚠️ {self.uid_prefix} No scores found after waiting, forcing fallback scoring..."
                    )
                    # Force fallback by temporarily removing slot_scores for this slot
                    if (
                        hasattr(self.core, "slot_scores")
                        and slot in self.core.slot_scores
                    ):
                        temp_scores = self.core.slot_scores[slot]
                        del self.core.slot_scores[slot]
                        local_scores_list = self.consensus.score_miner_results()
                        self.core.slot_scores[slot] = temp_scores  # Restore
                        logger.info(
                            f"🔄 {self.uid_prefix} Fallback scoring generated {len(local_scores_list)} scores"
                        )

                # CRITICAL FIX: Convert ValidatorScore list to miner_uid: score dict
                local_scores = {}
                for score_obj in local_scores_list:
                    local_scores[score_obj.miner_uid] = score_obj.score

                logger.info(
                    f"🎯 {self.uid_prefix} Converted {len(local_scores_list)} ValidatorScore objects to dict: {local_scores}"
                )

                # Coordinate consensus with other validators (synchronized)
                consensus_scores = (
                    await self.core.slot_coordinator.coordinate_consensus_round(
                        slot, local_scores
                    )
                )

                logger.info(
                    f"{self.uid_prefix} {self.core.consensus_mode.title()} consensus completed for slot {slot}: {len(consensus_scores)} final scores"
                )

                # CRITICAL: Store P2P consensus results for metagraph update
                if consensus_scores:
                    if not hasattr(self.core, "slot_aggregated_scores"):
                        self.core.slot_aggregated_scores = {}
                    self.core.slot_aggregated_scores[slot] = consensus_scores
                    logger.info(
                        f"💾 {self.uid_prefix} Stored {len(consensus_scores)} aggregated scores for slot {slot} metagraph update"
                    )

                    # DEBUG: Check execution flow
                    logger.info(
                        f"🔍 {self.uid_prefix} DEBUG: About to start immediate blockchain submission"
                    )

                    # IMMEDIATE blockchain submission to prevent scores from being cleared
                    logger.info(
                        f"🚀 {self.uid_prefix} Submitting consensus scores to blockchain immediately after P2P"
                    )

                    # Try immediate submission with enhanced error handling
                    submission_success = False
                    try:
                        logger.info(
                            f"🔧 {self.uid_prefix} DEBUG: Calling submit_to_blockchain({slot})"
                        )
                        await self.consensus.submit_to_blockchain(slot)
                        submission_success = True
                        # 🤖 CYBERPUNK SUCCESS 🤖
                        from rich.console import Console

                        cyber_console = Console(
                            force_terminal=True, color_system="truecolor"
                        )
                        cyber_console.print(
                            f"✅ [bold bright_green]{self.uid_prefix}[/] [bright_cyan]QUANTUM BLOCKCHAIN SYNC:[/] [bright_yellow]SLOT {slot} COMPLETE[/] 🔥"
                        )
                        logger.info(
                            f"✅ {self.uid_prefix} Blockchain submission completed for slot {slot}"
                        )
                    except Exception as e:
                        # 🔥 CYBERPUNK ERROR 🔥
                        from rich.console import Console

                        cyber_console = Console(
                            force_terminal=True, color_system="truecolor"
                        )
                        cyber_console.print(
                            f"❌ [bold bright_red]{self.uid_prefix}[/] [bright_yellow]CYBER MATRIX ERROR:[/] [bright_magenta]{e}[/] 🚨"
                        )
                        logger.error(
                            f"❌ {self.uid_prefix} Error in immediate blockchain submission: {e}"
                        )
                        logger.error(
                            f"🔍 {self.uid_prefix} Exception type: {type(e).__name__}"
                        )
                        logger.error(
                            f"🔍 {self.uid_prefix} Exception details: {str(e)}"
                        )

                    # Log submission result
                    logger.info(
                        f"📊 {self.uid_prefix} Immediate submission result: {'SUCCESS' if submission_success else 'FAILED'}"
                    )
                else:
                    logger.warning(
                        f"⚠️ {self.uid_prefix} No consensus scores to store for slot {slot}"
                    )

            else:
                # Legacy consensus logic (continuous mode)
                scores = self.consensus.score_miner_results()

                if scores:
                    # Broadcast scores to other validators
                    await self.consensus.broadcast_scores({str(slot): scores})

                    # Wait for consensus scores from other validators
                    consensus_timeout = 60.0  # 60 seconds timeout
                    await self.consensus.wait_for_consensus_scores(consensus_timeout)

                    # Finalize consensus by aggregating all scores (local + P2P)
                    final_scores = await self.consensus.finalize_consensus(slot)

                    logger.info(
                        f"{self.uid_prefix} Consensus finalized for slot {slot}: {len(final_scores)} final scores"
                    )

                logger.info(
                    f"{self.uid_prefix} Consensus scoring completed for slot {slot}"
                )

        except Exception as e:
            logger.error(f"{self.uid_prefix} Error in consensus scoring phase: {e}")

    async def _handle_metagraph_update_phase(self, slot: int):
        """Handle metagraph update phase."""

        # 🔥 CYBERPUNK UI: Metagraph Header
        try:
            from ..cli.cyberpunk_ui_extended import print_cyberpunk_metagraph_header

            print_cyberpunk_metagraph_header(self.uid_prefix, slot)
        except ImportError:
            pass

        logger.debug(
            f"{self.uid_prefix} Handling metagraph update phase for slot {slot}"
        )

        try:
            # FLEXIBLE MODE: Metagraph update MUST be synchronized for all modes
            if self.core.consensus_mode in ["flexible", "synchronized"]:
                logger.info(
                    f"{self.uid_prefix} {self.core.consensus_mode.title()} mode: Coordinating metagraph update"
                )

                # Coordinate metagraph update with other validators
                await self.core.slot_coordinator.register_phase_entry(
                    slot, SlotPhase.METAGRAPH_UPDATE
                )

                # Wait for all validators to reach metagraph phase
                await self.core.slot_coordinator.wait_for_phase_consensus(
                    slot, SlotPhase.METAGRAPH_UPDATE
                )

                # Update metagraph with consensus results
                await self.core.update_metagraph_with_consensus()

                # Submit to Core blockchain
                await self.consensus.submit_to_blockchain(slot)

                logger.info(
                    f"{self.uid_prefix} {self.core.consensus_mode.title()} metagraph update completed for slot {slot}"
                )

            else:
                # Legacy metagraph update (continuous mode)
                await self.core.update_metagraph_with_consensus()
                await self.consensus.submit_to_blockchain(slot)
                logger.info(
                    f"{self.uid_prefix} Metagraph update completed for slot {slot}"
                )

        except Exception as e:
            logger.error(f"{self.uid_prefix} Error in metagraph update phase: {e}")

    # === Delegation Methods (Backward Compatibility) ===

    async def add_miner_result(self, result: MinerResult) -> bool:
        """Add a miner result to the results buffer."""
        return await self.tasks.add_miner_result(result)

    def select_miners(self) -> List[MinerInfo]:
        """Select miners for task assignment."""
        return self.tasks.select_miners()

    def create_task_data(self, miner_uid: str) -> Any:
        """Create task data for a miner - must be implemented by subclasses."""
        return self.tasks.create_task_data(miner_uid)

    async def send_task_batch(self, miners_for_batch: List[MinerInfo], batch_num: int):
        """Send a batch of tasks to miners."""
        return await self.tasks.send_task_batch(miners_for_batch, batch_num)

    def score_miner_results(self):
        """Score all miner results."""
        return self.consensus.score_miner_results()

    async def broadcast_scores(
        self, scores_to_broadcast: Dict[str, List[ValidatorScore]]
    ):
        """Broadcast scores to other validators."""
        return await self.consensus.broadcast_scores(scores_to_broadcast)

    async def get_consensus_results_for_cycle(self, cycle_num: int):
        """Get consensus results for a specific cycle."""
        return await self.core.get_consensus_results_for_cycle(cycle_num)

    # === Utility Methods ===

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the validator node."""
        return {
            "validator_uid": self.info.uid,
            "current_cycle": self.current_cycle,
            "core_status": {
                "miners_count": len(self.core.miners_info),
                "validators_count": len(self.core.validators_info),
                "current_slot": self.core.get_current_blockchain_slot(),
            },
            "task_status": self.tasks.get_task_statistics(),
            "consensus_status": self.consensus.get_consensus_statistics(),
            "network_status": self.network.get_network_statistics(),
            "timestamp": time.time(),
        }

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the validator node."""
        return {
            "status": "healthy",
            "validator_uid": self.info.uid,
            "timestamp": time.time(),
            "uptime": time.time() - getattr(self, "_start_time", time.time()),
            "modules": {
                "core": True,
                "tasks": True,
                "consensus": True,
                "network": self.network.http_client is not None,
            },
            "flexible_consensus": self.flexible_consensus_enabled,
        }

    # === FLEXIBLE CONSENSUS METHODS ===

    def _setup_flexible_consensus(self):
        """Setup flexible consensus for this validator"""
        try:
            logger.info(
                f"🔄 {self.uid_prefix} Setting up flexible consensus in {self.flexible_mode} mode"
            )

            # 1. Initialize and assign the Slot Coordinator
            logger.info(f"   - Initializing FlexibleSlotCoordinator...")
            self.core.slot_coordinator = FlexibleSlotCoordinator(
                validator_uid=self.core.info.uid,
                # coordination_dir can be customized if needed, default is fine
            )
            logger.info(f"   - FlexibleSlotCoordinator assigned to core node.")

            # 2. Enable flexible mode in the consensus handler
            # This will now succeed because self.core.slot_coordinator exists
            if hasattr(self.consensus, "enable_flexible_mode"):
                logger.info(f"   - Enabling flexible mode in consensus handler...")
                self.consensus.enable_flexible_mode(
                    auto_detect_epoch=True, adaptive_timing=True
                )
                self.flexible_consensus_enabled = True
                logger.info(
                    f"✅ {self.uid_prefix} Flexible consensus setup completed successfully."
                )
            else:
                logger.error(
                    f"❌ {self.uid_prefix} Consensus handler does not support flexible mode."
                )
                self.flexible_consensus_enabled = False

        except Exception as e:
            logger.error(
                f"❌ {self.uid_prefix} Failed to setup flexible consensus: {e}",
                exc_info=True,
            )
            self.flexible_consensus_enabled = False

    def enable_flexible_consensus_mode(self, mode: str = None) -> bool:
        """
        Enable flexible consensus mode for this validator.

        Args:
            mode: Optional mode override ('ultra_flexible', 'balanced', 'performance')

        Returns:
            True if successful, False otherwise
        """
        if mode:
            self.flexible_mode = mode

        if not self.flexible_consensus_enabled:
            self._setup_flexible_consensus()
        elif hasattr(self.consensus, "enable_flexible_mode"):
            self.consensus.enable_flexible_mode()

        return self.flexible_consensus_enabled

    async def run_consensus_cycle_flexible(self, slot: Optional[int] = None) -> bool:
        """
        Run a single flexible consensus cycle with synchronized cutoffs.

        Args:
            slot: Optional slot number (auto-detected if None)

        Returns:
            True if successful, False otherwise
        """
        if not self.flexible_consensus_enabled:
            logger.warning(f"{self.uid_prefix} Flexible consensus not enabled")
            return False

        try:
            if hasattr(self.consensus, "run_flexible_consensus_cycle"):
                await self.consensus.run_flexible_consensus_cycle(slot)
                return True
            else:
                logger.error(
                    f"{self.uid_prefix} Flexible consensus cycle not available"
                )
                return False

        except Exception as e:
            logger.error(f"{self.uid_prefix} Error in flexible consensus cycle: {e}")
            return False

    def get_flexible_consensus_status(self) -> Dict[str, Any]:
        """Get flexible consensus status and metrics"""
        base_status = {
            "validator_uid": self.info.uid,
            "flexible_consensus_enabled": self.flexible_consensus_enabled,
            "flexible_mode": self.flexible_mode,
        }

        if self.flexible_consensus_enabled and hasattr(
            self.consensus, "get_flexible_status"
        ):
            base_status.update(self.consensus.get_flexible_status())

        return base_status

    # === Legacy Methods Support ===

    def get_current_cycle_number(self) -> int:
        """Get current cycle number (legacy method)."""
        return self.core.get_current_cycle_number()

    def set_current_cycle(self, cycle: int):
        """Set current cycle number (legacy method)."""
        return self.core.set_current_cycle(cycle)

    def advance_to_next_cycle(self):
        """Advance to next cycle (legacy method)."""
        return self.core.advance_to_next_cycle()

    async def _wait_for_metagraph_completion(self, slot: int) -> bool:
        """
        Wait for metagraph update to complete for a specific slot.

        Args:
            slot: Slot number to check

        Returns:
            True if metagraph update is complete, False otherwise
        """
        try:
            # Check if metagraph update is complete by looking for coordination files
            # or checking if the slot has been marked as updated
            if hasattr(self.core, "slot_coordinator"):
                # Check if metagraph phase is complete
                phase, _, _ = self.core.slot_coordinator.get_slot_phase(slot)
                if phase == SlotPhase.METAGRAPH_UPDATE:
                    # Check if metagraph update coordination is complete
                    ready_validators = (
                        await self.core.slot_coordinator.wait_for_phase_consensus(
                            slot, SlotPhase.METAGRAPH_UPDATE, timeout=30
                        )
                    )
                    if len(ready_validators) >= 2:  # At least 2 validators
                        logger.info(
                            f"✅ {self.uid_prefix} Metagraph update complete for slot {slot}"
                        )
                        return True

            # Fallback: check if consensus cycle completed successfully
            # This is a simple check - in practice you might want more sophisticated logic
            logger.info(
                f"⏳ {self.uid_prefix} Metagraph update status unknown for slot {slot}, assuming complete"
            )
            return True

        except Exception as e:
            logger.error(
                f"❌ {self.uid_prefix} Error checking metagraph completion for slot {slot}: {e}"
            )
            return False

    # === Context Manager Support ===

    async def __aenter__(self):
        """Async context manager entry."""
        # Pass the api_port from core to start method
        api_port = getattr(self.core, "api_port", None)
        logger.debug(f"{self.uid_prefix} __aenter__ passing api_port: {api_port}")

        await self.start(api_port=api_port)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()


# === Factory Function ===


def create_validator_node(
    validator_info: ValidatorInfo,
    core_client: Web3,
    account: Account,
    contract_address: str,
    **kwargs,
) -> ValidatorNode:
    """
    Factory function to create a ValidatorNode instance.

    Args:
        validator_info: Information about this validator
        core_client: Core blockchain Web3 client
        account: Core blockchain account for transactions
        contract_address: ModernTensor contract address
        **kwargs: Additional arguments for ValidatorNode

    Returns:
        Configured ValidatorNode instance
    """
    return ValidatorNode(
        validator_info=validator_info,
        core_client=core_client,
        account=account,
        contract_address=contract_address,
        **kwargs,
    )


# === Example Usage ===


async def example_usage():
    """Example of how to use the refactored ValidatorNode."""
    from ..core.datatypes import ValidatorInfo
    from web3 import Web3
    from eth_account import Account

    # Create validator info
    validator_info = ValidatorInfo(
        uid="validator_1",
        address="0x123...",
        api_endpoint="http://localhost:8001",
        trust_score=0.8,
        stake=1000.0,
        weight=1.0,
    )

    # Create Core client and account
    config = get_config()
    core_client = Web3(Web3.HTTPProvider(config.get_node_url()))
    account = Account.create()
    contract_address = "0x456..."

    # Create and start validator node
    async with create_validator_node(
        validator_info=validator_info,
        core_client=core_client,
        account=account,
        contract_address=contract_address,
        consensus_mode="continuous",
    ) as validator:
        # Node is now running
        status = validator.get_status()
        logger.info(f"Validator status: {status}")

        # Keep running
        await asyncio.sleep(3600)  # Run for 1 hour
