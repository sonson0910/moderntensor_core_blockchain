#!/usr/bin/env python3
"""
Test miner connection manually
"""

import asyncio
import httpx
import time

async def test_miner_connection():
    """Test connection to miners"""
    
    endpoints = [
        "http://localhost:8101",
        "http://localhost:8102"
    ]
    
    print("🔍 TESTING MINER CONNECTIONS")
    print("=" * 40)
    
    for i, endpoint in enumerate(endpoints, 1):
        print(f"\n📡 Testing endpoint {i}: {endpoint}")
        
        # Test 1: Health check
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{endpoint}/health")
                if response.status_code == 200:
                    print(f"✅ Health check: OK")
                else:
                    print(f"❌ Health check: Status {response.status_code}")
        except Exception as e:
            print(f"❌ Health check failed: {e}")
        
        # Test 2: Receive task endpoint
        try:
            task_data = {
                "task_id": f"test_{int(time.time())}",
                "description": "Test task",
                "deadline": str(int(time.time() + 30)),
                "priority": 3,
                "validator_endpoint": "http://localhost:8001"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(f"{endpoint}/receive-task", json=task_data)
                if response.status_code == 200:
                    print(f"✅ Receive task: OK")
                    print(f"   Response: {response.text}")
                else:
                    print(f"❌ Receive task: Status {response.status_code}")
                    print(f"   Response: {response.text}")
        except Exception as e:
            print(f"❌ Receive task failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_miner_connection()) 