# tests/conftest.py

import os
import sys
from pathlib import Path
import pytest
import asyncio
from mt_aptos.config.settings import settings
from aptos_sdk.account import Account

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

# Import MockRestClient (có thể import trong tests cụ thể nếu cần)
try:
    from tests.aptos.mock_client import MockRestClient
except ImportError:
    # Fallback nếu không tìm thấy
    MockRestClient = None

# Configure pytest
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )

# Aptos testnet URLs
@pytest.fixture
def testnet_url():
    return settings.APTOS_TESTNET_URL

@pytest.fixture
def faucet_url():
    return settings.APTOS_FAUCET_URL

# Mock Aptos client for testing
@pytest.fixture
def mock_aptos_client():
    """
    Trả về mock client cho Aptos API.
    Sử dụng để tránh gọi API thực và rate limits.
    """
    if MockRestClient is None:
        pytest.skip("MockRestClient không khả dụng")
    
    return MockRestClient()

# Fixture cung cấp tài khoản test với một số dư giả định
@pytest.fixture
def mock_test_account():
    """Tạo tài khoản test với private key cố định."""
    # Sử dụng một private key cố định để các test có thể tái tạo
    private_key_hex = "0x82a167f420cfd52500bdcf2754ccf68167ee70e9eef9cc4f95d387e42c97cfd7"
    return Account.load_key(private_key_hex)

# Định cấu hình cho mock client với tài khoản test
@pytest.fixture
def configured_mock_aptos_client(mock_aptos_client, mock_test_account):
    """
    Cấu hình mock client với resources cho tài khoản test.
    """
    # Cấu hình resources cho tài khoản test
    test_account_addr = str(mock_test_account.address())
    
    # Cấu hình CoinStore và FungibleStore cho tài khoản test
    mock_aptos_client.configure_account_resources(test_account_addr, [
        {
            "type": "0x1::account::Account",
            "data": {
                "authentication_key": test_account_addr,
                "sequence_number": "0"
            }
        },
        {
            "type": "0x1::coin::CoinStore<0x1::aptos_coin::AptosCoin>",
            "data": {
                "coin": {"value": "10000000000"},  # 100 APT
                "frozen": False
            }
        }
    ])
    
    # Cấu hình FungibleStore riêng (cho các test cần cả hai loại lưu trữ)
    fungible_store_address = "0x441e7a4984f621e9ece9747ac2ffe530e135a9ac6f60886ddb452dae5632ee27"
    mock_aptos_client.configure_account_resources(fungible_store_address, [
        {
            "type": "0x1::fungible_asset::FungibleStore",
            "data": {
                "balance": "297311045",  # ~2.97 APT
                "metadata": "0x1::aptos_coin::AptosCoin"
            }
        },
        {
            "type": "0x1::object::ObjectCore",
            "data": {
                "owner": test_account_addr,
                "guid_creation_num": "0",
                "allow_ungated_transfer": True
            }
        }
    ])
    
    return mock_aptos_client

# For asynchronous testing
@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
