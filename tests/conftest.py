# tests/conftest.py

import os
import sys
from pathlib import Path
import pytest

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

# Configure pytest
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )

@pytest.fixture(scope="session")
def testnet_url():
    """Get testnet URL."""
    return "https://fullnode.testnet.aptoslabs.com"

@pytest.fixture(scope="session")
def faucet_url():
    """Get faucet URL."""
    return "https://faucet.testnet.aptoslabs.com"
