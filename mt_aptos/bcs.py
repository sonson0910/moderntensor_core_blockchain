"""
BCS module - Re-exports from official Aptos SDK

This module provides a unified interface to Aptos BCS functionality.
"""

# Re-export from official Aptos SDK
from aptos_sdk.bcs import *

__all__ = [
    "Serializer"
] 