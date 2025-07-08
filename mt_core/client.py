"""
Client module - Web3 client for Core blockchain

This module provides a unified interface to Core blockchain client functionality.
"""

# Re-export from Web3.py for Core blockchain
from web3 import Web3
from web3.eth import Eth
from web3.net import Net

__all__ = [
    "Web3",
    "Eth", 
    "Net"
] 