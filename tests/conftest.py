# tests/conftest.py

import os
import sys
from pathlib import Path
import pytest
import asyncio
from web3 import Web3
from eth_account import Account
from mt_core.config.settings import Settings
from mt_core.account import CoreAccount

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

# Import MockWeb3Client (có thể import trong tests cụ thể nếu cần)
try:
    from tests.core.mock_client import MockWeb3Client
except ImportError:
    # Fallback nếu không tìm thấy
    MockWeb3Client = None

# Configure pytest
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )

# Core blockchain network configurations
@pytest.fixture
def core_testnet_config():
    """Core testnet configuration"""
    return {
        'rpc_url': 'https://rpc.test.btcs.network',
        'chain_id': 1115,
        'faucet_url': 'https://scan.test.btcs.network/faucet',
        'explorer_url': 'https://scan.test.btcs.network'
    }

@pytest.fixture
def core_mainnet_config():
    """Core mainnet configuration"""
    return {
        'rpc_url': 'https://rpc.coredao.org',
        'chain_id': 1116,
        'explorer_url': 'https://scan.coredao.org'
    }

@pytest.fixture
def settings():
    """Settings fixture for Core blockchain"""
    return Settings()

# Mock Web3 client for testing
@pytest.fixture
def mock_web3_client():
    """
    Trả về mock client cho Web3 API.
    Sử dụng để tránh gọi API thực và rate limits.
    """
    if MockWeb3Client is None:
        pytest.skip("MockWeb3Client không khả dụng")
    
    return MockWeb3Client()

# Fixture cung cấp tài khoản test với một số dư giả định
@pytest.fixture
def mock_test_account():
    """Tạo tài khoản test với private key cố định."""
    # Sử dụng một private key cố định để các test có thể tái tạo
    private_key_hex = "0x82a167f420cfd52500bdcf2754ccf68167ee70e9eef9cc4f95d387e42c97cfd7"
    return CoreAccount(private_key_hex)

@pytest.fixture
def mock_test_account_2():
    """Tạo tài khoản test thứ hai"""
    private_key_hex = "0x95a167f420cfd52500bdcf2754ccf68167ee70e9eef9cc4f95d387e42c97cfd8"
    return CoreAccount(private_key_hex)

# Định cấu hình cho mock client với tài khoản test
@pytest.fixture
def configured_mock_web3_client(mock_web3_client, mock_test_account):
    """
    Cấu hình mock client với balance cho tài khoản test.
    """
    # Cấu hình balance cho tài khoản test
    test_account_addr = mock_test_account.address
    
    # Cấu hình ETH balance
    mock_web3_client.set_balance(test_account_addr, Web3.to_wei(10, 'ether'))
    
    # Cấu hình CORE token balance
    mock_web3_client.set_token_balance(test_account_addr, Web3.to_wei(10000, 'ether'))
    
    # Cấu hình Bitcoin staking balance
    mock_web3_client.set_bitcoin_balance(test_account_addr, 1.0)  # 1 BTC
    
    return mock_web3_client

# Mock contract data for testing
@pytest.fixture
def mock_contract_data():
    """Mock contract data for testing"""
    return {
        'subnet_1': {
            'validators': [
                {
                    'uid': '0x1234567890abcdef1234567890abcdef12345678',
                    'address': '0x742d35Cc6634C0532925a3b8d2D25F95b32A6B3C',
                    'stake': Web3.to_wei(10000, 'ether'),
                    'staking_tier': 'base',
                    'bitcoin_staked': 0,
                    'active': True
                }
            ],
            'miners': [
                {
                    'uid': '0xabcdef1234567890abcdef1234567890abcdef12',
                    'address': '0x8ba1f109551bD432803012645Hac136c13e87058',
                    'stake': Web3.to_wei(1000, 'ether'),
                    'staking_tier': 'boost',
                    'bitcoin_staked': 0.1,
                    'api_endpoint': 'http://localhost:8080',
                    'active': True
                }
            ],
            'total_stake': Web3.to_wei(11000, 'ether'),
            'difficulty': 1000,
            'last_update': 1234567890
        }
    }

# Bitcoin staking fixtures
@pytest.fixture
def bitcoin_staking_config():
    """Bitcoin staking configuration"""
    return {
        'min_stake_amounts': {
            'base': 0,
            'boost': 0.01,
            'super': 0.1,
            'satoshi': 1.0
        },
        'reward_multipliers': {
            'base': 1.0,
            'boost': 1.25,
            'super': 1.5,
            'satoshi': 2.0
        },
        'lock_times': {
            'base': 0,
            'boost': 30,
            'super': 60,
            'satoshi': 90
        }
    }

# Smart contract mock addresses
@pytest.fixture
def mock_contract_addresses():
    """Mock contract addresses for testing"""
    return {
        'moderntensor_contract': '0x1234567890123456789012345678901234567890',
        'core_token': '0x40375C92d9FAf44d2f9db9Bd9ba41a3317a2404f',
        'bitcoin_staking': '0x9876543210987654321098765432109876543210',
        'subnet_manager': '0xabcdefabcdefabcdefabcdefabcdefabcdefabcd'
    }

# Network simulation fixtures
@pytest.fixture
def network_simulation_data():
    """Network simulation data for testing"""
    return {
        'validators': 4,
        'miners': 16,
        'total_stake': Web3.to_wei(50000, 'ether'),
        'total_bitcoin_stake': 5.0,
        'network_difficulty': 5000,
        'avg_block_time': 3,
        'tps': 5000,
        'gas_price': Web3.to_wei(20, 'gwei')
    }

# For asynchronous testing
@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Test database fixtures
@pytest.fixture
def test_database_config():
    """Test database configuration"""
    return {
        'database_url': 'sqlite:///test_moderntensor.db',
        'echo': False,
        'pool_size': 1,
        'max_overflow': 0
    }

# Integration test fixtures
@pytest.fixture
def integration_test_config():
    """Integration test configuration"""
    return {
        'use_real_network': False,
        'timeout_seconds': 30,
        'max_retries': 3,
        'skip_slow_tests': True
    }

# Performance test fixtures
@pytest.fixture
def performance_test_config():
    """Performance test configuration"""
    return {
        'max_response_time': 1.0,
        'min_tps': 1000,
        'max_memory_usage': 100 * 1024 * 1024,  # 100MB
        'test_duration': 60  # seconds
    }
