# keymanager/hotkey_manager.py

import os
import json
import logging
from cryptography.fernet import Fernet
from pycardano import (
    Address,
    Network,
    PaymentVerificationKey,
    StakeVerificationKey,
    ExtendedSigningKey,
    ExtendedVerificationKey
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class HotKeyManager:
    """
    Theo logic cũ:
      - generate_hotkey => trả về encrypted_hotkey (chuỗi)
      - hotkeys.json => { "address":..., "encrypted_data":... }
      - import_hotkey(..., encrypted_hotkey, hotkey_name, overwrite=False) => giải mã => store => 'encrypted_data'
      - Fix: Lưu cbor dưới dạng hex => không còn lỗi JSON.
    """

    def __init__(
        self,
        coldkeys_dict: dict,  # { coldkey_name -> {"wallet": HDWallet, "cipher_suite":..., "hotkeys": {...}} }
        base_dir="moderntensor",
        network=Network.TESTNET
    ):
        self.coldkeys = coldkeys_dict
        self.base_dir = base_dir
        self.network = network or Network.TESTNET

    def generate_hotkey(self, coldkey_name: str, hotkey_name: str):
        """
        Tạo mới HotKey => private key (extended) mã hoá => 'encrypted_data'.
        Lưu { "address", "encrypted_data" } => hotkeys.json.
        Trả về chuỗi encrypted_hotkey.
        """
        if coldkey_name not in self.coldkeys:
            raise ValueError(f"Coldkey '{coldkey_name}' does not exist in memory.")

        wallet_info = self.coldkeys[coldkey_name]
        coldkey_wallet = wallet_info["wallet"]
        cipher_suite: Fernet = wallet_info["cipher_suite"]
        hotkeys_dict = wallet_info["hotkeys"]

        # Kiểm tra trùng
        if hotkey_name in hotkeys_dict:
            raise Exception(f"Hotkey '{hotkey_name}' already exists for coldkey '{coldkey_name}'.")

        idx = len(hotkeys_dict)

        # 1) Derive extended signing key (payment)
        payment_child = coldkey_wallet.derive_from_path(f"m/1852'/1815'/0'/0/{idx}")
        payment_xsk = ExtendedSigningKey.from_hdwallet(payment_child)
        payment_xvk = payment_xsk.to_verification_key()

        # 2) Derive stake => address
        stake_child = coldkey_wallet.derive_from_path(f"m/1852'/1815'/0'/2/{idx}")
        stake_vk = StakeVerificationKey.from_primitive(stake_child.public_key)
        hotkey_address = Address(payment_xvk.hash(), stake_vk.hash(), network=self.network)

        # 3) Lưu extended key ở dạng hex
        pmt_skey_cbor = payment_xsk.to_cbor()   # bytes
        pmt_skey_hex  = pmt_skey_cbor.hex()     # convert to hex => str

        # Tạo data JSON-friendly
        hotkey_data = {
            "name": hotkey_name,
            "address": str(hotkey_address),
            "payment_xsk_cbor_hex": pmt_skey_hex
        }

        # 4) Mã hoá JSON => encrypted_hotkey
        raw_json = json.dumps(hotkey_data).encode("utf-8")
        encrypted_bytes = cipher_suite.encrypt(raw_json)
        encrypted_hotkey = encrypted_bytes.decode("utf-8")

        # 5) Ghi hotkeys.json => "address", "encrypted_data"
        hotkeys_dict[hotkey_name] = {
            "address": str(hotkey_address),
            "encrypted_data": encrypted_hotkey
        }

        coldkey_dir = os.path.join(self.base_dir, coldkey_name)
        os.makedirs(coldkey_dir, exist_ok=True)
        hotkey_path = os.path.join(coldkey_dir, "hotkeys.json")
        with open(hotkey_path, "w") as f:
            json.dump({"hotkeys": hotkeys_dict}, f, indent=2)

        logger.info(f"[generate_hotkey] Hot Key '{hotkey_name}' => address={hotkey_address}")
        return encrypted_hotkey

    def import_hotkey(
        self,
        coldkey_name: str,
        encrypted_hotkey: str,
        hotkey_name: str,
        overwrite=False
    ):
        """
        Test cũ calls: import_hotkey(name, enc_data, hotkey_name, overwrite=False)
        => Check overwrite => decode => parse => store => 'encrypted_data'
        => Tạo extended verification => address => log
        => Ko còn lỗi 32 bytes do xài extended key
        """
        if coldkey_name not in self.coldkeys:
            raise ValueError(f"[import_hotkey] Cold Key '{coldkey_name}' not in memory.")

        wallet_info = self.coldkeys[coldkey_name]
        cipher_suite: Fernet = wallet_info["cipher_suite"]
        hotkeys_dict = wallet_info["hotkeys"]

        # 1) Check overwrite
        if hotkey_name in hotkeys_dict and not overwrite:
            response = input(f"Hot Key '{hotkey_name}' already exists. Overwrite? (yes/no): ").strip().lower()
            if response not in ("yes", "y"):
                logging.warning("[import_hotkey] User canceled overwrite => import aborted.")
                return
            logging.warning(f"[import_hotkey] Overwriting Hot Key '{hotkey_name}'.")

        # 2) Giải mã => hotkey_data (JSON)
        raw_decrypted = cipher_suite.decrypt(encrypted_hotkey.encode("utf-8"))
        hotkey_data = json.loads(raw_decrypted.decode("utf-8"))
        # => { "name":..., "address":..., "payment_xsk_cbor_hex":... }

        # 3) Override name
        hotkey_data["name"] = hotkey_name

        # 4) Tái tạo extended key => address
        pmt_skey_hex = hotkey_data["payment_xsk_cbor_hex"]  # hex
        import binascii
        pmt_skey_cbor = binascii.unhexlify(pmt_skey_hex)     # bytes
        payment_xsk = ExtendedSigningKey.from_cbor(pmt_skey_cbor)
        payment_xvk = payment_xsk.to_verification_key()
        # stake key optional => ta xài address cũ sẵn trong hotkey_data:
        final_address = hotkey_data["address"]

        # 5) Ghi hotkeys.json => 'address', 'encrypted_data'
        hotkeys_dict[hotkey_name] = {
            "address": final_address,
            "encrypted_data": encrypted_hotkey
        }

        coldkey_dir = os.path.join(self.base_dir, coldkey_name)
        hotkey_path = os.path.join(coldkey_dir, "hotkeys.json")
        with open(hotkey_path, "w") as f:
            json.dump({"hotkeys": hotkeys_dict}, f, indent=2)

        logger.info(f"[import_hotkey] Hot Key '{hotkey_name}' imported successfully.")
