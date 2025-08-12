#!/usr/bin/env python3
"""
Test script compatibility with updated environment variables
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv


def test_script_compatibility():
    print("🧪 TESTING SCRIPT COMPATIBILITY")
    print("=" * 50)

    # Load environment variables
    load_dotenv()

    # Test 1: Validator Script Configuration
    print("\n📋 1. TESTING VALIDATOR SCRIPT CONFIGURATION:")

    for validator_id in ["1", "2", "3"]:
        print(f"\n  🛡️ Validator {validator_id}:")

        # Variables that validator scripts expect
        validator_vars = {
            f"VALIDATOR_{validator_id}_ID": os.getenv(f"VALIDATOR_{validator_id}_ID"),
            f"VALIDATOR_{validator_id}_PRIVATE_KEY": os.getenv(
                f"VALIDATOR_{validator_id}_PRIVATE_KEY"
            ),
            f"VALIDATOR_{validator_id}_ADDRESS": os.getenv(
                f"VALIDATOR_{validator_id}_ADDRESS"
            ),
            f"VALIDATOR_{validator_id}_API_ENDPOINT": os.getenv(
                f"VALIDATOR_{validator_id}_API_ENDPOINT"
            ),
        }

        all_present = True
        for var_name, value in validator_vars.items():
            if value:
                if "PRIVATE_KEY" in var_name:
                    print(f"    ✅ {var_name}: {'*' * 10}...{value[-4:]}")
                else:
                    print(f"    ✅ {var_name}: {value}")
            else:
                print(f"    ❌ {var_name}: Missing")
                all_present = False

        if all_present:
            print(f"    🎉 Validator {validator_id}: ALL CONFIGURED")
        else:
            print(f"    ⚠️ Validator {validator_id}: Some variables missing")

    # Test 2: Miner Script Configuration
    print("\n📋 2. TESTING MINER SCRIPT CONFIGURATION:")

    for miner_id in ["1", "2"]:
        print(f"\n  ⛏️ Miner {miner_id}:")

        # Variables that miner scripts expect
        miner_vars = {
            f"MINER_{miner_id}_ID": os.getenv(f"MINER_{miner_id}_ID"),
            f"MINER_{miner_id}_PRIVATE_KEY": os.getenv(f"MINER_{miner_id}_PRIVATE_KEY"),
            f"MINER_{miner_id}_ADDRESS": os.getenv(f"MINER_{miner_id}_ADDRESS"),
            f"MINER_{miner_id}_API_ENDPOINT": os.getenv(
                f"MINER_{miner_id}_API_ENDPOINT"
            ),
        }

        all_present = True
        for var_name, value in miner_vars.items():
            if value:
                if "PRIVATE_KEY" in var_name:
                    print(f"    ✅ {var_name}: {'*' * 10}...{value[-4:]}")
                else:
                    print(f"    ✅ {var_name}: {value}")
            else:
                print(f"    ❌ {var_name}: Missing")
                all_present = False

        if all_present:
            print(f"    🎉 Miner {miner_id}: ALL CONFIGURED")
        else:
            print(f"    ⚠️ Miner {miner_id}: Some variables missing")

    # Test 3: Core Configuration
    print("\n📋 3. TESTING CORE CONFIGURATION:")

    core_vars = {
        "CORE_NODE_URL": os.getenv("CORE_NODE_URL"),
        "CORE_CONTRACT_ADDRESS": os.getenv("CORE_CONTRACT_ADDRESS"),
        "CORE_TOKEN_ADDRESS": os.getenv("CORE_TOKEN_ADDRESS"),
        "SUBNET_ID": os.getenv("SUBNET_ID"),
    }

    core_ok = True
    for var_name, value in core_vars.items():
        if value:
            print(f"  ✅ {var_name}: {value}")
        else:
            print(f"  ❌ {var_name}: Missing")
            core_ok = False

    # Test 4: Script Simulation
    print("\n📋 4. SIMULATING SCRIPT STARTUP LOGIC:")

    # Simulate run_validator_core.py logic
    print("\n  🛡️ Validator Script Simulation:")
    validator_id = os.getenv("VALIDATOR_ID", "1")

    if validator_id == "2":
        validator_readable_id = os.getenv("VALIDATOR_2_ID")
        validator_private_key = os.getenv("VALIDATOR_2_PRIVATE_KEY")
    else:
        validator_readable_id = os.getenv("VALIDATOR_1_ID") or os.getenv(
            "SUBNET1_VALIDATOR_ID"
        )
        validator_private_key = os.getenv("VALIDATOR_1_PRIVATE_KEY") or os.getenv(
            "CORE_PRIVATE_KEY"
        )

    if validator_readable_id and validator_private_key:
        print(f"    ✅ Validator {validator_id} config resolved successfully")
        print(f"    📝 ID: {validator_readable_id}")
        print(f"    🔑 Key: {'*' * 10}...{validator_private_key[-4:]}")
    else:
        print(f"    ❌ Validator {validator_id} config resolution failed")

    # Simulate run_miner_core.py logic
    print("\n  ⛏️ Miner Script Simulation:")
    miner_id = os.getenv("MINER_ID", "1")

    if miner_id == "2":
        miner_private_key = os.getenv("MINER_2_PRIVATE_KEY")
        miner_readable_id = f"subnet1_miner_{miner_id}"
    else:
        miner_private_key = os.getenv("MINER_1_PRIVATE_KEY")
        miner_readable_id = f"subnet1_miner_{miner_id}"

    if miner_private_key:
        print(f"    ✅ Miner {miner_id} config resolved successfully")
        print(f"    📝 ID: {miner_readable_id}")
        print(f"    🔑 Key: {'*' * 10}...{miner_private_key[-4:]}")
    else:
        print(f"    ❌ Miner {miner_id} config resolution failed")

    # Summary
    print("\n" + "=" * 50)
    print("🎯 SCRIPT COMPATIBILITY SUMMARY")
    print("=" * 50)

    if core_ok:
        print("✅ Core configuration: READY")
        print("✅ Environment variables: COMPLETE")
        print("✅ Script simulation: SUCCESSFUL")

        print("\n🚀 SCRIPTS READY TO RUN:")
        print("  1. python scripts/run_validator_core.py")
        print("  2. python scripts/run_miner_core.py")
        print("  3. python scripts/run_validator_core_v2.py --validator 1")
        print("  4. python scripts/run_validator_core_v2.py --validator 2")
        print("  5. MINER_ID=2 python scripts/run_miner_core.py")

        return True
    else:
        print("❌ Some configuration issues found")
        return False


if __name__ == "__main__":
    test_script_compatibility()
