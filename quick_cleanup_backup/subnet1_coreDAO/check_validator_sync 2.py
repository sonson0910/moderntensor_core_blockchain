#!/usr/bin/env python3
"""
Check if validators are running and synchronized
"""

import os
import sys
import time
import requests
import subprocess
from pathlib import Path
from dotenv import load_dotenv


def check_validator_sync():
    print("🔍 CHECKING VALIDATOR SYNCHRONIZATION")
    print("=" * 50)

    # Load environment
    load_dotenv()

    # Validator endpoints
    validators = [
        {"id": 1, "endpoint": "http://localhost:8001", "name": "Validator 1"},
        {"id": 2, "endpoint": "http://localhost:8002", "name": "Validator 2"},
        {"id": 3, "endpoint": "http://localhost:8003", "name": "Validator 3"},
    ]

    print("📋 1. CHECKING VALIDATOR API ENDPOINTS:")

    running_validators = []
    for validator in validators:
        print(f"\n  🛡️ {validator['name']}: {validator['endpoint']}")

        try:
            # Check if validator is responding
            response = requests.get(f"{validator['endpoint']}/health", timeout=5)
            if response.status_code == 200:
                print(f"    ✅ API responding")
                running_validators.append(validator)

                # Get validator status
                try:
                    status_response = requests.get(
                        f"{validator['endpoint']}/status", timeout=5
                    )
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        print(f"    📊 Status: {status_data.get('status', 'Unknown')}")
                        print(
                            f"    🔄 Cycle: {status_data.get('current_cycle', 'Unknown')}"
                        )
                        print(f"    ⏰ Uptime: {status_data.get('uptime', 'Unknown')}")
                except Exception as e:
                    print(f"    ⚠️ Cannot get status: {e}")
            else:
                print(f"    ❌ API not responding (Status: {response.status_code})")

        except requests.exceptions.ConnectionError:
            print(f"    ❌ Connection failed - Validator not running")
        except Exception as e:
            print(f"    ❌ Error: {e}")

    print(
        f"\n📊 SUMMARY: {len(running_validators)}/{len(validators)} validators running"
    )

    # Check if consensus is happening
    print("\n📋 2. CHECKING CONSENSUS ACTIVITY:")

    if running_validators:
        # Check consensus logs from one validator
        validator = running_validators[0]
        print(f"\n  🔍 Checking consensus logs from {validator['name']}:")

        try:
            # Try to get consensus status
            consensus_response = requests.get(
                f"{validator['endpoint']}/consensus/status", timeout=5
            )
            if consensus_response.status_code == 200:
                consensus_data = consensus_response.json()
                print(f"    ✅ Consensus Status: {consensus_data}")
            else:
                print(f"    ⚠️ Cannot get consensus status")

        except Exception as e:
            print(f"    ❌ Error checking consensus: {e}")
    else:
        print("  ❌ No validators running - cannot check consensus")

    # Check process status
    print("\n📋 3. CHECKING PROCESS STATUS:")

    validator_processes = []
    for i in range(1, 4):
        try:
            # Check if validator process is running
            result = subprocess.run(
                ["pgrep", "-f", f"run_validator.*{i}"], capture_output=True, text=True
            )
            if result.returncode == 0:
                pids = result.stdout.strip().split("\n")
                print(f"  ✅ Validator {i} running (PIDs: {pids})")
                validator_processes.append(i)
            else:
                print(f"  ❌ Validator {i} not running")
        except Exception as e:
            print(f"  ❌ Error checking Validator {i}: {e}")

    print(f"\n📊 Process Summary: {len(validator_processes)}/3 validator processes")

    # Recommendations
    print("\n📋 4. RECOMMENDATIONS:")

    if len(running_validators) < 3:
        print("❌ ISSUES DETECTED:")
        print("   1. Not all validators are running")
        print("   2. Consensus cannot happen without sufficient validators")
        print("   3. Metagraph updates may fail")

        print("\n🔧 SOLUTIONS:")
        print("   1. Start missing validators:")
        for i in range(1, 4):
            if i not in [v["id"] for v in running_validators]:
                print(
                    f"      - python scripts/run_validator_core.py (for Validator {i})"
                )

        print("   2. Check validator logs for errors")
        print("   3. Verify environment variables are correct")

    elif len(running_validators) == 3:
        print("✅ ALL VALIDATORS RUNNING")
        print("   - Consensus should be working")
        print("   - Check timing synchronization")
        print("   - Monitor consensus logs")

        print("\n🔍 NEXT STEPS:")
        print("   1. Check consensus timing configuration")
        print("   2. Monitor metagraph update intervals")
        print("   3. Verify transaction submission")


if __name__ == "__main__":
    check_validator_sync()
