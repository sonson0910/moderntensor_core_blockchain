"""
Core blockchain integration tests for ModernTensor
Tests the main functionalities including Bitcoin staking, dual staking, and smart contracts
"""

import pytest
import asyncio
import os
from web3 import Web3
from mt_core.account import CoreAccount
from mt_core.core_client.contract_client import ModernTensorCoreClient
from mt_core.config.settings import Settings
from tests.core.mock_client import MockWeb3Client


class TestCoreIntegration:
    """Test Core blockchain integration"""
    
    @pytest.fixture
    def mock_client(self):
        """Mock Web3 client for testing"""
        return MockWeb3Client()
    
    @pytest.fixture
    def test_account(self):
        """Test account for Core blockchain"""
        private_key = "0x82a167f420cfd52500bdcf2754ccf68167ee70e9eef9cc4f95d387e42c97cfd7"
        return CoreAccount(private_key)
    
    @pytest.fixture
    def core_client(self, test_account, mock_client):
        """ModernTensor Core client with mock"""
        # Mock the client to use our mock Web3 client
        client = ModernTensorCoreClient(
            account=test_account,
            rpc_url="https://rpc.test.btcs.network",
            contract_address="0x1234567890123456789012345678901234567890",
            chain_id=1115
        )
        # Replace with mock client
        client._web3_client = mock_client
        return client
    
    def test_account_creation(self, test_account):
        """Test Core account creation"""
        assert test_account.address is not None
        assert test_account.private_key is not None
        assert test_account.public_key is not None
        assert len(test_account.address) == 42  # 0x + 40 hex chars
        assert test_account.address.startswith('0x')
    
    def test_account_signing(self, test_account):
        """Test transaction signing"""
        message = "test message"
        signature = test_account.sign_message(message)
        assert signature is not None
        
        # Verify signature
        recovered_address = test_account.recover_message(message, signature)
        assert recovered_address.lower() == test_account.address.lower()
    
    @pytest.mark.asyncio
    async def test_balance_checking(self, core_client, mock_client, test_account):
        """Test balance checking functionality"""
        # Set up mock balances
        mock_client.set_balance(test_account.address, Web3.to_wei(10, 'ether'))
        mock_client.set_token_balance(test_account.address, Web3.to_wei(1000, 'ether'))
        mock_client.set_bitcoin_balance(test_account.address, 0.5)
        
        # Test ETH balance
        eth_balance = await core_client.get_eth_balance(test_account.address)
        assert eth_balance == 10.0
        
        # Test CORE token balance
        core_balance = await core_client.get_core_balance(test_account.address)
        assert core_balance == 1000.0
        
        # Test Bitcoin balance
        btc_balance = await core_client.get_bitcoin_balance(test_account.address)
        assert btc_balance == 0.5
    
    @pytest.mark.asyncio
    async def test_miner_registration(self, core_client, test_account):
        """Test miner registration"""
        uid = os.urandom(16)
        subnet_uid = 1
        stake_amount = Web3.to_wei(1000, 'ether')
        api_endpoint = "http://localhost:8080"
        staking_tier = "base"
        
        # Register miner
        tx_hash = await core_client.register_miner(
            uid=uid,
            subnet_uid=subnet_uid,
            stake_amount=stake_amount,
            api_endpoint=api_endpoint,
            staking_tier=staking_tier
        )
        
        assert tx_hash is not None
        assert tx_hash.startswith('0x')
        assert len(tx_hash) == 66  # 0x + 64 hex chars
    
    @pytest.mark.asyncio
    async def test_validator_registration(self, core_client, test_account):
        """Test validator registration"""
        uid = os.urandom(16)
        subnet_uid = 1
        stake_amount = Web3.to_wei(10000, 'ether')
        staking_tier = "super"
        
        # Register validator
        tx_hash = await core_client.register_validator(
            uid=uid,
            subnet_uid=subnet_uid,
            stake_amount=stake_amount,
            staking_tier=staking_tier
        )
        
        assert tx_hash is not None
        assert tx_hash.startswith('0x')
    
    @pytest.mark.asyncio
    async def test_bitcoin_staking_tiers(self, core_client, test_account, bitcoin_staking_config):
        """Test Bitcoin staking tiers"""
        tiers = ['boost', 'super', 'satoshi']
        
        for tier in tiers:
            min_btc = bitcoin_staking_config['min_stake_amounts'][tier]
            multiplier = bitcoin_staking_config['reward_multipliers'][tier]
            
            # Test with minimum required BTC
            tx_hash = await core_client.enable_dual_staking(
                core_amount=Web3.to_wei(1000, 'ether'),
                btc_amount=min_btc,
                staking_tier=tier,
                lock_time=None,
                staker_address=test_account.address
            )
            
            assert tx_hash is not None
            
            # Verify staking info
            staking_info = await core_client.get_staking_info(test_account.address)
            assert staking_info['staking_tier'] == tier
            assert staking_info['bitcoin_staked'] >= min_btc
            assert staking_info['dual_staking'] == True
    
    @pytest.mark.asyncio
    async def test_dual_staking_validation(self, core_client, test_account):
        """Test dual staking validation"""
        # Test insufficient Bitcoin for tier
        with pytest.raises(ValueError, match="Insufficient Bitcoin"):
            await core_client.enable_dual_staking(
                core_amount=Web3.to_wei(1000, 'ether'),
                btc_amount=0.005,  # Less than required 0.01 for boost
                staking_tier='boost',
                lock_time=None,
                staker_address=test_account.address
            )
        
        # Test invalid tier
        with pytest.raises(ValueError, match="Invalid staking tier"):
            await core_client.enable_dual_staking(
                core_amount=Web3.to_wei(1000, 'ether'),
                btc_amount=1.0,
                staking_tier='invalid_tier',
                lock_time=None,
                staker_address=test_account.address
            )
    
    @pytest.mark.asyncio
    async def test_reward_calculations(self, core_client, test_account, bitcoin_staking_config):
        """Test reward calculations for different tiers"""
        base_rewards = 100  # Base rewards
        
        for tier, config in bitcoin_staking_config['reward_multipliers'].items():
            multiplier = config
            
            # Setup staking for tier
            if tier != 'base':
                await core_client.enable_dual_staking(
                    core_amount=Web3.to_wei(1000, 'ether'),
                    btc_amount=bitcoin_staking_config['min_stake_amounts'][tier],
                    staking_tier=tier,
                    lock_time=None,
                    staker_address=test_account.address
                )
            
            # Calculate rewards
            rewards = await core_client.calculate_rewards(test_account.address)
            
            expected_core_rewards = base_rewards * multiplier
            assert rewards['core_rewards'] == expected_core_rewards
            
            if tier != 'base':
                assert rewards['bitcoin_rewards'] > 0
            else:
                assert rewards['bitcoin_rewards'] == 0
    
    @pytest.mark.asyncio
    async def test_reward_claiming(self, core_client, test_account):
        """Test reward claiming"""
        # Setup some staking first
        await core_client.enable_dual_staking(
            core_amount=Web3.to_wei(1000, 'ether'),
            btc_amount=0.1,
            staking_tier='super',
            lock_time=None,
            staker_address=test_account.address
        )
        
        # Claim rewards
        tx_hash = await core_client.claim_rewards(test_account.address)
        
        assert tx_hash is not None
        assert tx_hash.startswith('0x')
    
    @pytest.mark.asyncio
    async def test_subnet_operations(self, core_client, test_account):
        """Test subnet operations"""
        # Get subnet info
        subnet_info = await core_client.get_subnet_info(1)
        
        assert 'total_stake' in subnet_info
        assert 'validator_count' in subnet_info
        assert 'miner_count' in subnet_info
        assert 'difficulty' in subnet_info
        
        # Verify subnet data structure
        assert isinstance(subnet_info['total_stake'], int)
        assert isinstance(subnet_info['validator_count'], int)
        assert isinstance(subnet_info['miner_count'], int)
    
    @pytest.mark.asyncio
    async def test_metagraph_operations(self, core_client):
        """Test metagraph operations"""
        # Get metagraph data
        metagraph = await core_client.get_metagraph(1)
        
        assert isinstance(metagraph, dict)
        # Metagraph should contain validator and miner information
    
    @pytest.mark.asyncio
    async def test_gas_estimation(self, core_client, test_account):
        """Test gas estimation for different operations"""
        # Test miner registration gas
        gas_estimate = await core_client.estimate_gas_cost('register_miner')
        assert gas_estimate > 0
        
        # Test dual staking gas
        gas_estimate = await core_client.estimate_gas_cost('enable_dual_staking')
        assert gas_estimate > 0
        
        # Test reward claiming gas
        gas_estimate = await core_client.estimate_gas_cost('claim_rewards')
        assert gas_estimate > 0
    
    @pytest.mark.asyncio
    async def test_transaction_monitoring(self, core_client, test_account):
        """Test transaction monitoring"""
        # Register a miner
        tx_hash = await core_client.register_miner(
            uid=os.urandom(16),
            subnet_uid=1,
            stake_amount=Web3.to_wei(1000, 'ether'),
            api_endpoint="http://localhost:8080",
            staking_tier="base"
        )
        
        # Get transaction receipt
        receipt = await core_client.get_transaction_receipt(tx_hash)
        
        assert receipt is not None
        assert receipt['transactionHash'] == tx_hash
        assert receipt['status'] == 1  # Success
    
    def test_network_configuration(self, settings):
        """Test network configuration"""
        assert settings.CORE_NETWORK in ['testnet', 'mainnet']
        assert settings.CORE_NODE_URL.startswith('https://')
        assert settings.CORE_CHAIN_ID in [1115, 1116]  # Testnet or mainnet
        assert settings.CORE_CONTRACT_ADDRESS.startswith('0x')
        assert len(settings.CORE_CONTRACT_ADDRESS) == 42
    
    def test_staking_tier_configuration(self, bitcoin_staking_config):
        """Test staking tier configuration"""
        required_tiers = ['base', 'boost', 'super', 'satoshi']
        
        for tier in required_tiers:
            assert tier in bitcoin_staking_config['min_stake_amounts']
            assert tier in bitcoin_staking_config['reward_multipliers']
            assert tier in bitcoin_staking_config['lock_times']
        
        # Verify multiplier progression
        assert bitcoin_staking_config['reward_multipliers']['base'] == 1.0
        assert bitcoin_staking_config['reward_multipliers']['boost'] == 1.25
        assert bitcoin_staking_config['reward_multipliers']['super'] == 1.5
        assert bitcoin_staking_config['reward_multipliers']['satoshi'] == 2.0
    
    @pytest.mark.asyncio
    async def test_network_conditions(self, mock_client, core_client):
        """Test different network conditions"""
        # Test high gas conditions
        mock_client.simulate_network_conditions({'high_gas': True})
        assert mock_client.gas_price > Web3.to_wei(50, 'gwei')
        
        # Test low gas conditions
        mock_client.simulate_network_conditions({'low_gas': True})
        assert mock_client.gas_price < Web3.to_wei(10, 'gwei')
        
        # Reset to normal
        mock_client.reset()
        assert mock_client.gas_price == Web3.to_wei(20, 'gwei')


class TestBitcoinStaking:
    """Dedicated tests for Bitcoin staking functionality"""
    
    @pytest.fixture
    def bitcoin_client(self, test_account, mock_client):
        """Core client configured for Bitcoin staking"""
        client = ModernTensorCoreClient(
            account=test_account,
            rpc_url="https://rpc.test.btcs.network",
            contract_address="0x9876543210987654321098765432109876543210",
            chain_id=1115
        )
        client._web3_client = mock_client
        return client
    
    @pytest.mark.asyncio
    async def test_bitcoin_timelock_creation(self, bitcoin_client, test_account):
        """Test Bitcoin timelock creation"""
        from datetime import datetime, timedelta
        
        # Create 30-day timelock
        lock_time = datetime.now() + timedelta(days=30)
        
        tx_hash = await bitcoin_client.stake_bitcoin(
            amount=0.1,
            lock_time=lock_time,
            staker_address=test_account.address
        )
        
        assert tx_hash is not None
    
    @pytest.mark.asyncio
    async def test_bitcoin_staking_validation(self, bitcoin_client, test_account):
        """Test Bitcoin staking validation"""
        from datetime import datetime, timedelta
        
        # Test minimum staking amount validation
        with pytest.raises(ValueError):
            await bitcoin_client.stake_bitcoin(
                amount=0.001,  # Too small
                lock_time=datetime.now() + timedelta(days=30),
                staker_address=test_account.address
            )
    
    @pytest.mark.asyncio
    async def test_dual_staking_economics(self, bitcoin_client, test_account, bitcoin_staking_config):
        """Test dual staking economics"""
        # Test each tier's economics
        for tier in ['boost', 'super', 'satoshi']:
            min_btc = bitcoin_staking_config['min_stake_amounts'][tier]
            multiplier = bitcoin_staking_config['reward_multipliers'][tier]
            
            # Enable dual staking
            await bitcoin_client.enable_dual_staking(
                core_amount=Web3.to_wei(1000, 'ether'),
                btc_amount=min_btc,
                staking_tier=tier,
                lock_time=None,
                staker_address=test_account.address
            )
            
            # Calculate expected vs actual rewards
            rewards = await bitcoin_client.calculate_rewards(test_account.address)
            expected_core = 100 * multiplier  # Base 100 * multiplier
            
            assert rewards['core_rewards'] == expected_core
            assert rewards['bitcoin_rewards'] > 0


class TestPerformance:
    """Performance tests for Core blockchain operations"""
    
    @pytest.mark.asyncio
    async def test_transaction_throughput(self, core_client, performance_test_config):
        """Test transaction throughput"""
        import time
        
        start_time = time.time()
        transactions = []
        
        # Send multiple transactions
        for i in range(10):
            tx_hash = await core_client.register_miner(
                uid=os.urandom(16),
                subnet_uid=1,
                stake_amount=Web3.to_wei(1000, 'ether'),
                api_endpoint=f"http://localhost:808{i}",
                staking_tier="base"
            )
            transactions.append(tx_hash)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Check performance
        assert duration < performance_test_config['max_response_time'] * 10  # 10 transactions
        assert len(transactions) == 10
        assert all(tx.startswith('0x') for tx in transactions)
    
    @pytest.mark.asyncio
    async def test_memory_usage(self, core_client, performance_test_config):
        """Test memory usage during operations"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Perform memory-intensive operations
        for i in range(100):
            await core_client.get_subnet_info(1)
            await core_client.calculate_rewards("0x742d35Cc6634C0532925a3b8d2D25F95b32A6B3C")
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Check memory usage is within limits
        assert memory_increase < performance_test_config['max_memory_usage']


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 