"""
Test configuration and fixtures for ModernTensor Core tests
"""

import pytest
import asyncio
import os
from typing import List

# Test private keys (for testing only - never use in production)
test_private_keys = [
    "0x82a167f420cfd52500bdcf2754ccf68167ee70e9eef9cc4f95d387e42c97cfd7",
    "0x7b3f9b8c1d2e4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9",
    "0x1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2",
    "0x9f8e7d6c5b4a39284756193847561029384756193847561029384756193847aa",
    "0x5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4",
    "0x6b5a49382746501928374650192837465019283746501928374650192837465b",
    "0x7c6b5a493827465019283746501928374650192837465019283746501928374c",
    "0x8d7c6b5a4938274650192837465019283746501928374650192837465019283d",
    "0x9e8d7c6b5a4938274650192837465019283746501928374650192837465019ee",
    "0x0f9e8d7c6b5a4938274650192837465019283746501928374650192837465fff",
]


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_accounts():
    """Provide test accounts for integration tests"""
    from mt_core.account import CoreAccount

    accounts = []
    for i, private_key in enumerate(test_private_keys[:5]):
        account = CoreAccount(private_key)
        accounts.append(
            {
                "name": f"test_account_{i+1}",
                "account": account,
                "private_key": private_key,
            }
        )

    return accounts


@pytest.fixture
def test_config():
    """Provide test configuration"""
    return {
        "network": "testnet",
        "rpc_url": "https://rpc.test.btcs.network",
        "chain_id": 1115,
        "contract_address": "0x0000000000000000000000000000000000000000",
        "timeout": 30,
    }


@pytest.fixture
async def mock_blockchain_client():
    """Mock blockchain client for testing without real network calls"""
    from tests.core.mock_client import MockWeb3Client

    return MockWeb3Client()


# Mark all async tests
def pytest_collection_modifyitems(config, items):
    """Automatically mark async tests"""
    for item in items:
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)


# Setup test environment
def pytest_configure(config):
    """Configure test environment"""
    # Set test environment variables
    os.environ["MODERNTENSOR_LOG_LEVEL"] = "DEBUG"
    os.environ["MODERNTENSOR_CORE_NETWORK"] = "testnet"

    # Register custom markers
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line(
        "markers", "blockchain: mark test as requiring blockchain interaction"
    )


# Cleanup after tests
def pytest_unconfigure(config):
    """Cleanup after test session"""
    # Clean up any test files or resources
    pass
