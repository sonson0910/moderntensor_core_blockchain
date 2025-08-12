#!/usr/bin/env python3
"""
Simple network startup for P2P consensus
"""

import os
import sys
import time
import subprocess
from pathlib import Path

def start_background(script, env_vars=None):
    """Start a component in background"""
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)
    
    try:
        process = subprocess.Popen(
            [sys.executable, script],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return process
    except Exception as e:
        print(f"❌ Failed to start {script}: {e}")
        return None

def main():
    """Main function"""
    print("🚀 STARTING SIMPLE P2P NETWORK")
    print("=" * 40)
    
    processes = []
    
    # Start validators
    print("📋 Starting Validators...")
    
    v1 = start_background("scripts/run_validator_core.py", {"VALIDATOR_ID": "1"})
    if v1:
        print("✅ Validator 1 started")
        processes.append(("Validator 1", v1))
    
    time.sleep(3)
    
    v2 = start_background("scripts/run_validator_core.py", {"VALIDATOR_ID": "2"})
    if v2:
        print("✅ Validator 2 started")
        processes.append(("Validator 2", v2))
    
    # Start miners
    print("📋 Starting Miners...")
    
    m1 = start_background("scripts/run_miner_core.py", {"MINER_ID": "1"})
    if m1:
        print("✅ Miner 1 started")
        processes.append(("Miner 1", m1))
    
    m2 = start_background("scripts/run_miner_core.py", {"MINER_ID": "2"})
    if m2:
        print("✅ Miner 2 started")
        processes.append(("Miner 2", m2))
    
    print(f"\n✅ Started {len(processes)} components")
    
    # Wait for startup
    print("⏳ Waiting 30s for components to initialize...")
    time.sleep(30)
    
    # Check ports
    print("🔍 Checking ports...")
    import socket
    
    ports = [8001, 8002, 8101, 8102]
    for port in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            if result == 0:
                print(f"✅ Port {port}: Listening")
            else:
                print(f"❌ Port {port}: Not listening")
        except:
            print(f"❌ Port {port}: Error checking")
    
    print("\n🎉 NETWORK STARTED!")
    print("💡 Components are running in background")
    print("💡 Use Ctrl+C to stop")
    
    try:
        while True:
            time.sleep(10)
            print("⏱️  Still running...")
    except KeyboardInterrupt:
        print("\n🛑 Stopping network...")
        for name, process in processes:
            try:
                process.terminate()
                print(f"✅ {name} stopped")
            except:
                print(f"❌ Failed to stop {name}")
        print("✅ Network stopped")

if __name__ == "__main__":
    main() 