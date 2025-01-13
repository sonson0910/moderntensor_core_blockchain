import os
import json
import binascii
from cryptography.fernet import Fernet
from pycardano import ExtendedSigningKey, Network
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

    # 1) Tạo cipher_suite từ password + salt
    coldkey_dir = os.path.join(base_dir, coldkey_name)
    salt = get_or_create_salt(coldkey_dir)  
    encryption_key = generate_encryption_key(password, salt)
    cipher_suite = Fernet(encryption_key)

    # 2) Đọc hotkey.json
    hotkeys_json_path = os.path.join(coldkey_dir, "hotkeys.json")
    if not os.path.isfile(hotkeys_json_path):
        raise FileNotFoundError(f"hotkeys.json not found: {hotkeys_json_path}")

    with open(hotkeys_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if hotkey_name not in data["hotkeys"]:
        raise ValueError(f"Hotkey '{hotkey_name}' not found in {hotkeys_json_path}")

    # 3) Lấy encrypted_data
    encrypted_data = data["hotkeys"][hotkey_name]["encrypted_data"]  # base64 string

    # 4) Giải mã => parse JSON => lấy "payment_xsk_cbor_hex"
    decrypted_bytes = cipher_suite.decrypt(encrypted_data.encode("utf-8"))
    hotkey_data = json.loads(decrypted_bytes.decode("utf-8"))
    # hotkey_data: {"name":..., "address":..., "payment_xsk_cbor_hex":...}

    xsk_cbor_hex = hotkey_data["payment_xsk_cbor_hex"]
    xsk_cbor = binascii.unhexlify(xsk_cbor_hex)  # bytes cbor

    # 5) Tạo extended signing key
    extended_skey = ExtendedSigningKey.from_cbor(xsk_cbor)

    return extended_skey
