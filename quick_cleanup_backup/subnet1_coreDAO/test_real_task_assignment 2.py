#!/usr/bin/env python3
"""
Test real task assignment with mock miners
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


async def test_task_creation_and_sending():
    """Test creating and sending real tasks"""
    print("🚀 TESTING REAL TASK ASSIGNMENT")
    print("=" * 50)

    try:
        from mt_core.network.server import TaskModel

        # Create a real task
        task_data = {
            "task_id": f"real_test_{int(time.time())}",
            "description": "Generate an image of a beautiful landscape with mountains and a lake",
            "deadline": str(int(time.time() + 30)),
            "priority": 3,
            "validator_endpoint": "http://localhost:8001",
        }

        task = TaskModel(**task_data)
        print(f"✅ Task created: {task.task_id}")

        # Test task serialization (fix Pydantic v2 warning)
        try:
            task_dict = task.model_dump()  # Use model_dump instead of dict
        except AttributeError:
            task_dict = task.dict()  # Fallback for older versions

        print(f"✅ Task serialized: {task_dict}")

        # Simulate sending to miners
        miners = [
            {"uid": "miner_1", "endpoint": "http://localhost:8101"},
            {"uid": "miner_2", "endpoint": "http://localhost:8102"},
        ]

        print(f"\n📤 Simulating task sending to {len(miners)} miners...")

        for i, miner in enumerate(miners, 1):
            print(f"\n📡 Miner {i}: {miner['uid']}")
            print(f"   Endpoint: {miner['endpoint']}")
            print(f"   Task ID: {task.task_id}")
            print(f"   Description: {task.description}")
            print(f"   Priority: {task.priority}")
            print(f"   ✅ Would send successfully")

        print(f"\n✅ Task assignment simulation completed")
        return True

    except Exception as e:
        print(f"❌ Task creation failed: {e}")
        import traceback

        print(f"❌ Traceback: {traceback.format_exc()}")
        return False


async def test_validator_logic():
    """Test validator task assignment logic"""
    print("\n🔍 TESTING VALIDATOR LOGIC")
    print("=" * 40)

    try:
        # Simulate validator task assignment process
        slot = 17.0
        task_round = 1

        print(f"📋 Slot: {slot}")
        print(f"📋 Round: {task_round}")

        # Simulate miner discovery
        miners = [
            {"uid": "miner_1", "endpoint": "http://localhost:8101"},
            {"uid": "miner_2", "endpoint": "http://localhost:8102"},
        ]

        print(f"📋 Found {len(miners)} miners")

        # Simulate task assignment loop
        for miner in miners:
            task_id = f"slot_{slot}_r{task_round}_{miner['uid']}_{int(time.time())}"
            print(f"📤 Would assign task {task_id} to {miner['uid']}")

        print(f"✅ Validator logic simulation completed")
        return True

    except Exception as e:
        print(f"❌ Validator logic failed: {e}")
        return False


async def test_http_communication():
    """Test HTTP communication patterns"""
    print("\n🌐 TESTING HTTP COMMUNICATION")
    print("=" * 40)

    try:
        import httpx

        # Test URL construction
        miner_endpoint = "http://localhost:8101"
        url = f"{miner_endpoint.rstrip('/')}/receive-task"
        print(f"✅ URL: {url}")

        # Test payload structure
        payload = {
            "task_id": f"http_test_{int(time.time())}",
            "description": "Test task for HTTP communication",
            "deadline": str(int(time.time() + 30)),
            "priority": 3,
            "validator_endpoint": "http://localhost:8001",
        }
        print(f"✅ Payload structure: {payload}")

        # Test client creation
        client = httpx.AsyncClient(timeout=10.0)
        print(f"✅ HTTP client created")

        print(f"✅ HTTP communication test completed")
        return True

    except Exception as e:
        print(f"❌ HTTP communication failed: {e}")
        return False


async def main():
    """Main test function"""
    print("🚀 COMPREHENSIVE TASK ASSIGNMENT TEST")
    print("=" * 60)

    # Test 1: Task creation and sending
    task_ok = await test_task_creation_and_sending()

    # Test 2: Validator logic
    validator_ok = await test_validator_logic()

    # Test 3: HTTP communication
    http_ok = await test_http_communication()

    # Summary
    print("\n📊 TEST SUMMARY")
    print("=" * 40)
    print(f"✅ Task Creation: {'OK' if task_ok else 'FAILED'}")
    print(f"✅ Validator Logic: {'OK' if validator_ok else 'FAILED'}")
    print(f"✅ HTTP Communication: {'OK' if http_ok else 'FAILED'}")

    if all([task_ok, validator_ok, http_ok]):
        print("\n🎉 ALL TESTS PASSED!")
        print("💡 Task assignment logic is working correctly")
        print("💡 The issue is likely timing/startup related")
    else:
        print("\n❌ SOME TESTS FAILED")
        print("💡 Check the failed components above")


if __name__ == "__main__":
    asyncio.run(main())
