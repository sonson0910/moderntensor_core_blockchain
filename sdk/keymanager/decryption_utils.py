# keymanager/decryption_utils.py

import os
import json
import binascii
from cryptography.fernet import Fernet
from pycardano import ExtendedSigningKey

from sdk.keymanager.encryption_utils import get_or_create_salt, generate_encryption_key
from sdk.config.settings import settings, logger

def decode_hotkey_skey(
    base_dir: str = None,
    coldkey_name: str = "",
    hotkey_name: str = "",
    password: str = "",
):
    """
    Decrypt the hotkey extended signing keys (payment & stake) from hotkeys.json.

    This function reads and decrypts the 'encrypted_data' field in hotkeys.json 
    for a particular hotkey, reconstructing the ExtendedSigningKey objects.

    If no base_dir is provided, it defaults to settings.HOTKEY_BASE_DIR.

    Args:
        base_dir (str, optional): The base directory path where coldkeys are stored.
                                  Defaults to settings.HOTKEY_BASE_DIR if None.
        coldkey_name (str): The folder name of the coldkey.
        hotkey_name (str): The specific hotkey name in hotkeys.json.
        password (str): The password to derive the Fernet key and decrypt the hotkey data.

    Returns:
        (ExtendedSigningKey, ExtendedSigningKey): A tuple containing (payment_xsk, stake_xsk).

    Raises:
        KeyError: If 'hotkeys' or 'encrypted_data' fields are missing in hotkeys.json.
        FileNotFoundError: If hotkeys.json does not exist or the specified hotkey is not found.
        Exception: If decryption fails or required fields are missing in the decrypted data.
    """

    # ----------------------------------------------------------------
    # 1) Determine the base directory (use settings if not provided)
    # ----------------------------------------------------------------
    base_dir = base_dir or settings.HOTKEY_BASE_DIR
    coldkey_dir = os.path.join(base_dir, coldkey_name)

    # ----------------------------------------------------------------
    # 2) Retrieve or create the salt for this coldkey directory
    #    and generate the Fernet encryption key
    # ----------------------------------------------------------------
    salt = get_or_create_salt(coldkey_dir)
    enc_key = generate_encryption_key(password, salt)
    cipher = Fernet(enc_key)

    # ----------------------------------------------------------------
    # 3) Read hotkeys.json, then find the relevant encrypted_data
    # ----------------------------------------------------------------
    hotkeys_json_path = os.path.join(coldkey_dir, "hotkeys.json")
    if not os.path.exists(hotkeys_json_path):
        raise FileNotFoundError(f"hotkeys.json not found at {hotkeys_json_path}")

    with open(hotkeys_json_path, "r") as f:
        data = json.load(f)

    if "hotkeys" not in data:
        raise KeyError("'hotkeys' field is missing in hotkeys.json")

    if hotkey_name not in data["hotkeys"]:
        raise FileNotFoundError(f"Hotkey '{hotkey_name}' not found in hotkeys.json")

    encrypted_data = data["hotkeys"][hotkey_name].get("encrypted_data")
    if not encrypted_data:
        raise KeyError(f"'encrypted_data' missing for hotkey '{hotkey_name}'")

    # ----------------------------------------------------------------
    # 4) Decrypt the hotkey data and parse JSON
    # ----------------------------------------------------------------
    try:
        decrypted_bytes = cipher.decrypt(encrypted_data.encode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to decrypt hotkey '{hotkey_name}': {e}")
        raise Exception("Hotkey decryption failed. Invalid password or data.")

    hotkey_data = json.loads(decrypted_bytes.decode("utf-8"))

    # ----------------------------------------------------------------
    # 5) Extract the hex-encoded CBOR strings for payment & stake keys
    # ----------------------------------------------------------------
    pay_hex = hotkey_data.get("payment_xsk_cbor_hex")
    stk_hex = hotkey_data.get("stake_xsk_cbor_hex")

    if not pay_hex or not stk_hex:
        raise KeyError(
            f"Missing 'payment_xsk_cbor_hex' or 'stake_xsk_cbor_hex' "
            f"in the decrypted data for hotkey '{hotkey_name}'."
        )

    # ----------------------------------------------------------------
    # 6) Convert hex to bytes, then to ExtendedSigningKey objects
    # ----------------------------------------------------------------
    payment_xsk = ExtendedSigningKey.from_cbor(binascii.unhexlify(pay_hex))
    stake_xsk = ExtendedSigningKey.from_cbor(binascii.unhexlify(stk_hex))

    logger.info(
        f"[decode_hotkey_skey] Successfully decoded hotkey '{hotkey_name}' "
        f"under coldkey '{coldkey_name}'."
    )

    return (payment_xsk, stake_xsk)
