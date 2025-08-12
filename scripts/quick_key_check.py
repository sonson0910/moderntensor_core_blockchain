#!/usr/bin/env python3
"""
Quick script to check keys registered on blockchain vs .env file
"""""
import os
import sys
from pathlib import Path

# Add paths
project_root  =  Path(__file__).parent
sys.path.insert(0, str(project_root))

from mt_core.metagraph.core_metagraph_adapter import CoreMetagraphClient
from mt_core.config.settings import settings


def quick_key_check():
    """Quick check of registered keys vs .env"""""
    print("🔍 QUICK KEY CHECK: BLOCKCHAIN vs .ENV")
    print(" = " * 60)

    # Load .env from subnet1_aptos
    env_file  =  project_root.parent / "subnet1_aptos" / ".env"
    if env_file.exists():
        from dotenv import load_dotenv

        load_dotenv(env_file)
        print(f"✅ Loaded .env from: {env_file}")
    else:
        print(f"❌ .env not found at: {env_file}")
        return

    # Get .env keys
    print("\n📋 KEYS FROM .ENV:")
    print("-" * 30)

    miners_env  =  {
        "miner_1": {
            "address": os.getenv("MINER_1_ADDRESS", "NOT_SET"),
            "endpoint": os.getenv("MINER_1_API_ENDPOINT", "NOT_SET"),
            "port": os.getenv("MINER_1_PORT", "NOT_SET"),
        },
        "miner_2": {
            "address": os.getenv("MINER_2_ADDRESS", "NOT_SET"),
            "endpoint": os.getenv("MINER_2_API_ENDPOINT", "NOT_SET"),
            "port": os.getenv("MINER_2_PORT", "NOT_SET"),
        },
    }

    validators_env  =  {
        "validator_1": {
            "address": os.getenv("VALIDATOR_1_ADDRESS", "NOT_SET"),
            "endpoint": os.getenv("VALIDATOR_1_API_ENDPOINT", "NOT_SET"),
            "port": os.getenv("VALIDATOR_1_PORT", "NOT_SET"),
        },
        "validator_2": {
            "address": os.getenv("VALIDATOR_2_ADDRESS", "NOT_SET"),
            "endpoint": os.getenv("VALIDATOR_2_API_ENDPOINT", "NOT_SET"),
            "port": os.getenv("VALIDATOR_2_PORT", "NOT_SET"),
        },
    }

    for name, info in miners_env.items():
        print(f"🔧 {name}:")
        print(f"   Address: {info['address']}")
        print(f"   Endpoint: {info['endpoint']}")
        print(f"   Port: {info['port']}")

    for name, info in validators_env.items():
        print(f"🛡️ {name}:")
        print(f"   Address: {info['address']}")
        print(f"   Endpoint: {info['endpoint']}")
        print(f"   Port: {info['port']}")

    # Get blockchain data with timeout
    print("\n🌐 KEYS FROM BLOCKCHAIN:")
    print("-" * 30)

    try:
        client  =  CoreMetagraphClient()

        # Get miner addresses (quick)
        miner_addrs  =  client.get_all_miners()
        print(f"📊 Found {len(miner_addrs)} miners on blockchain:")
        for i, addr in enumerate(miner_addrs):
            print(f"   Miner {i+1}: {addr}")

        # Get validator addresses (quick)
        validator_addrs  =  client.get_all_validators()
        print(f"🛡️ Found {len(validator_addrs)} validators on blockchain:")
        for i, addr in enumerate(validator_addrs):
            print(f"   Validator {i+1}: {addr}")

    except Exception as e:
        print(f"❌ Error getting blockchain data: {e}")
        return

    # Compare
    print("\n🔍 COMPARISON:")
    print("-" * 30)

    # Check miners
    env_miner_addrs  =  [
        miners_env["miner_1"]["address"],
        miners_env["miner_2"]["address"],
    ]
    for i, addr in enumerate(env_miner_addrs):
        if addr in miner_addrs:
            print(f"✅ Miner {i+1} address {addr} FOUND on blockchain")
        else:
            print(f"❌ Miner {i+1} address {addr} NOT FOUND on blockchain")

    # Check validators
    env_validator_addrs  =  [
        validators_env["validator_1"]["address"],
        validators_env["validator_2"]["address"],
    ]
    for i, addr in enumerate(env_validator_addrs):
        if addr in validator_addrs:
            print(f"✅ Validator {i+1} address {addr} FOUND on blockchain")
        else:
            print(f"❌ Validator {i+1} address {addr} NOT FOUND on blockchain")


if __name__ == "__main__":
    quick_key_check()
