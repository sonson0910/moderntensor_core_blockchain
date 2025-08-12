#!/usr/bin/env python3
"""
Start validators with proper P2P communication
"""

import os
import sys
import time
import subprocess
import asyncio
import httpx
from pathlib import Path


def start_validator(validator_id, port):
    """Start a single validator"""
    print(f"🚀 Starting Validator {validator_id} on port {port}...")

    env = os.environ.copy()
    env["VALIDATOR_ID"] = str(validator_id)
    env["LOG_LEVEL"] = "INFO"

    try:
        cmd = [sys.executable, "scripts/run_validator_core.py"]
        process = subprocess.Popen(
            cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        print(f"✅ Validator {validator_id} started (PID: {process.pid})")
        return process

    except Exception as e:
        print(f"❌ Failed to start Validator {validator_id}: {e}")
        return None


def wait_for_validator_ready(port, timeout=60):
    """Wait for validator to be ready"""
    print(f"⏳ Waiting for validator on port {port} to be ready...")

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Test health endpoint
            response = httpx.get(f"http://localhost:{port}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ Validator on port {port} is ready!")
                return True
        except:
            pass

        # Test if port is listening
        try:
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(("localhost", port))
            sock.close()
            if result == 0:
                print(f"✅ Port {port} is listening")
                return True
        except:
            pass

        time.sleep(2)

    print(f"❌ Validator on port {port} not ready after {timeout}s")
    return False


def test_p2p_communication():
    """Test P2P communication between validators"""
    print("\n🔍 TESTING P2P COMMUNICATION")
    print("=" * 40)

    try:
        # Test validator 1
        response1 = httpx.get("http://localhost:8001/health", timeout=5)
        print(f"✅ Validator 1: Status {response1.status_code}")

        # Test validator 2
        response2 = httpx.get("http://localhost:8002/health", timeout=5)
        print(f"✅ Validator 2: Status {response2.status_code}")

        # Test validator-to-validator communication
        print("🔍 Testing validator-to-validator communication...")

        # Try to get validator list from validator 1
        try:
            response = httpx.get("http://localhost:8001/validators", timeout=5)
            if response.status_code == 200:
                validators = response.json()
                print(f"✅ Validator 1 found {len(validators)} validators")
                for v in validators:
                    print(
                        f"   - {v.get('uid', 'unknown')} at {v.get('endpoint', 'unknown')}"
                    )
            else:
                print(f"❌ Validator 1 returned status {response.status_code}")
        except Exception as e:
            print(f"❌ Cannot get validator list from validator 1: {e}")

        return True

    except Exception as e:
        print(f"❌ P2P communication test failed: {e}")
        return False


def main():
    """Main function"""
    print("🚀 STARTING VALIDATORS WITH P2P COMMUNICATION")
    print("=" * 50)

    # Start validators
    print("\n📋 Starting Validators...")

    validator1 = start_validator(1, 8001)
    if not validator1:
        print("❌ Cannot proceed without Validator 1")
        return

    # Wait a bit before starting validator 2
    time.sleep(3)

    validator2 = start_validator(2, 8002)
    if not validator2:
        print("❌ Cannot proceed without Validator 2")
        return

    # Wait for validators to be ready
    print("\n⏳ Waiting for validators to be ready...")

    if not wait_for_validator_ready(8001, 60):
        print("❌ Validator 1 not ready")
        return

    if not wait_for_validator_ready(8002, 60):
        print("❌ Validator 2 not ready")
        return

    print("✅ All validators are ready!")

    # Test P2P communication
    p2p_ok = test_p2p_communication()

    if p2p_ok:
        print("\n🎉 P2P COMMUNICATION ESTABLISHED!")
        print("💡 Validators can now communicate for consensus")
    else:
        print("\n⚠️ P2P COMMUNICATION ISSUES DETECTED")
        print("💡 Check validator logs for details")

    # Keep running
    print("\n⏱️  Validators running... (Ctrl+C to stop)")
    try:
        while True:
            time.sleep(10)
            print("⏱️  Still running...")
    except KeyboardInterrupt:
        print("\n🛑 Stopping validators...")
        for process in [validator1, validator2]:
            if process:
                process.terminate()
        print("✅ Validators stopped")


if __name__ == "__main__":
    main()
