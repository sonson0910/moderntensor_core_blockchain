
#!/usr/bin/env python3
"""
Manual task assignment test
"""

import asyncio
import httpx
import json
import time

async def test_task_assignment():
    """Test sending a task to miners manually"""
    
    # Test task data
    task_data = {
        "task_id": f"test_task_{int(time.time())}",
        "description": "Generate an image of a beautiful landscape",
        "deadline": str(int(time.time() + 30)),
        "priority": 3,
        "validator_endpoint": "http://localhost:8001",
        "slot": 17,
        "round": 1,
        "miner_uid": "miner_1",
        "validator_uid": "validator_1",
        "seed": 42,
        "created_at": time.time()
    }
    
    # Test endpoints
    endpoints = [
        "http://localhost:8101/receive-task",
        "http://localhost:8102/receive-task"
    ]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for i, endpoint in enumerate(endpoints, 1):
            try:
                print(f"📤 Testing endpoint {i}: {endpoint}")
                response = await client.post(endpoint, json=task_data)
                
                if response.status_code == 200:
                    print(f"✅ Endpoint {i}: Success")
                    print(f"   Response: {response.text}")
                else:
                    print(f"❌ Endpoint {i}: Status {response.status_code}")
                    print(f"   Response: {response.text}")
                    
            except Exception as e:
                print(f"❌ Endpoint {i}: Error - {e}")

if __name__ == "__main__":
    asyncio.run(test_task_assignment())
