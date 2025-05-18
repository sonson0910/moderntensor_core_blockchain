"""
Aptos Core package for ModernTensor SDK.
This package replaces the Cardano-specific functionality with Aptos blockchain integration.
"""

from .contract_client import AptosContractClient, create_aptos_client
from .context import get_aptos_context
from .address import get_aptos_address
from .account_service import (
    get_account_resources,
    get_account_balance,
    transfer_coins,
    check_account_exists
)
from .validator_helper import (
    get_validator_info,
    get_all_validators,
    get_all_miners,
    is_validator_active
)

__all__ = [
    "AptosContractClient", 
    "create_aptos_client", 
    "get_aptos_context",
    "get_aptos_address",
    "get_account_resources",
    "get_account_balance",
    "transfer_coins",
    "check_account_exists",
    "get_validator_info",
    "get_all_validators",
    "get_all_miners",
    "is_validator_active"
] 