#!/usr/bin/env python3
"""
Debug task flow - why miners are not receiving tasks
"""

import asyncio
import httpx
import time
import os
import sys
from pathlib import Path

# Add paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
moderntensor_path = project_root.parent / "moderntensor_aptos"
sys.path.insert(0, str(moderntensor_path))


async def test_miner_health():
    """Test if miners are healthy"""
    print("🔍 TESTING MINER HEALTH")
    print("=" * 40)

    miners = [
        {"id": 1, "endpoint": "http://localhost:8101"},
        {"id": 2, "endpoint": "http://localhost:8102"},
    ]

    healthy_miners = []
    for miner in miners:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{miner['endpoint']}/health")
                if response.status_code == 200:
                    print(f"✅ Miner {miner['id']}: Healthy")
                    healthy_miners.append(miner)
                else:
                    print(f"❌ Miner {miner['id']}: Status {response.status_code}")
        except Exception as e:
            print(f"❌ Miner {miner['id']}: Connection failed - {e}")

    return healthy_miners


async def test_task_sending():
    """Test sending tasks to miners"""
    print("\n📤 TESTING TASK SENDING")
    print("=" * 40)

    miners = [
        {"id": 1, "endpoint": "http://localhost:8101"},
        {"id": 2, "endpoint": "http://localhost:8102"},
    ]

    for miner in miners:
        print(f"\n📡 Testing task sending to Miner {miner['id']}")

        task_data = {
            "task_id": f"debug_test_{int(time.time())}",
            "description": "Debug test task",
            "deadline": str(int(time.time() + 30)),
            "priority": 3,
            "validator_endpoint": "http://localhost:8001",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{miner['endpoint']}/receive-task", json=task_data
                )

                if response.status_code == 200:
                    print(f"✅ Task sent successfully to Miner {miner['id']}")
                    print(f"   Response: {response.text}")
                else:
                    print(
                        f"❌ Task failed for Miner {miner['id']}: Status {response.status_code}"
                    )
                    print(f"   Response: {response.text}")

        except Exception as e:
            print(f"❌ Task sending failed for Miner {miner['id']}: {e}")


async def test_validator_health():
    """Test if validators are healthy"""
    print("\n🔍 TESTING VALIDATOR HEALTH")
    print("=" * 40)

    validators = [
        {"id": 1, "endpoint": "http://localhost:8001"},
        {"id": 2, "endpoint": "http://localhost:8002"},
    ]

    healthy_validators = []
    for validator in validators:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{validator['endpoint']}/health")
                if response.status_code == 200:
                    print(f"✅ Validator {validator['id']}: Healthy")
                    healthy_validators.append(validator)
                else:
                    print(
                        f"❌ Validator {validator['id']}: Status {response.status_code}"
                    )
        except Exception as e:
            print(f"❌ Validator {validator['id']}: Connection failed - {e}")

    return healthy_validators


async def main():
    """Main debug function"""
    print("🚀 DEBUGGING TASK FLOW ISSUES")
    print("=" * 50)

    # Test validator health
    healthy_validators = await test_validator_health()

    # Test miner health
    healthy_miners = await test_miner_health()

    # Test task sending
    await test_task_sending()

    # Summary
    print("\n📊 SUMMARY")
    print("=" * 40)
    print(f"✅ Healthy Validators: {len(healthy_validators)}/2")
    print(f"✅ Healthy Miners: {len(healthy_miners)}/2")

    if len(healthy_miners) == 0:
        print("\n❌ PROBLEM: No miners are running!")
        print("   Solution: Start miners first")
    elif len(healthy_validators) == 0:
        print("\n❌ PROBLEM: No validators are running!")
        print("   Solution: Start validators first")
    else:
        print("\n✅ All components are running")
        print("   Next: Check validator logs for task assignment issues")


if __name__ == "__main__":
    asyncio.run(main())
