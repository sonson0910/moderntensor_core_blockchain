# keymanager/encryption_utils.py

import os
import base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
from rich.console import Console
from typing import cast, Optional

from ..config.settings import settings, logger


def get_or_create_salt(coldkey_dir: str) -> bytes:
    """
    Retrieves an existing salt or creates a new random salt for a ColdKey.

    The salt is crucial for deriving the encryption key from the password.
    It is stored in a file named 'salt.bin' within the specified coldkey directory.
    Each ColdKey directory should have its own unique salt file.

    If the directory does not exist, it will be created.
    If 'salt.bin' exists, its content is read and returned.
    If 'salt.bin' does not exist, a new 16-byte random salt is generated,
    written to 'salt.bin', and then returned.

    Args:
        coldkey_dir (str): The absolute or relative path to the ColdKey directory.

    Returns:
        bytes: The 16-byte salt for the given coldkey directory.

    Raises:
        IOError: If there is an error reading or writing the salt file.
        OSError: If there is an error creating the coldkey directory.
    """
    try:
        if not os.path.exists(coldkey_dir):
            os.makedirs(coldkey_dir, exist_ok=True)
            logger.debug(f":file_folder: [dim]Created directory:[/dim] {coldkey_dir}")
    except OSError as e:
        logger.error(f"Failed to create directory {coldkey_dir}: {e}")
        raise  # Re-raise the exception

    salt_path = os.path.join(coldkey_dir, "salt.bin")

    try:
        if os.path.exists(salt_path):
            with open(salt_path, "rb") as f:
                salt = f.read()
            if len(salt) != 16:
                logger.warning(
                    f"Salt file {salt_path} has unexpected length ({len(salt)} bytes). Regenerating."
                )
                # Force regeneration if salt is invalid
                os.remove(salt_path)
                salt = os.urandom(16)
                with open(salt_path, "wb") as f:
                    f.write(salt)
                logger.info(
                    f":sparkles: [yellow]Regenerated invalid salt at[/yellow] {salt_path}"
                )
            else:
                logger.debug(
                    f":package: [dim]Loaded existing 16-byte salt from[/dim] {salt_path}"
                )
        else:
            salt = os.urandom(16)
            with open(salt_path, "wb") as f:
                f.write(salt)
            logger.info(
                f":sparkles: [green]Generated new 16-byte salt at[/green] {salt_path}"
            )
    except IOError as e:
        logger.error(f"Error accessing salt file {salt_path}: {e}")
        raise

    return salt


def generate_encryption_key(password: str, salt: bytes) -> bytes:
    """
    Derives a reproducible encryption key using PBKDF2HMAC KDF.

    Combines the user-provided password and the unique salt for the coldkey
    to generate a strong, 32-byte (256-bit) key suitable for symmetric encryption.
    The derived key is then base64-url-encoded for compatibility with Fernet.

    Args:
        password (str): The password provided by the user.
        salt (bytes): The 16-byte salt retrieved via get_or_create_salt().
                      It MUST be the correct salt associated with the coldkey.

    Returns:
        bytes: A base64-url-encoded 32-byte encryption key.
    """
    if not isinstance(salt, bytes) or len(salt) != 16:
        raise ValueError("Salt must be a 16-byte sequence.")

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=settings.ENCRYPTION_PBKDF2_ITERATIONS,  # Use setting
        backend=default_backend(),
    )
    derived_key = kdf.derive(password.encode("utf-8"))
    encoded_key = base64.urlsafe_b64encode(derived_key)

    logger.debug(":key: [dim]Derived and encoded a 32-byte key for Fernet.[/dim]")
    return encoded_key


def get_cipher_suite(password: str, coldkey_dir: Optional[str] = None) -> Fernet:
    """
    Creates a Fernet cipher suite instance for encryption/decryption.

    This function orchestrates the process:
    1. Determines the correct coldkey directory path (uses settings if None provided).
    2. Retrieves or creates the unique salt for that directory using `get_or_create_salt()`.
    3. Derives the encryption key from the password and salt using `generate_encryption_key()`.
    4. Initializes and returns a Fernet object using the derived key.

    The returned Fernet object can be used directly for `encrypt()` and `decrypt()` operations.

    Args:
        password (str): The password associated with the coldkey.
        coldkey_dir (Optional[str], optional): Path to the specific ColdKey directory.
            If None, defaults to `settings.HOTKEY_BASE_DIR`.

    Returns:
        Fernet: An initialized Fernet cipher suite instance.

    Raises:
        ValueError: If the coldkey directory cannot be determined (e.g., None provided
                    and setting is not configured).
        FileNotFoundError: If `get_or_create_salt` fails to find/create the salt file (propagated).
        IOError: If `get_or_create_salt` encounters an I/O error (propagated).
    """
    # Determine the final directory path
    final_coldkey_dir: str
    if coldkey_dir is not None:
        final_coldkey_dir = coldkey_dir
    else:
        resolved_base_dir = settings.HOTKEY_BASE_DIR
        if resolved_base_dir:
            final_coldkey_dir = resolved_base_dir
        else:
            logger.error(
                ":stop_sign: [bold red]CRITICAL: coldkey_dir is None and settings.HOTKEY_BASE_DIR is not set.[/bold red]"
            )
            raise ValueError("Could not determine the coldkey directory.")

    # Propagates exceptions from get_or_create_salt
    salt = get_or_create_salt(cast(str, final_coldkey_dir))

    # Generate the key (can raise ValueError if salt is invalid, though get_or_create_salt should ensure validity)
    encryption_key = generate_encryption_key(password, salt)

    # Initialize Fernet
    cipher = Fernet(encryption_key)

    logger.debug(
        f":shield: [dim]Created Fernet cipher suite for directory:[/dim] {final_coldkey_dir}"
    )

    return cipher
