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
    Decrypts the hotkey skey (extended signing key) that is stored in hotkeys.json
    as `encrypted_data` (using Fernet).

    Requirements:
        - hotkeys.json has the structure:
             {
                "hotkeys": {
                   "myhot1": {
                      "address": "...",
                      "encrypted_data": "...(base64-encoded string)..."
                   }
                }
             }
        - Inside 'encrypted_data', after decryption, we expect a JSON like:
             {
               "payment_xsk_cbor_hex": "...",
               "stake_xsk_cbor_hex": "..."
             }
          (this follows the logic from the old generate_hotkey function)
        - We then call ExtendedSigningKey.from_cbor(...) to retrieve the extended key objects.
    
    Returns:
        A tuple of (payment_xsk, stake_xsk) where each is an ExtendedSigningKey instance.
    """

    # Construct the path to the specified coldkey directory
    coldkey_dir = os.path.join(base_dir, coldkey_name)
    
    # Retrieve or create the salt file (salt.bin) in the coldkey directory
    # The salt is used to derive the Fernet encryption key
    salt = get_or_create_salt(coldkey_dir)
    
    # Generate the encryption/decryption key from the provided password + salt
    enc_key = generate_encryption_key(password, salt)
    
    # Create a Fernet cipher object using the derived key
    cipher = Fernet(enc_key)

    # Load the hotkeys.json file to read the encrypted data for the specified hotkey
    hotkeys_json_path = os.path.join(coldkey_dir, "hotkeys.json")
    with open(hotkeys_json_path, "r") as f:
        data = json.load(f)

    # Retrieve the base64-encoded encrypted data for the given hotkey
    enc_data = data["hotkeys"][hotkey_name]["encrypted_data"]
    
    # Decrypt the data (which should be JSON-encoded bytes after decryption)
    dec = cipher.decrypt(enc_data.encode("utf-8"))
    
    # Convert the decrypted bytes into a dictionary
    hotkey_data = json.loads(dec.decode("utf-8"))

    # Extract the payment and stake extended key hex strings
    pay_hex = hotkey_data["payment_xsk_cbor_hex"]
    stk_hex = hotkey_data["stake_xsk_cbor_hex"]

    # Convert the hex-encoded CBOR strings back to bytes, then load as ExtendedSigningKey
    payment_xsk = ExtendedSigningKey.from_cbor(binascii.unhexlify(pay_hex))
    stake_xsk = ExtendedSigningKey.from_cbor(binascii.unhexlify(stk_hex))

    # Return both extended signing keys as a tuple
    return (payment_xsk, stake_xsk)
