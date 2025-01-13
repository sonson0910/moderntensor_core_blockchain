# tests/conftest.py

import os
import json
import binascii
import pytest
from cryptography.fernet import Fernet
from pycardano import ExtendedSigningKey
from sdk.keymanager.encryption_utils import get_or_create_salt, generate_encryption_key

def decode_hotkey_skeys(base_dir, coldkey_name, hotkey_name, password):
    """
    Read hotkeys.json => encrypted_data => Fernet decrypt => parse => payment_xsk, stake_xsk
    """
    coldkey_dir = os.path.join(base_dir, coldkey_name)
    salt = get_or_create_salt(coldkey_dir)
    enc_key = generate_encryption_key(password, salt)
    cipher = Fernet(enc_key)

    hotkeys_json_path = os.path.join(coldkey_dir, "hotkeys.json")
    with open(hotkeys_json_path, "r") as f:
        data = json.load(f)

    enc_data = data["hotkeys"][hotkey_name]["encrypted_data"]
    dec = cipher.decrypt(enc_data.encode("utf-8"))
    hotkey_data = json.loads(dec.decode("utf-8"))

    pay_hex = hotkey_data["payment_xsk_cbor_hex"]
    stk_hex = hotkey_data["stake_xsk_cbor_hex"]

    payment_xsk = ExtendedSigningKey.from_cbor(binascii.unhexlify(pay_hex))
    stake_xsk = ExtendedSigningKey.from_cbor(binascii.unhexlify(stk_hex))

    return payment_xsk, stake_xsk

@pytest.fixture(scope="session")
def hotkey_skey_fixture():
    base_dir = os.getenv("HOTKEY_BASE_DIR", "moderntensor")
    coldkey_name = os.getenv("COLDKEY_NAME", "kickoff")
    hotkey_name = os.getenv("HOTKEY_NAME", "hk1")
    password = os.getenv("HOTKEY_PASSWORD", "sonlearn2003")

    pmt, stk = decode_hotkey_skeys(base_dir, coldkey_name, hotkey_name, password)
    return (pmt, stk)
