#!/usr/bin/env python3
"""
Check endpoints of registered keys on blockchain
"""
import sys
from pathlib import Path

# Add paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mt_core.metagraph.core_metagraph_adapter import CoreMetagraphClient


def check_registered_endpoints():
    """Check what endpoints are registered for the blockchain keys"""
    print("🔍 REGISTERED KEYS & ENDPOINTS ON BLOCKCHAIN:")
    print("=" * 60)

    try:
        client = CoreMetagraphClient()

        # Check miners
        miner_addrs = client.get_all_miners()
        print(f"\n📊 MINERS ({len(miner_addrs)}):")
        print("-" * 40)

        for i, addr in enumerate(miner_addrs):
            try:
                info = client.get_miner_info(addr)
                if info:
                    print(f"🔧 Miner {i+1}: {addr}")
                    print(f"   Endpoint: {info.get('api_endpoint', 'NOT_SET')}")
                    print(f"   Active: {info.get('active', False)}")
                    print(f"   Stake: {info.get('stake', 0)} CORE")
                else:
                    print(f"🔧 Miner {i+1}: {addr} - NO INFO")
            except Exception as e:
                print(f"🔧 Miner {i+1}: {addr} - ERROR: {e}")

        # Check validators
        validator_addrs = client.get_all_validators()
        print(f"\n🛡️ VALIDATORS ({len(validator_addrs)}):")
        print("-" * 40)

        for i, addr in enumerate(validator_addrs):
            try:
                info = client.get_validator_info(addr)
                if info:
                    print(f"🛡️ Validator {i+1}: {addr}")
                    print(f"   Endpoint: {info.get('api_endpoint', 'NOT_SET')}")
                    print(f"   Active: {info.get('active', False)}")
                    print(f"   Stake: {info.get('stake', 0)} CORE")
                else:
                    print(f"🛡️ Validator {i+1}: {addr} - NO INFO")
            except Exception as e:
                print(f"🛡️ Validator {i+1}: {addr} - ERROR: {e}")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    check_registered_endpoints()
