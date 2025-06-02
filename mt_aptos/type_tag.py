"""
Type Tag module - Re-exports from official Aptos SDK

This module provides a unified interface to Aptos type tag functionality.
"""

# Re-export from official Aptos SDK
from aptos_sdk.type_tag import *

__all__ = [
    "TypeTag",
    "StructTag"
] 