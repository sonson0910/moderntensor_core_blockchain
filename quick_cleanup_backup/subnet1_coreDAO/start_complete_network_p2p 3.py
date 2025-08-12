#!/usr/bin/env python3
"""
Start complete network with P2P consensus support
"""

import os
import sys
import time
import subprocess
import asyncio
import httpx
from pathlib import Path

def start_component(name, script, env_vars=None):
    """Start a single component"""
    print(f"🚀 Starting {name}...")
    
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)
    
    try:
        process = subprocess.Popen(
            [sys.executable, script],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print(f"✅ {name} started (PID: {process.pid})")
        return process
        
    except Exception as e:
        print(f"❌ Failed to start {name}: {e}")
        return None

def wait_for_port(port, timeout=60):
    """Wait for port to be available"""
    print(f"⏳ Waiting for port {port} to be ready...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            if result == 0:
                print(f"✅ Port {port} is ready")
                return True
        except:
            pass
        time.sleep(2)
    
    print(f"❌ Port {port} not ready after {timeout}s")
    return False

def test_network_health():
    """Test network health"""
    print("\n🔍 TESTING NETWORK HEALTH")
    print("=" * 40)
    
    components = [
        {"name": "Validator 1", "port": 8001},
        {"name": "Validator 2", "port": 8002},
        {"name": "Miner 1", "port": 8101},
        {"name": "Miner 2", "port": 8102}
    ]
    
    healthy_components = []
    
    for component in components:
        try:
            response = httpx.get(f"http://localhost:{component['port']}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ {component['name']}: Healthy")
                healthy_components.append(component)
            else:
                print(f"❌ {component['name']}: Status {response.status_code}")
        except Exception as e:
            print(f"❌ {component['name']}: Connection failed - {e}")
    
    return healthy_components

def test_p2p_consensus():
    """Test P2P consensus between validators"""
    print("\n🤝 TESTING P2P CONSENSUS")
    print("=" * 40)
    
    try:
        # Test if validators can see each other
        print("🔍 Checking validator discovery...")
        
        # Try to get validator list from validator 1
        try:
            response = httpx.get("http://localhost:8001/validators", timeout=5)
            if response.status_code == 200:
                validators = response.json()
                print(f"✅ Validator 1 found {len(validators)} validators")
                for v in validators:
                    print(f"   - {v.get('uid', 'unknown')} at {v.get('endpoint', 'unknown')}")
                
                if len(validators) >= 2:
                    print("✅ P2P consensus can work!")
                    return True
                else:
                    print("⚠️ Not enough validators for P2P consensus")
                    return False
            else:
                print(f"❌ Validator 1 returned status {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Cannot get validator list: {e}")
            return False
            
    except Exception as e:
        print(f"❌ P2P consensus test failed: {e}")
        return False

def test_task_assignment():
    """Test task assignment to miners"""
    print("\n📤 TESTING TASK ASSIGNMENT")
    print("=" * 40)
    
    miners = [
        {"id": 1, "endpoint": "http://localhost:8101"},
        {"id": 2, "endpoint": "http://localhost:8102"}
    ]
    
    successful_tasks = 0
    
    for miner in miners:
        try:
            task_data = {
                "task_id": f"p2p_test_{int(time.time())}",
                "description": "Test task for P2P consensus",
                "deadline": str(int(time.time() + 30)),
                "priority": 3,
                "validator_endpoint": "http://localhost:8001"
            }
            
            response = httpx.post(f"{miner['endpoint']}/receive-task", json=task_data, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ Task sent successfully to Miner {miner['id']}")
                print(f"   Response: {response.text}")
                successful_tasks += 1
            else:
                print(f"❌ Task failed for Miner {miner['id']}: Status {response.status_code}")
                
        except Exception as e:
            print(f"❌ Task sending failed for Miner {miner['id']}: {e}")
    
    return successful_tasks

def main():
    """Main function"""
    print("🚀 STARTING COMPLETE NETWORK WITH P2P CONSENSUS")
    print("=" * 60)
    
    # Start validators first
    print("\n📋 Starting Validators...")
    
    validator1 = start_component("Validator 1", "scripts/run_validator_core.py", {"VALIDATOR_ID": "1"})
    if not validator1:
        print("❌ Cannot proceed without Validator 1")
        return
    
    # Wait before starting validator 2
    time.sleep(5)
    
    validator2 = start_component("Validator 2", "scripts/run_validator_core.py", {"VALIDATOR_ID": "2"})
    if not validator2:
        print("❌ Cannot proceed without Validator 2")
        return
    
    # Wait for validators to be ready
    print("\n⏳ Waiting for validators to be ready...")
    
    if not wait_for_port(8001, 60):
        print("❌ Validator 1 not ready")
        return
    
    if not wait_for_port(8002, 60):
        print("❌ Validator 2 not ready")
        return
    
    print("✅ All validators are ready!")
    
    # Start miners
    print("\n📋 Starting Miners...")
    
    miner1 = start_component("Miner 1", "scripts/run_miner_core.py", {"MINER_ID": "1"})
    if not miner1:
        print("❌ Cannot proceed without Miner 1")
        return
    
    miner2 = start_component("Miner 2", "scripts/run_miner_core.py", {"MINER_ID": "2"})
    if not miner2:
        print("❌ Cannot proceed without Miner 2")
        return
    
    # Wait for miners to be ready
    print("\n⏳ Waiting for miners to be ready...")
    
    if not wait_for_port(8101, 60):
        print("❌ Miner 1 not ready")
        return
    
    if not wait_for_port(8102, 60):
        print("❌ Miner 2 not ready")
        return
    
    print("✅ All miners are ready!")
    
    # Test network health
    healthy_components = test_network_health()
    
    # Test P2P consensus
    p2p_ok = test_p2p_consensus()
    
    # Test task assignment
    successful_tasks = test_task_assignment()
    
    # Summary
    print("\n📊 NETWORK SUMMARY")
    print("=" * 40)
    print(f"✅ Healthy Components: {len(healthy_components)}/4")
    print(f"✅ P2P Consensus: {'OK' if p2p_ok else 'FAILED'}")
    print(f"✅ Task Assignment: {successful_tasks}/2 tasks sent")
    
    if len(healthy_components) == 4 and p2p_ok and successful_tasks > 0:
        print("\n🎉 COMPLETE NETWORK WITH P2P CONSENSUS READY!")
        print("💡 Validators can now communicate and update metagraph")
        print("💡 Miners can receive tasks and submit results")
    else:
        print("\n⚠️ NETWORK ISSUES DETECTED")
        print("💡 Check component logs for details")
    
    # Keep running
    print("\n⏱️  Network running... (Ctrl+C to stop)")
    try:
        while True:
            time.sleep(10)
            print("⏱️  Still running...")
    except KeyboardInterrupt:
        print("\n🛑 Stopping network...")
        for process in [validator1, validator2, miner1, miner2]:
            if process:
                process.terminate()
        print("✅ Network stopped")

if __name__ == "__main__":
    main() 