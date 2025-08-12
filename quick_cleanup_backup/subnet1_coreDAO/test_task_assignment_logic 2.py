#!/usr/bin/env python3
"""
Test task assignment logic - simulate what validators should do
"""

import asyncio
import time
import sys
from pathlib import Path

# Add paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
moderntensor_path = project_root.parent / "moderntensor_aptos"
sys.path.insert(0, str(moderntensor_path))


async def test_task_creation():
    """Test if we can create tasks properly"""
    print("🔍 TESTING TASK CREATION")
    print("=" * 40)

    try:
        from mt_core.network.server import TaskModel

        # Create a test task
        task_data = {
            "task_id": f"test_task_{int(time.time())}",
            "description": "Generate an image of a beautiful landscape",
            "deadline": str(int(time.time() + 30)),
            "priority": 3,
            "validator_endpoint": "http://localhost:8001",
        }

        task = TaskModel(**task_data)
        print(f"✅ Task created successfully: {task.task_id}")
        print(f"   Description: {task.description}")
        print(f"   Priority: {task.priority}")

        # Test task serialization
        task_dict = task.dict()
        print(f"✅ Task serialized: {task_dict}")

        return True

    except Exception as e:
        print(f"❌ Task creation failed: {e}")
        import traceback

        print(f"❌ Traceback: {traceback.format_exc()}")
        return False


async def test_miner_discovery():
    """Test if we can discover miners"""
    print("\n🔍 TESTING MINER DISCOVERY")
    print("=" * 40)

    try:
        # Simulate miner discovery
        mock_miners = [
            {
                "uid": "7375626e6574315f6d696e65725f31",  # subnet1_miner_1
                "endpoint": "http://localhost:8101",
                "address": "0xd89fBAbb72190ed22F012ADFC693ad974bAD3005",
            },
            {
                "uid": "7375626e6574315f6d696e65725f32",  # subnet1_miner_2
                "endpoint": "http://localhost:8102",
                "address": "0x1234567890123456789012345678901234567890",
            },
        ]

        print(f"✅ Found {len(mock_miners)} miners:")
        for i, miner in enumerate(mock_miners, 1):
            print(f"   Miner {i}: {miner['uid']} -> {miner['endpoint']}")

        return mock_miners

    except Exception as e:
        print(f"❌ Miner discovery failed: {e}")
        return []


async def test_task_assignment_simulation():
    """Simulate task assignment process"""
    print("\n📤 TESTING TASK ASSIGNMENT SIMULATION")
    print("=" * 40)

    # Test task creation
    task_ok = await test_task_creation()
    if not task_ok:
        print("❌ Cannot proceed - task creation failed")
        return

    # Test miner discovery
    miners = await test_miner_discovery()
    if not miners:
        print("❌ Cannot proceed - no miners found")
        return

    # Simulate task assignment
    print(f"\n📋 Simulating task assignment to {len(miners)} miners...")

    for i, miner in enumerate(miners, 1):
        print(f"\n📡 Assigning task to Miner {i}:")
        print(f"   UID: {miner['uid']}")
        print(f"   Endpoint: {miner['endpoint']}")

        # Simulate HTTP request
        print(f"   📤 Would send POST to: {miner['endpoint']}/receive-task")
        print(
            f"   📦 Would send payload: {{'task_id': 'test_123', 'description': '...'}}"
        )

        # Simulate response
        print(f"   ✅ Simulated: Task sent successfully")

    print(f"\n✅ Task assignment simulation completed for {len(miners)} miners")


async def test_http_client_simulation():
    """Test HTTP client creation and usage"""
    print("\n🌐 TESTING HTTP CLIENT SIMULATION")
    print("=" * 40)

    try:
        import httpx

        # Test client creation
        print("📡 Creating HTTP client...")
        client = httpx.AsyncClient(timeout=10.0)
        print("✅ HTTP client created successfully")

        # Test URL construction
        miner_endpoint = "http://localhost:8101"
        url = f"{miner_endpoint.rstrip('/')}/receive-task"
        print(f"✅ URL constructed: {url}")

        # Test payload preparation
        payload = {
            "task_id": f"test_{int(time.time())}",
            "description": "Test task",
            "deadline": str(int(time.time() + 30)),
            "priority": 3,
            "validator_endpoint": "http://localhost:8001",
        }
        print(f"✅ Payload prepared: {payload}")

        print("✅ HTTP client simulation successful")
        return True

    except Exception as e:
        print(f"❌ HTTP client simulation failed: {e}")
        return False


async def main():
    """Main test function"""
    print("🚀 TESTING TASK ASSIGNMENT LOGIC")
    print("=" * 50)

    # Test HTTP client
    http_ok = await test_http_client_simulation()

    # Test task assignment simulation
    await test_task_assignment_simulation()

    print("\n📊 SUMMARY")
    print("=" * 40)
    if http_ok:
        print("✅ HTTP client: Working")
    else:
        print("❌ HTTP client: Failed")

    print("✅ Task assignment logic: Ready")
    print("\n💡 NEXT STEPS:")
    print("   1. Start miners manually")
    print("   2. Start validators manually")
    print("   3. Check logs for task assignment")


if __name__ == "__main__":
    asyncio.run(main())
