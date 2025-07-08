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
from ..config.settings import settings

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
        consensus_mode: str = "continuous",
        batch_wait_time: float = 30.0,
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
        """
        # Initialize core module
        self.core = ValidatorNodeCore(
            validator_info=validator_info,
            core_client=core_client,
            account=account,
            contract_address=contract_address,
            state_file=state_file,
            consensus_mode=consensus_mode,
            batch_wait_time=batch_wait_time,
        )

        # Initialize functional modules
        self.tasks = ValidatorNodeTasks(self.core)
        self.consensus = ValidatorNodeConsensus(self.core)
        self.network = ValidatorNodeNetwork(self.core)

        # Aliases for backward compatibility
        self.uid_prefix = self.core.uid_prefix
        self.info = self.core.info

        # Background tasks
        self.main_task = None
        self.health_monitor_task = None

        logger.info(
            f"✅ {self.uid_prefix} Refactored ValidatorNode initialized successfully"
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

        try:
            # Load initial metagraph data
            await self.core.load_metagraph_data()

            # Start network services
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
                    await self._handle_consensus_scoring_phase(current_slot)
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
            if self.core.consensus_mode == "flexible":
                # Flexible mode: Enter task assignment independently
                await self.core.slot_coordinator.register_phase_entry(
                    slot, SlotPhase.TASK_ASSIGNMENT
                )
                logger.info(
                    f"{self.uid_prefix} Entered task assignment phase independently for slot {slot}"
                )

                # Select and send tasks to miners using minibatch approach
                selected_miners = self.tasks.cardano_select_miners(slot)

                if selected_miners:
                    await self.tasks.cardano_send_minibatches(slot, selected_miners)
                    logger.info(
                        f"{self.uid_prefix} Minibatch tasks completed for {len(selected_miners)} miners in slot {slot}"
                    )

            elif self.core.consensus_mode == "synchronized":
                # Synchronized mode: Wait for all validators
                await self.core.slot_coordinator.register_phase_entry(
                    slot, SlotPhase.TASK_ASSIGNMENT
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

        except Exception as e:
            logger.error(f"{self.uid_prefix} Error in task assignment phase: {e}")

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
            # Score miner results
            scores = self.consensus.score_miner_results()

            if scores:
                # Broadcast scores to other validators
                await self.consensus.broadcast_scores({str(slot): scores})

                # Wait for consensus
                await self.consensus.wait_for_consensus(slot)

                logger.info(
                    f"{self.uid_prefix} Consensus scoring completed for slot {slot}"
                )

        except Exception as e:
            logger.error(f"{self.uid_prefix} Error in consensus scoring phase: {e}")

    async def _handle_metagraph_update_phase(self, slot: int):
        """Handle metagraph update phase."""
        logger.debug(
            f"{self.uid_prefix} Handling metagraph update phase for slot {slot}"
        )

        try:
            # Update metagraph with consensus results
            await self.core.update_metagraph_with_consensus()

            # Submit to Core blockchain
            await self.consensus.submit_to_blockchain(slot)

            logger.info(f"{self.uid_prefix} Metagraph update completed for slot {slot}")

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
        }

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

    # === Context Manager Support ===

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
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
    core_client = Web3(Web3.HTTPProvider(settings.CORE_RPC_URL))
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
