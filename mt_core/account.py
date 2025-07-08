"""
Account module - Ethereum/Core blockchain account functionality

This module provides account functionality for Core blockchain using eth-account.
"""

# Re-export account-related classes for Core blockchain
from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_utils import to_checksum_address, keccak
from web3 import Web3

# Fix eth_keys import
try:
    from eth_keys.datatypes import PrivateKey, PublicKey
except ImportError:
    # Fallback for different eth_keys versions
    try:
        from eth_keys import keys

        PrivateKey = keys.PrivateKey
        PublicKey = keys.PublicKey
    except ImportError:
        # Create dummy classes if eth_keys not available
        class PrivateKey:
            pass

        class PublicKey:
            pass


# Core blockchain specific utilities
class CoreAccount:
    """Wrapper for Core blockchain account functionality"""

    def __init__(self, private_key=None):
        if private_key:
            self.account = Account.from_key(private_key)
        else:
            self.account = Account.create()

    @property
    def address(self):
        """Get checksum address"""
        return to_checksum_address(self.account.address)

    @property
    def private_key(self):
        """Get private key hex"""
        return self.account.key.hex()

    @property
    def public_key(self):
        """Get public key"""
        return self.account._key_obj.public_key

    def sign_message(self, message):
        """Sign a message"""
        return self.account.sign_message(message)

    def sign_transaction(self, transaction):
        """Sign a transaction"""
        return self.account.sign_transaction(transaction)


# Make them available at module level
__all__ = [
    "Account",
    "LocalAccount",
    "PrivateKey",
    "PublicKey",
    "CoreAccount",
    "to_checksum_address",
    "keccak",
    "Web3",
]
