#!/usr/bin/env python3
"""
Quick verification script for ModernTensor Core improvements
Tests all major components to ensure they work correctly
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_imports():
    """Test that all new modules can be imported successfully"""
    print("🧪 Testing imports...")

    try:
        # Test core modules
        from mt_core.async_client import CoreAsyncClient, get_async_client
        from mt_core.bcs import BCSEncoder, bcs_encode, canonical_hash
        from mt_core.account import CoreAccount

        # Test config system
        from mt_core.config.config_loader import (
            get_config,
            get_blockchain_config,
            get_consensus_config,
            get_staking_config,
        )

        # Test data types
        from mt_core.core.datatypes import MinerInfo, ValidatorInfo, TaskAssignment

        print("✅ All imports successful!")
        return True

    except Exception as e:
        print(f"❌ Import error: {e}")
        return False


def test_configuration_system():
    """Test the new YAML configuration system"""
    print("🧪 Testing configuration system...")

    try:
        from mt_core.config.config_loader import get_config

        config = get_config()

        # Test blockchain config
        blockchain_config = config.blockchain
        assert blockchain_config.network in ["testnet", "mainnet"]
        assert blockchain_config.testnet_url.startswith("https://")

        # Test consensus config
        consensus_config = config.consensus
        assert consensus_config.cycle_length > 0
        assert consensus_config.selection.miners_per_cycle > 0

        # Test staking config
        staking_config = config.staking
        assert staking_config.dual_staking["enabled"] is True

        # Test tier configuration
        base_tier = config.get_staking_tier_config("base")
        assert base_tier is not None
        assert base_tier.multiplier == 1.0

        print("✅ Configuration system working correctly!")
        return True

    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False


def test_account_creation():
    """Test Core account creation and validation"""
    print("🧪 Testing account creation...")

    try:
        from mt_core.account import CoreAccount

        # Create test account
        account = CoreAccount()

        assert account.address is not None
        assert account.private_key is not None
        assert len(account.address) == 42  # 0x + 40 hex chars
        assert account.address.startswith("0x")

        # Test message signing
        message = "Test message"
        signature = account.sign_message(message)
        assert signature is not None

        print(f"✅ Account created: {account.address}")
        return True

    except Exception as e:
        print(f"❌ Account creation error: {e}")
        return False


def test_bcs_serialization():
    """Test BCS serialization functionality"""
    print("🧪 Testing BCS serialization...")

    try:
        from mt_core.bcs import BCSEncoder, bcs_encode, canonical_hash
        from mt_core.account import CoreAccount

        # Test basic encoding
        encoder = BCSEncoder()
        encoder.encode_u64(123456789)
        encoder.encode_string("test_string")
        encoder.encode_bool(True)

        # Test address encoding
        account = CoreAccount()
        encoder.encode_address(account.address)

        serialized = encoder.to_bytes()
        assert len(serialized) > 0

        # Test struct encoding
        test_data = {
            "miner_uid": "test_miner_123",
            "subnet_uid": 1,
            "stake_amount": 1000,
            "owner": account.address,
        }

        canonical_data = bcs_encode(test_data)
        assert len(canonical_data) > 0

        # Test canonical hash
        hash_result = canonical_hash(test_data)
        assert len(hash_result) == 32  # Keccak256 produces 32 bytes

        print("✅ BCS serialization working correctly!")
        return True

    except Exception as e:
        print(f"❌ BCS serialization error: {e}")
        return False


async def test_async_client():
    """Test async client functionality"""
    print("🧪 Testing async client...")

    try:
        from mt_core.async_client import CoreAsyncClient
        from mt_core.config.config_loader import get_blockchain_config
        from mt_core.account import CoreAccount

        config = get_blockchain_config()
        account = CoreAccount()

        async with CoreAsyncClient(config.testnet_url) as client:
            # Test connection
            assert client.web3 is not None

            # Test balance checking (will be 0 on testnet)
            balance = await client.get_balance(account.address)
            assert balance >= 0

            # Test gas price retrieval
            gas_price = await client.get_gas_price()
            assert gas_price > 0

            # Test nonce retrieval
            nonce = await client.get_transaction_count(account.address)
            assert nonce >= 0

        print("✅ Async client working correctly!")
        return True

    except Exception as e:
        print(f"❌ Async client error: {e}")
        return False


def test_data_structures():
    """Test miner and validator data structures"""
    print("🧪 Testing data structures...")

    try:
        from mt_core.core.datatypes import MinerInfo, ValidatorInfo, TaskAssignment
        from mt_core.account import CoreAccount
        import time

        account = CoreAccount()

        # Test MinerInfo
        miner_info = MinerInfo(
            uid="test_miner_001",
            address=account.address,
            api_endpoint="http://localhost:8100",
            trust_score=0.85,
            weight=1.5,
            stake=1000.0,
            last_selected_time=int(time.time()),
            performance_history=[0.8, 0.9, 0.85, 0.95],
            subnet_uid=1,
        )

        assert miner_info.uid == "test_miner_001"
        assert miner_info.trust_score == 0.85
        assert len(miner_info.performance_history) == 4

        # Test ValidatorInfo
        validator_info = ValidatorInfo(
            uid="test_validator_001",
            address=account.address,
            api_endpoint="http://localhost:8001",
            trust_score=0.9,
            weight=2.0,
            stake=5000.0,
            last_performance=0.92,
            subnet_uid=1,
        )

        assert validator_info.uid == "test_validator_001"
        assert validator_info.last_performance == 0.92

        # Test TaskAssignment
        task = TaskAssignment(
            task_id="task_001",
            task_data={"prompt": "Generate an image of a cat", "steps": 20},
            miner_uid=miner_info.uid,
            validator_uid=validator_info.uid,
            timestamp_sent=time.time(),
            expected_result_format="image_url",
        )

        assert task.task_id == "task_001"
        assert "prompt" in task.task_data

        print("✅ Data structures working correctly!")
        return True

    except Exception as e:
        print(f"❌ Data structures error: {e}")
        return False


async def main():
    """Run all verification tests"""
    print("🚀 ModernTensor Core - Improvements Verification")
    print("=" * 50)

    tests = [
        ("Imports", test_imports),
        ("Configuration System", test_configuration_system),
        ("Account Creation", test_account_creation),
        ("BCS Serialization", test_bcs_serialization),
        ("Async Client", test_async_client),
        ("Data Structures", test_data_structures),
    ]

    results = {}

    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} test failed: {e}")
            results[test_name] = False

    # Summary
    print("\n" + "=" * 50)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 50)

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")

    print(f"\n🎯 Overall Result: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All improvements verified successfully!")
        print("✅ ModernTensor Core is ready for production!")
        return True
    else:
        print("⚠️  Some improvements need attention.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
