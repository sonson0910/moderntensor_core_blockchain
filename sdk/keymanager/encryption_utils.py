# keymanager/encryption_utils.py

import os
import base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
from rich.console import Console
from typing import cast

from sdk.config.settings import settings, logger


def get_or_create_salt(coldkey_dir: str) -> bytes:
    """
    Retrieves or creates a random salt for a ColdKey. The salt is stored in
    'salt.bin' within the coldkey directory. Each ColdKey folder should have
    its own salt to ensure unique key derivation for each one.

    Steps:
        1. Check if the coldkey directory exists; if not, create it.
        2. Look for 'salt.bin'. If it exists, read and return its contents.
        3. If it does not exist, generate a new random 16-byte salt,
           write it to 'salt.bin', and return it.

    Args:
        coldkey_dir (str): The path to the ColdKey directory.

    Returns:
        bytes: The salt used for key derivation.
    """
    if not os.path.exists(coldkey_dir):
        os.makedirs(coldkey_dir, exist_ok=True)
        logger.debug(f":file_folder: [dim]Created directory:[/dim] {coldkey_dir}")

    salt_path = os.path.join(coldkey_dir, "salt.bin")

    if os.path.exists(salt_path):
        with open(salt_path, "rb") as f:
            salt = f.read()
        logger.debug(f":package: [dim]Loaded existing salt from[/dim] {salt_path}")
    else:
        salt = os.urandom(16)
        with open(salt_path, "wb") as f:
            f.write(salt)
        logger.info(f":sparkles: [green]Generated new salt at[/green] {salt_path}")

    return salt


def generate_encryption_key(password: str, salt: bytes) -> bytes:
    """
    Generates an encryption key using the PBKDF2HMAC KDF with the given password and salt.
    The key is 32 bytes (256 bits) and is then base64-url-encoded for Fernet compatibility.

    Steps:
        1. Use PBKDF2HMAC with SHA-256 to derive a 32-byte key.
        2. Return the key after base64-url-encoding.

    Args:
        password (str): The password provided by the user.
        salt (bytes): The salt (unique to each ColdKey directory).

    Returns:
        bytes: A base64-url-encoded 32-byte encryption key suitable for Fernet.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
        backend=default_backend(),
    )
    derived_key = kdf.derive(password.encode("utf-8"))
    encoded_key = base64.urlsafe_b64encode(derived_key)

    logger.debug(":key: [dim]Derived and encoded a 32-byte key for Fernet.[/dim]")
    return encoded_key


def get_cipher_suite(password: str, coldkey_dir: str = None) -> Fernet:  # type: ignore
    """
    Creates a Fernet cipher suite (Fernet object) based on the user's password
    and the salt stored (or created) in the specified ColdKey directory.

    Steps:
        1. If coldkey_dir is None, default to settings.HOTKEY_BASE_DIR.
        2. Retrieve (or create) the salt via get_or_create_salt().
        3. Derive a Fernet-compatible key using generate_encryption_key().
        4. Return a Fernet object that uses this key for encryption/decryption.

    Args:
        password (str): The password used to derive the encryption key.
        coldkey_dir (str, optional): Path to the ColdKey directory (contains salt.bin).
                                     If None, defaults to settings.HOTKEY_BASE_DIR.

    Returns:
        Fernet: A Fernet instance for performing encryption/decryption operations.
    """
    # Determine the final directory path
    final_coldkey_dir: str
    if coldkey_dir is not None:
        final_coldkey_dir = coldkey_dir
    else:
        # Fallback to the global base_dir
        resolved_base_dir = settings.HOTKEY_BASE_DIR
        if resolved_base_dir:
            final_coldkey_dir = resolved_base_dir
        else:
            # This case should ideally not happen
            logger.error(
                ":stop_sign: [bold red]CRITICAL: coldkey_dir is None and settings.HOTKEY_BASE_DIR is not set.[/bold red]"
            )
            raise ValueError("Could not determine the coldkey directory.")

    # Now final_coldkey_dir is guaranteed to be a string
    # Use cast to explicitly tell the type checker
    salt = get_or_create_salt(cast(str, final_coldkey_dir))
    encryption_key = generate_encryption_key(password, salt)
    cipher = Fernet(encryption_key)

    # Use rich markup
    logger.debug(
        f":shield: [dim]Created Fernet cipher suite for directory:[/dim] {final_coldkey_dir}"
    )
    return cipher
