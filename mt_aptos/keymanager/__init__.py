"""
Compatibility module for importing from the old 'sdk.keymanager' package.
"""

from mt_aptos.keymanager import *
from mt_aptos.keymanager.coldkey_manager import ColdKeyManager
from mt_aptos.keymanager.hotkey_manager import HotKeyManager
from mt_aptos.keymanager.decryption_utils import decode_hotkey_account
from mt_aptos.keymanager.encryption_utils import get_cipher_suite, get_or_create_salt, generate_encryption_key

__all__ = [
    "ColdKeyManager",
    "HotKeyManager",
    "decode_hotkey_account",
    "get_cipher_suite",
    "get_or_create_salt",
    "generate_encryption_key"
]
