#!/usr/bin/env python3
"""
Simple sequential network startup
"""

import os
import sys
import time
import subprocess
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
            text=True,
        )

        print(f"✅ {name} started (PID: {process.pid})")
        return process

    except Exception as e:
        print(f"❌ Failed to start {name}: {e}")
        return None


def wait_for_port(port, timeout=30):
    """Wait for port to be available"""
    import socket
    import time

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(("localhost", port))
            sock.close()
            if result == 0:
                print(f"✅ Port {port} is ready")
                return True
        except:
            pass
        time.sleep(1)

    print(f"❌ Port {port} not ready after {timeout}s")
    return False


def main():
    """Main startup function"""
    print("🚀 SIMPLE NETWORK STARTUP")
    print("=" * 40)

    # Start miners first
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
    if not wait_for_port(8101, 30):
        print("❌ Miner 1 not ready")
        return

    if not wait_for_port(8102, 30):
        print("❌ Miner 2 not ready")
        return

    print("✅ All miners are ready!")

    # Start validators
    print("\n📋 Starting Validators...")

    validator1 = start_component(
        "Validator 1", "scripts/run_validator_core.py", {"VALIDATOR_ID": "1"}
    )
    if not validator1:
        print("❌ Cannot proceed without Validator 1")
        return

    validator2 = start_component(
        "Validator 2", "scripts/run_validator_core.py", {"VALIDATOR_ID": "2"}
    )
    if not validator2:
        print("❌ Cannot proceed without Validator 2")
        return

    # Wait for validators to be ready
    print("\n⏳ Waiting for validators to be ready...")
    if not wait_for_port(8001, 30):
        print("❌ Validator 1 not ready")
        return

    if not wait_for_port(8002, 30):
        print("❌ Validator 2 not ready")
        return

    print("✅ All validators are ready!")

    # Final check
    print("\n📊 NETWORK STATUS:")
    print("=" * 40)
    print("✅ Miner 1: Running on port 8101")
    print("✅ Miner 2: Running on port 8102")
    print("✅ Validator 1: Running on port 8001")
    print("✅ Validator 2: Running on port 8002")

    print("\n🎉 NETWORK STARTED SUCCESSFULLY!")
    print("💡 Now you can test task assignment")

    # Keep running
    try:
        while True:
            time.sleep(10)
            print("⏱️  Network still running... (Ctrl+C to stop)")
    except KeyboardInterrupt:
        print("\n🛑 Stopping network...")
        for process in [miner1, miner2, validator1, validator2]:
            if process:
                process.terminate()
        print("✅ Network stopped")


if __name__ == "__main__":
    main()
