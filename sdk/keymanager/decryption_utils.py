import os
import json
import binascii
from cryptography.fernet import Fernet
from pycardano import ExtendedSigningKey
from sdk.keymanager.encryption_utils import get_or_create_salt, generate_encryption_key

def decode_hotkey_skey(
    base_dir: str,
    coldkey_name: str,
    hotkey_name: str,
    password: str,
) -> ExtendedSigningKey:
    """
    Giải mã skey (extended) được lưu trong hotkey.json dưới dạng encrypted_data (Fernet).
    
    Yêu cầu:
        - hotkey.json: {
             "hotkeys": {
                "myhot1": {
                   "address": "...",
                   "encrypted_data": "...(base64)..."
                }
             }
          }
        - Bên trong encrypted_data (giải mã) -> JSON => 
             { "payment_xsk_cbor_hex": "..." } (theo logic generate_hotkey cũ)
        - Tạo ExtendedSigningKey.from_cbor(...) => trả về extended key
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

    return (payment_xsk, stake_xsk)