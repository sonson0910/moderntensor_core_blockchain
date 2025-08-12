#!/usr/bin/env python3
"""
Debug task assignment issue - why miners are not receiving tasks
"""

import os
import sys
import time
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv

def analyze_task_assignment_logs():
    """Analyze task assignment logs to find the issue"""
    print("🔍 ANALYZING TASK ASSIGNMENT LOGS")
    print("=" * 50)
    
    # Load environment
    load_dotenv()
    
    # Check validator logs for task assignment
    log_file = Path("logs/validator_1.log")
    if not log_file.exists():
        print("❌ Validator log not found")
        return False
    
    print("📊 ANALYZING TASK ASSIGNMENT PATTERN:")
    print("-" * 40)
    
    # Track task assignment events
    events = {
        "task_assignment_started": 0,
        "sequential_rounds": 0,
        "tasks_sent": 0,
        "tasks_scored": 0,
        "errors": 0
    }
    
    with open(log_file, "r") as f:
        for line in f:
            if "Starting task assignment" in line:
                events["task_assignment_started"] += 1
            elif "Sequential round" in line:
                events["sequential_rounds"] += 1
            elif "Sequential task sent" in line:
                events["tasks_sent"] += 1
            elif "Scored task from miner" in line:
                events["tasks_scored"] += 1
            elif "Error" in line and ("task" in line or "miner" in line):
                events["errors"] += 1
    
    print("📊 TASK ASSIGNMENT EVENTS:")
    for event, count in events.items():
        print(f"   {event}: {count}")
    
    # Check for specific patterns
    print("\n🔍 CHECKING SPECIFIC PATTERNS:")
    print("-" * 30)
    
    patterns = {
        "Using mock miners": 0,
        "Found.*available miners": 0,
        "Sequential round.*completed: 0 scores": 0,
        "Error.*miner": 0,
        "HTTP.*POST": 0,
        "receive-task": 0
    }
    
    with open(log_file, "r") as f:
        for line in f:
            for pattern in patterns:
                if pattern in line:
                    patterns[pattern] += 1
    
    for pattern, count in patterns.items():
        print(f"   {pattern}: {count}")
    
    return events, patterns

def check_miner_endpoints():
    """Check if miner endpoints are accessible"""
    print("\n🔍 CHECKING MINER ENDPOINTS")
    print("=" * 50)
    
    import requests
    
    miner_endpoints = [
        "http://localhost:8101",
        "http://localhost:8102"
    ]
    
    for endpoint in miner_endpoints:
        try:
            response = requests.get(f"{endpoint}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ {endpoint}: Healthy")
            else:
                print(f"⚠️  {endpoint}: Status {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint}: Error - {e}")

def check_miner_logs():
    """Check miner logs for any issues"""
    print("\n🔍 CHECKING MINER LOGS")
    print("=" * 50)
    
    for i in [1, 2]:
        log_file = Path(f"logs/miner_{i}.log")
        if log_file.exists():
            print(f"\n📄 Miner {i} logs:")
            print("-" * 20)
            
            with open(log_file, "r") as f:
                lines = f.readlines()
                # Show last 10 lines
                for line in lines[-10:]:
                    print(f"   {line.strip()}")
        else:
            print(f"❌ Miner {i} log not found")

def create_task_assignment_test():
    """Create a test to manually send a task to miners"""
    print("\n🔧 CREATING TASK ASSIGNMENT TEST")
    print("=" * 50)
    
    test_script = """
#!/usr/bin/env python3
\"\"\"
Manual task assignment test
\"\"\"

import asyncio
import httpx
import json
import time

async def test_task_assignment():
    \"\"\"Test sending a task to miners manually\"\"\"
    
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
"""
    
    test_file = Path("test_task_assignment.py")
    with open(test_file, "w") as f:
        f.write(test_script)
    
    print(f"✅ Created test script: {test_file}")
    print("🚀 To run test:")
    print("   python test_task_assignment.py")

def main():
    print("🔧 DEBUGGING TASK ASSIGNMENT ISSUE")
    print("=" * 50)
    
    # Analyze logs
    events, patterns = analyze_task_assignment_logs()
    
    # Check endpoints
    check_miner_endpoints()
    
    # Check miner logs
    check_miner_logs()
    
    # Create test
    create_task_assignment_test()
    
    print("\n🔍 DIAGNOSIS:")
    print("   - Sequential rounds are running but no tasks sent")
    print("   - Possible issues:")
    print("     1. _send_single_task_to_miner returning None")
    print("     2. Miner endpoints not accessible")
    print("     3. HTTP client issues")
    print("     4. Task data format problems")
    
    print("\n📋 NEXT STEPS:")
    print("1. Run test_task_assignment.py to test endpoints")
    print("2. Check if miners are running and accessible")
    print("3. Verify task data format")
    print("4. Debug _send_single_task_to_miner function")

if __name__ == "__main__":
    main() 