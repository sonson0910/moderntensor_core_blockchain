# keymanager/encryption_utils.py

import os
import base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet


def get_or_create_salt(coldkey_dir: str) -> bytes:
    """
    Each ColdKey has its own random salt, stored in the salt.bin file.
    If it doesn't exist, create a new one; if it exists, read it to use.
    """
    # ==== FIX: Ensure the directory is created before writing salt.bin ====
    if not os.path.exists(coldkey_dir):
        os.makedirs(coldkey_dir, exist_ok=True)

    salt_path = os.path.join(coldkey_dir, "salt.bin")
    if os.path.exists(salt_path):
        with open(salt_path, "rb") as f:
            salt = f.read()
    else:
        salt = os.urandom(16)
        with open(salt_path, "wb") as f:
            f.write(salt)
    return salt


def generate_encryption_key(password: str, salt: bytes) -> bytes:
    """
    Generate an encryption key using PBKDF2HMAC, with salt that is unique for each ColdKey.
    """
    kdf = PBKDF2HMAC(
        algorithm=SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
        backend=default_backend(),
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def get_cipher_suite(password: str, coldkey_dir: str) -> Fernet:
    """
    Create a Fernet object based on password + salt (retrieved from coldkey_dir).
    """
    salt = get_or_create_salt(coldkey_dir)
    encryption_key = generate_encryption_key(password, salt)
    return Fernet(encryption_key)
