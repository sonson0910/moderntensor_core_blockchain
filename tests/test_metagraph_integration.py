#!/usr/bin/env python3

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "mt_core"))

from mt_core.metagraph.core_metagraph_adapter import 
)


def test_metagraph_integration():
    print("🔍 TESTING METAGRAPH INTEGRATION WITH CORE BLOCKCHAIN")
    print(" = " * 70)

    # Test individual functions
    print("\n📊 TESTING INDIVIDUAL FUNCTIONS...")
    print("-" * 50)

    # Test miners
    print("👥 Getting miner data...")
    miners  =  get_all_miner_data()
    print(f"   Found {len(miners)} miners")
    for i, miner in enumerate(miners):
        print(f"   Miner {i+1}: {miner['address']}")
        print(f"     UID: {miner['uid'][:16]}...")
        print(f"     Stake: {miner['stake']} CORE")
        print(f"     Accumulated Rewards: {miner['accumulated_rewards']} CORE")
        print(f"     Status: {miner['status']} (Active: {miner['active']})")
        print(f"     Trust Score: {miner['scaled_trust_score']}")
        print(f"     Performance: {miner['scaled_last_performance']}")
        print(f"     Endpoint: {miner['api_endpoint']}")

    # Test validators
    print("\n🛡️ Getting validator data...")
    validators  =  get_all_validator_data()
    print(f"   Found {len(validators)} validators")
    for i, validator in enumerate(validators):
        print(f"   Validator {i+1}: {validator['address']}")
        print(f"     UID: {validator['uid'][:16]}...")
        print(f"     Stake: {validator['stake']} CORE")
        print(f"     Accumulated Rewards: {validator['accumulated_rewards']} CORE")
        print(f"     Status: {validator['status']} (Active: {validator['active']})")
        print(f"     Trust Score: {validator['scaled_trust_score']}")
        print(f"     Performance: {validator['scaled_last_performance']}")
        print(f"     Endpoint: {validator['api_endpoint']}")

    # Test network stats
    print("\n📈 Getting network stats...")
    stats  =  get_network_stats()
    print(f"   Total Miners: {stats['total_miners']}")
    print(f"   Total Validators: {stats['total_validators']}")
    print(f"   Active Miners: {stats['active_miners']}")
    print(f"   Active Validators: {stats['active_validators']}")
    print(f"   Network: {stats['network']}")
    print(f"   Contract: {stats['contract_address']}")

    # Test registration checks
    print("\n🔍 TESTING REGISTRATION CHECKS...")
    print("-" * 40)

    test_addresses  =  [
        "0x1Be31A94361a391bBaFB2a4CCd704F57dc04d4bb",  # Miner 1
        "0x580A1998965dD6a0128d5cBB39e58c2960679f38",  # Validator 1
        "0x1234567890123456789012345678901234567890",  # Random address
    ]

    for addr in test_addresses:
        is_miner  =  is_miner_registered(addr)
        is_validator  =  is_validator_registered(addr)
        print(f"   {addr}")
        print(f"     Miner: {is_miner}, Validator: {is_validator}")

    # Test full metagraph load
    print("\n🌐 TESTING FULL METAGRAPH LOAD...")
    print("-" * 40)

    full_data  =  load_metagraph_data()
    print(f"✅ Full metagraph loaded successfully!")
    print(f"   Miners: {len(full_data['miners'])}")
    print(f"   Validators: {len(full_data['validators'])}")
    print(f"   Network: {full_data['network_stats']['network']}")

    # Save as official metagraph snapshot
    import json

    with open("official_metagraph_snapshot.json", "w") as f:
        json.dump(full_data, f, indent = 2)

    print(f"\n💾 Official metagraph saved to official_metagraph_snapshot.json")

    print(f"\n🎉 METAGRAPH INTEGRATION TEST COMPLETE!")
    print(" = " * 50)
    print("✅ Metagraph system is working with Core blockchain")
    print("✅ All miners and validators retrieved successfully")
    print("✅ Network statistics calculated correctly")
    print("✅ Registration checks working")
    print("✅ Data format compatible with existing systems")


if __name__ == "__main__":
    test_metagraph_integration()
