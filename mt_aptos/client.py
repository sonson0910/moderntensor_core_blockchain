"""
Client module - Re-exports from official Aptos SDK

This module provides a unified interface to Aptos client functionality.
"""

# Re-export from official Aptos SDK async_client module
from aptos_sdk.async_client import RestClient

__all__ = [
    "RestClient"
] 