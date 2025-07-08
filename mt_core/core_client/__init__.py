"""
Core Client package for ModernTensor SDK.
This package provides Core blockchain integration functionality.
"""

from .contract_client import ModernTensorCoreClient

# Core blockchain utilities
try:
    from .context import get_core_context
except ImportError:
    # Fallback if context module not available
    def get_core_context():
        from web3 import Web3

        return Web3(Web3.HTTPProvider("https://rpc.test.btcs.network"))


try:
    from .address import get_core_address
except ImportError:
    # Fallback if address module not available
    def get_core_address():
        return "0x0000000000000000000000000000000000000000"


# Account and validator utilities (optional)
try:
    from .account_service import (
        get_account_resources,
        get_account_balance,
        transfer_coins,
        check_account_exists,
    )
except ImportError:
    # Fallback implementations
    def get_account_resources(*args, **kwargs):
        return {}

    def get_account_balance(*args, **kwargs):
        return 0

    def transfer_coins(*args, **kwargs):
        return None

    def check_account_exists(*args, **kwargs):
        return False


try:
    from .validator_helper import (
        get_validator_info,
        get_all_validators,
        get_all_miners,
        is_validator_active,
    )
except ImportError:
    # Fallback implementations
    def get_validator_info(*args, **kwargs):
        return None

    def get_all_validators(*args, **kwargs):
        return []

    def get_all_miners(*args, **kwargs):
        return []

    def is_validator_active(*args, **kwargs):
        return False


__all__ = [
    "ModernTensorCoreClient",
    "get_core_context",
    "get_core_address",
    "get_account_resources",
    "get_account_balance",
    "transfer_coins",
    "check_account_exists",
    "get_validator_info",
    "get_all_validators",
    "get_all_miners",
    "is_validator_active",
]
