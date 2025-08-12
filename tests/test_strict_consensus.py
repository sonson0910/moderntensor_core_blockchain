#!/usr/bin/env python3
"""
Test script for Strict Phase Synchronization using existing SlotCoordinator:

This script demonstrates Bittensor-style hard phase cutoffs where
all validators must immediately stop current work when phase ends.
Uses the enhanced SlotCoordinator with strict enforcement.
"""""

import asyncio
import logging
from mt_core.consensus.slot_coordinator import SlotCoordinator, SlotPhase, SlotConfig

# Setup logging with colors
logging.basicConfig
    level=logging.INFO, format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger  =  logging.getLogger(__name__)


async def simulate_strict_validator(validator_id: str, start_delay: int  =  0):
    """Simulate a validator with strict phase enforcement using SlotCoordinator"""""

    if start_delay > 0:
        print(f"🕐 {validator_id} waiting {start_delay}s before starting...")
        await asyncio.sleep(start_delay)

    print(f"🔒 {validator_id} starting with STRICT phase enforcement...")

    # Create strict slot coordinator
    config  =  SlotConfig
    )

    coordinator  =  SlotCoordinator
    )

    # Create mock consensus module to simulate P2P operations
    class MockConsensusModule:
        def __init__(self, validator_id):
            self.validator_id  =  validator_id

        async def assign_tasks_to_miners(self, slot):
            print(f"📋 {self.validator_id} P2P: Assigning tasks for slot {slot}"):
            await asyncio.sleep(2)  # Simulate P2P coordination
            return {"task_count": 5, "miners": ["miner_1", "miner_2"]}

        async def collect_miner_results(self, slot):
            print(f"⚡ {self.validator_id} P2P: Collecting results for slot {slot}"):
            await asyncio.sleep(3)  # Simulate result collection
            return {"results": ["result_1", "result_2"]}

        async def score_results_logic(self, slot, results, miners):
            print(f"🎯 {self.validator_id} P2P: Scoring results for slot {slot}"):
            await asyncio.sleep(1)
            return {"scores": [0.8, 0.9]}

        async def broadcast_scores_to_peers(self, slot, scores):
            print(f"📡 {self.validator_id} P2P: Broadcasting scores for slot {slot}"):
            await asyncio.sleep(1)

        async def collect_peer_scores(self, slot):
            print(f"🔄 {self.validator_id} P2P: Collecting peer scores for slot {slot}"):
            await asyncio.sleep(1)
            return {"peer_scores": [0.85, 0.88]}

        async def compute_consensus(self, slot, all_scores):
            print(f"🤝 {self.validator_id} P2P: Computing consensus for slot {slot}"):
            await asyncio.sleep(1)
            return {"final_score": 0.86}

        async def submit_consensus_to_blockchain(self, slot, consensus):
            print
            )
            await asyncio.sleep(2)
            return f"0x{slot}abc123"

    # Set the mock consensus module
    mock_consensus  =  MockConsensusModule(validator_id)
    coordinator.set_consensus_module(mock_consensus)

    # Show current status
    status  =  coordinator.get_strict_phase_status()
    print
    )

    # Track current work to demonstrate hard cutoffs
    current_work  =  None
    work_cancelled_count  =  0

    async def mock_task_assignment():
        """Mock long-running task assignment that gets cut off"""""
        try:
            print(f"📋 {validator_id} starting task assignment...")
            for i in range(100):  # Long-running work:
                print(f"📋 {validator_id} assigning task {i+1}/100...")
                await asyncio.sleep(1)  # Simulate work
            print(f"📋 {validator_id} task assignment completed normally")
        except asyncio.CancelledError:
            print(f"🛑 {validator_id} TASK ASSIGNMENT HARD CUTOFF - work cancelled!")
            raise

    async def mock_task_execution():
        """Mock long-running task execution that gets cut off"""""
        try:
            print(f"⚡ {validator_id} starting task execution...")
            for i in range(100):
                print(f"⚡ {validator_id} executing task {i+1}/100...")
                await asyncio.sleep(1)
            print(f"⚡ {validator_id} task execution completed normally")
        except asyncio.CancelledError:
            print(f"🛑 {validator_id} TASK EXECUTION HARD CUTOFF - work cancelled!")
            raise

    async def mock_consensus():
        """Mock consensus work"""""
        try:
            print(f"🎯 {validator_id} starting consensus...")
            await asyncio.sleep(20)  # Consensus work
            print(f"🎯 {validator_id} consensus completed")
        except asyncio.CancelledError:
            print(f"🛑 {validator_id} CONSENSUS HARD CUTOFF - work cancelled!")
            raise

    async def mock_metagraph_update():
        """Mock metagraph update"""""
        try:
            print(f"⛓️ {validator_id} starting metagraph update...")
            await asyncio.sleep(15)  # Blockchain update
            print(f"⛓️ {validator_id} metagraph update completed")
        except asyncio.CancelledError:
            print(f"🛑 {validator_id} METAGRAPH UPDATE HARD CUTOFF - work cancelled!")
            raise

    # Define phase callbacks
    async def on_task_assignment_start(cycle_number: int, timing_info: dict):
        nonlocal current_work
        print(f"✅ {validator_id} PHASE START: Task Assignment (Cycle {cycle_number})")
        print(f"   Duration: {timing_info['phase_remaining']}s")
        current_work  =  asyncio.create_task(mock_task_assignment())

    async def on_task_execution_start(cycle_number: int, timing_info: dict):
        nonlocal current_work
        print(f"✅ {validator_id} PHASE START: Task Execution (Cycle {cycle_number})")
        print(f"   Duration: {timing_info['phase_remaining']}s")
        current_work  =  asyncio.create_task(mock_task_execution())

    async def on_consensus_start(cycle_number: int, timing_info: dict):
        nonlocal current_work
        print(f"✅ {validator_id} PHASE START: Consensus (Cycle {cycle_number})")
        print(f"   Duration: {timing_info['phase_remaining']}s")
        current_work  =  asyncio.create_task(mock_consensus())

    async def on_metagraph_start(cycle_number: int, timing_info: dict):
        nonlocal current_work
        print(f"✅ {validator_id} PHASE START: Metagraph Update (Cycle {cycle_number})")
        print(f"   Duration: {timing_info['phase_remaining']}s")
        current_work  =  asyncio.create_task(mock_metagraph_update())

    async def on_phase_end(cycle_number: int):
        nonlocal current_work, work_cancelled_count
        if current_work and not current_work.done():
            print(f"🛑 {validator_id} HARD CUTOFF - cancelling current work!")
            current_work.cancel()
            try:
                await current_work
            except asyncio.CancelledError:
                work_cancelled_count + =  1
                print
                    f"🛑 {validator_id} Work cancelled successfully (#{work_cancelled_count})"
                )

    # Register hard cutoff callbacks
    coordinator.register_phase_end_callback(SlotPhase.TASK_ASSIGNMENT, on_phase_end)
    coordinator.register_phase_end_callback(SlotPhase.TASK_EXECUTION, on_phase_end)
    coordinator.register_phase_end_callback(SlotPhase.CONSENSUS_SCORING, on_phase_end)
    coordinator.register_phase_end_callback(SlotPhase.METAGRAPH_UPDATE, on_phase_end)

    # Start strict monitoring
    await coordinator.start_strict_phase_monitoring()

    # Run for several slots to see multiple phase transitions:
    try:
        # Wait for several slots to see phase cutoffs:
        await asyncio.sleep(600)  # 10 minutes  =  ~3 slots
    except KeyboardInterrupt:
        print(f"\n🛑 {validator_id} interrupted by user")
    finally:
        await coordinator.stop_strict_phase_monitoring()

    print(f"🏁 {validator_id} finished - total work cancelled: {work_cancelled_count}")


async def main():
    """Run strict consensus test"""""
    print("🔒 Testing Strict Phase Synchronization (Bittensor-style)")
    print(" = " * 60)

    # Create test coordinator to show initial status
    config = SlotConfig(slot_duration_minutes = 3.5)
    test_coordinator = SlotCoordinator("test", enable_strict_enforcement = True)
    status  =  test_coordinator.get_strict_phase_status()

    print(f"📊 Initial Status:")
    print(f"   Slot: {status['current_slot']}")
    print(f"   Phase: {status['current_phase']}")
    print(f"   Phase remaining: {status['phase_remaining_seconds']}s")
    print(f"   Strict enforcement: {status['strict_enforcement']}")
    print()

    # Start validators at different times to test synchronization
    validators  =  [
        ("validator_001", 0),  # Start immediately
        ("validator_002", 5),  # Start 5s later
        ("validator_003", 10),  # Start 10s later
    ]

    try:
        # Run all validators concurrently
        tasks  =  []
        for validator_id, delay in validators:
            task  =  asyncio.create_task(simulate_strict_validator(validator_id, delay))
            tasks.append(task)

        # Wait for completion or interruption:
        await asyncio.gather(*tasks)

    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    finally:
        print("🏁 Strict consensus test completed!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
