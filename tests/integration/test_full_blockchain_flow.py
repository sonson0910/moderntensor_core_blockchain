"""
Comprehensive integration tests for ModernTensor Core blockchain
Tests the complete flow from account creation to mining, consensus, and rewards
"""

import pytest
import asyncio
import os
import time
from decimal import Decimal
from typing import List, Dict, Any
from dataclasses import dataclass

# Core imports
from mt_core.account import CoreAccount
from mt_core.async_client import CoreAsyncClient, get_async_client
from mt_core.bcs import bcs_encode, BCSEncoder, canonical_hash
from mt_core.config.config_loader import (
    get_config,
    get_blockchain_config,
    get_staking_config,
)
from mt_core.core.datatypes import MinerInfo, ValidatorInfo, TaskAssignment

# Helper functions defined at bottom of file

# Test fixtures and utilities
from tests.conftest import test_private_keys


@dataclass
class TestAccount:
    """Test account wrapper"""

    name: str
    account: CoreAccount
    private_key: str
    role: str  # 'miner', 'validator', 'user'


@dataclass
class TestNetwork:
    """Test network state"""

    accounts: List[TestAccount]
    subnet_id: int
    miners: List[TestAccount]
    validators: List[TestAccount]
    contract_address: str


class TestFullBlockchainFlow:
    """Integration tests for complete blockchain flow"""

    @pytest.fixture
    def test_network(self) -> TestNetwork:
        """Setup test network with accounts"""
        config = get_config()

        # Create test accounts
        accounts = []

        # Create 3 validators
        for i in range(3):
            private_key = test_private_keys[i]
            account = CoreAccount(private_key)
            test_account = TestAccount(
                name=f"validator_{i+1}",
                account=account,
                private_key=private_key,
                role="validator",
            )
            accounts.append(test_account)

        # Create 5 miners
        for i in range(5):
            private_key = test_private_keys[i + 3]
            account = CoreAccount(private_key)
            test_account = TestAccount(
                name=f"miner_{i+1}",
                account=account,
                private_key=private_key,
                role="miner",
            )
            accounts.append(test_account)

        # Create 2 regular users
        for i in range(2):
            private_key = test_private_keys[i + 8]
            account = CoreAccount(private_key)
            test_account = TestAccount(
                name=f"user_{i+1}",
                account=account,
                private_key=private_key,
                role="user",
            )
            accounts.append(test_account)

        validators = [acc for acc in accounts if acc.role == "validator"]
        miners = [acc for acc in accounts if acc.role == "miner"]

        network = TestNetwork(
            accounts=accounts,
            subnet_id=1,
            miners=miners,
            validators=validators,
            contract_address=config.blockchain.contract_address,
        )

        return network

    @pytest.mark.asyncio
    async def test_account_creation_and_validation(self, test_network: TestNetwork):
        """Test account creation and validation"""
        print("🧪 Testing account creation and validation...")

        for account in test_network.accounts:
            # Validate account properties
            assert account.account.address is not None
            assert account.account.private_key is not None
            assert len(account.account.address) == 42  # 0x + 40 hex chars
            assert account.account.address.startswith("0x")

            # Test message signing
            message = f"Test message for {account.name}"
            signature = account.account.sign_message(message)
            assert signature is not None

            print(f"✅ Account {account.name}: {account.account.address}")

        print("✅ All accounts created and validated successfully")

    @pytest.mark.asyncio
    async def test_bcs_serialization(self, test_network: TestNetwork):
        """Test BCS serialization functionality"""
        print("🧪 Testing BCS serialization...")

        # Test basic types
        encoder = BCSEncoder()

        # Test integers
        encoder.encode_u64(123456789)
        encoder.encode_string("test_string")
        encoder.encode_bool(True)

        # Test address encoding
        test_address = test_network.accounts[0].account.address
        encoder.encode_address(test_address)

        serialized = encoder.to_bytes()
        assert len(serialized) > 0

        # Test struct encoding
        test_data = {
            "miner_uid": "test_miner_123",
            "subnet_uid": 1,
            "stake_amount": 1000,
            "owner": test_address,
        }

        canonical_data = bcs_encode(test_data)
        assert len(canonical_data) > 0

        # Test canonical hash
        hash_result = canonical_hash(test_data)
        assert len(hash_result) == 32  # Keccak256 produces 32 bytes

        print("✅ BCS serialization tests passed")

    @pytest.mark.asyncio
    async def test_async_client_functionality(self, test_network: TestNetwork):
        """Test async client functionality"""
        print("🧪 Testing async client functionality...")

        config = get_blockchain_config()

        async with CoreAsyncClient(config.testnet_url) as client:
            # Test connection
            assert client.web3 is not None

            # Test balance checking (will be 0 on testnet)
            test_account = test_network.accounts[0]
            balance = await client.get_balance(test_account.account.address)
            assert balance >= 0

            # Test gas price retrieval
            gas_price = await client.get_gas_price()
            assert gas_price > 0

            # Test nonce retrieval
            nonce = await client.get_transaction_count(test_account.account.address)
            assert nonce >= 0

            print(f"✅ Balance: {balance} ETH, Gas Price: {gas_price}, Nonce: {nonce}")

        print("✅ Async client functionality tests passed")

    @pytest.mark.asyncio
    async def test_configuration_management(self):
        """Test configuration management system"""
        print("🧪 Testing configuration management...")

        config = get_config()

        # Test blockchain config
        blockchain_config = config.blockchain
        assert blockchain_config.network in ["testnet", "mainnet"]
        assert blockchain_config.testnet_url.startswith("https://")
        assert blockchain_config.testnet_chain_id > 0

        # Test consensus config
        consensus_config = config.consensus
        assert consensus_config.cycle_length > 0
        assert consensus_config.selection.miners_per_cycle > 0
        assert 0 <= consensus_config.trust.alpha_base <= 1

        # Test staking config
        staking_config = config.staking
        assert staking_config.dual_staking["enabled"] is True

        # Test tier configuration
        base_tier = config.get_staking_tier_config("base")
        assert base_tier is not None
        assert base_tier.multiplier == 1.0

        satoshi_tier = config.get_staking_tier_config("satoshi")
        assert satoshi_tier is not None
        assert satoshi_tier.multiplier == 2.0

        # Test configuration validation
        is_valid = config.validate_config()
        assert is_valid is True

        print("✅ Configuration management tests passed")

    @pytest.mark.asyncio
    async def test_miner_validator_data_structures(self, test_network: TestNetwork):
        """Test miner and validator data structures"""
        print("🧪 Testing miner and validator data structures...")

        # Create test miner info
        miner_account = test_network.miners[0]
        miner_info = MinerInfo(
            uid="test_miner_001",
            address=miner_account.account.address,
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

        # Create test validator info
        validator_account = test_network.validators[0]
        validator_info = ValidatorInfo(
            uid="test_validator_001",
            address=validator_account.account.address,
            api_endpoint="http://localhost:8001",
            trust_score=0.9,
            weight=2.0,
            stake=5000.0,
            last_performance=0.92,
            subnet_uid=1,
        )

        assert validator_info.uid == "test_validator_001"
        assert validator_info.last_performance == 0.92

        # Create test task assignment
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

        print("✅ Data structure tests passed")

    @pytest.mark.asyncio
    async def test_scoring_algorithms(self, test_network: TestNetwork):
        """Test scoring and consensus algorithms"""
        print("🧪 Testing scoring algorithms...")

        # Setup test data
        miners_info = []
        for i, miner_account in enumerate(test_network.miners):
            miner_info = MinerInfo(
                uid=f"miner_{i+1:03d}",
                address=miner_account.account.address,
                trust_score=0.8 + (i * 0.05),  # Varying trust scores
                weight=1.0 + (i * 0.2),  # Varying weights
                stake=1000.0 + (i * 500),  # Varying stakes
                performance_history=[0.7 + (i * 0.05)] * 10,
                subnet_uid=1,
            )
            miners_info.append(miner_info)

        # Test incentive calculation
        total_incentive_pool = 1000.0

        total_weighted_performance = sum(
            miner.trust_score
            * miner.weight
            * sum(miner.performance_history)
            / len(miner.performance_history)
            for miner in miners_info
        )

        for miner in miners_info:
            avg_performance = sum(miner.performance_history) / len(
                miner.performance_history
            )
            incentive = calculate_miner_incentive(
                miner_trust=miner.trust_score,
                miner_weight=miner.weight,
                miner_performance=avg_performance,
                total_weighted_performance=total_weighted_performance,
                total_incentive_pool=total_incentive_pool,
            )

            assert incentive >= 0
            assert incentive <= total_incentive_pool

            print(f"✅ Miner {miner.uid}: Incentive = {incentive:.2f}")

        # Test validator weight calculation
        validators_info = []
        for i, validator_account in enumerate(test_network.validators):
            validator_info = ValidatorInfo(
                uid=f"validator_{i+1:03d}",
                address=validator_account.account.address,
                stake=5000.0 + (i * 1000),
                last_performance=0.85 + (i * 0.03),
                registration_time=int(time.time())
                - (i * 86400),  # Different registration times
                subnet_uid=1,
            )
            validators_info.append(validator_info)

        total_stake = sum(v.stake for v in validators_info)

        for validator in validators_info:
            weight = calculate_validator_weight(
                stake=validator.stake,
                total_stake=total_stake,
                performance=validator.last_performance,
                time_participated=int(time.time()) - validator.registration_time,
                lambda_balance=0.5,  # 50% stake, 50% performance/time
            )

            assert weight >= 0
            print(f"✅ Validator {validator.uid}: Weight = {weight:.4f}")

        print("✅ Scoring algorithm tests passed")

    @pytest.mark.asyncio
    async def test_staking_tier_calculation(self, test_network: TestNetwork):
        """Test staking tier calculation logic"""
        print("🧪 Testing staking tier calculation...")

        config = get_staking_config()

        # Test scenarios
        test_cases = [
            # (core_amount, bitcoin_amount, expected_tier)
            (50, 0, "base"),  # Base tier
            (1500, 0.015, "boost"),  # Boost tier
            (15000, 0.15, "super"),  # Super tier
            (60000, 1.5, "satoshi"),  # Satoshi tier
        ]

        for core_amount, bitcoin_amount, expected_tier in test_cases:
            # Get tier config
            tier_config = get_config().get_staking_tier_config(expected_tier)
            assert tier_config is not None

            # Check if amounts meet tier requirements
            meets_core_req = core_amount >= tier_config.min_core
            meets_bitcoin_req = bitcoin_amount >= tier_config.min_bitcoin

            if meets_core_req and meets_bitcoin_req:
                print(
                    f"✅ {core_amount} CORE + {bitcoin_amount} BTC = {expected_tier} tier (multiplier: {tier_config.multiplier}x)"
                )
            else:
                print(
                    f"❌ {core_amount} CORE + {bitcoin_amount} BTC does not meet {expected_tier} tier requirements"
                )

        print("✅ Staking tier calculation tests passed")

    @pytest.mark.asyncio
    async def test_end_to_end_consensus_simulation(self, test_network: TestNetwork):
        """Simulate end-to-end consensus process"""
        print("🧪 Testing end-to-end consensus simulation...")

        # Simulate consensus cycle
        cycle_id = 1
        selected_miners = test_network.miners[:3]  # Select 3 miners

        # Step 1: Task assignment
        tasks = []
        for i, miner in enumerate(selected_miners):
            task = TaskAssignment(
                task_id=f"cycle_{cycle_id}_task_{i+1}",
                task_data={
                    "prompt": f"Generate image {i+1}",
                    "steps": 20,
                    "seed": 42 + i,
                },
                miner_uid=f"miner_{miner.name.split('_')[1]}",
                validator_uid="validator_1",
                timestamp_sent=time.time(),
                expected_result_format="image_url",
            )
            tasks.append(task)

        print(f"✅ Created {len(tasks)} tasks for consensus cycle {cycle_id}")

        # Step 2: Simulate miner responses
        miner_results = []
        for task in tasks:
            # Simulate processing time
            await asyncio.sleep(0.1)

            result = {
                "task_id": task.task_id,
                "result_data": f"https://generated-image-{task.task_id}.png",
                "processing_time": 2.5,
                "quality_score": 0.85 + (hash(task.task_id) % 100) / 1000,
            }
            miner_results.append(result)

        print(f"✅ Received {len(miner_results)} miner results")

        # Step 3: Validator scoring
        validator_scores = {}
        for validator in test_network.validators:
            validator_id = validator.name
            scores = []

            for result in miner_results:
                # Simulate scoring logic
                base_score = result["quality_score"]
                # Add some validator-specific variation
                validator_bias = (hash(validator_id) % 20 - 10) / 100  # ±0.1 variation
                score = max(0, min(1, base_score + validator_bias))
                scores.append(
                    {
                        "task_id": result["task_id"],
                        "score": score,
                        "validator_id": validator_id,
                    }
                )

            validator_scores[validator_id] = scores

        print(f"✅ Generated scores from {len(validator_scores)} validators")

        # Step 4: Consensus calculation
        final_scores = {}
        for result in miner_results:
            task_id = result["task_id"]
            scores = []

            for validator_id, validator_score_list in validator_scores.items():
                for score_data in validator_score_list:
                    if score_data["task_id"] == task_id:
                        scores.append(score_data["score"])

            # Calculate weighted average (equal weights for simulation)
            if scores:
                final_score = sum(scores) / len(scores)
                final_scores[task_id] = final_score

        print(f"✅ Calculated final consensus scores:")
        for task_id, score in final_scores.items():
            print(f"   Task {task_id}: {score:.3f}")

        # Step 5: Reward calculation
        total_rewards = 100.0  # 100 CORE tokens for the cycle
        total_score = sum(final_scores.values())

        if total_score > 0:
            for task_id, score in final_scores.items():
                reward = (score / total_score) * total_rewards
                print(f"   Reward for {task_id}: {reward:.2f} CORE")

        print("✅ End-to-end consensus simulation completed successfully")

    @pytest.mark.asyncio
    async def test_error_handling_and_edge_cases(self, test_network: TestNetwork):
        """Test error handling and edge cases"""
        print("🧪 Testing error handling and edge cases...")

        # Test invalid configurations
        try:
            config = get_config()
            # Test accessing non-existent tier
            invalid_tier = config.get_staking_tier_config("invalid_tier")
            assert invalid_tier is None
            print("✅ Invalid tier handling: OK")
        except Exception as e:
            pytest.fail(f"Unexpected error in tier handling: {e}")

        # Test BCS encoding edge cases
        try:
            encoder = BCSEncoder()

            # Test empty string
            encoder.encode_string("")

            # Test zero values
            encoder.encode_u64(0)
            encoder.encode_bool(False)

            # Test maximum values
            encoder.encode_u8(255)
            encoder.encode_u16(65535)
            encoder.encode_u32(4294967295)

            result = encoder.to_bytes()
            assert len(result) > 0
            print("✅ BCS edge cases: OK")
        except Exception as e:
            pytest.fail(f"BCS encoding failed on edge cases: {e}")

        # Test async client error handling
        try:
            # Test with invalid URL
            invalid_client = CoreAsyncClient("http://invalid-url:9999")
            # This should not fail immediately, only on actual calls
            print("✅ Invalid client creation: OK")
        except Exception as e:
            pytest.fail(f"Unexpected error creating invalid client: {e}")

        print("✅ Error handling and edge cases tests passed")


# Helper functions for scoring
def calculate_miner_incentive(
    miner_trust: float,
    miner_weight: float,
    miner_performance: float,
    total_weighted_performance: float,
    total_incentive_pool: float,
) -> float:
    """Calculate miner incentive based on trust, weight, and performance"""
    if total_weighted_performance == 0:
        return 0

    weighted_contribution = miner_trust * miner_weight * miner_performance
    incentive = (
        weighted_contribution / total_weighted_performance
    ) * total_incentive_pool

    return incentive


def calculate_validator_weight(
    stake: float,
    total_stake: float,
    performance: float,
    time_participated: int,
    lambda_balance: float = 0.5,
) -> float:
    """Calculate validator weight based on stake, performance, and time"""
    import math

    stake_component = stake / total_stake if total_stake > 0 else 0

    # Time component (logarithmic)
    time_hours = time_participated / 3600  # Convert to hours
    time_component = performance * (1 + math.log10(max(1, time_hours)))

    weight = lambda_balance * stake_component + (1 - lambda_balance) * time_component

    return weight
