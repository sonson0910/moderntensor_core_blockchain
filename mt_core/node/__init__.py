"""
ModernTensor node module for Aptos integration.

This module provides node-specific functionality for interacting with the Aptos blockchain.
"""

from .web3_client import CoreClient
from .aptos_contract import AptosContractManager

__all__ = [
    "CoreClient",
    "AptosContractManager",
]
