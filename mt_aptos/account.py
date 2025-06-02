"""
Account module - Re-exports from official Aptos SDK

This module provides a unified interface to Aptos account functionality
while maintaining compatibility with the official Aptos SDK.
"""

# Re-export all account-related classes from the official Aptos SDK
from aptos_sdk.account import (
    Account,
    AccountAddress,
    AccountAuthenticator,
    RotationProofChallenge,
    ed25519
)

# Make them available at module level
__all__ = [
    "Account",
    "AccountAddress",
    "AccountAuthenticator",
    "RotationProofChallenge", 
    "ed25519"
] 