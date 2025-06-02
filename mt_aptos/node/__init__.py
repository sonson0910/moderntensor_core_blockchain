"""
ModernTensor node module for Aptos integration.

This module provides node-specific functionality for interacting with the Aptos blockchain.
"""

from .aptos_client import AptosClient
from .aptos_contract import AptosContractManager

__all__ = [
    "AptosClient",
    "AptosContractManager",
]
