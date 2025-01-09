# file: keymanager/hotkey_manager.py

import os
import json
import logging
from pycardano import Address, Network, PaymentVerificationKey, StakeVerificationKey
from cryptography.fernet import Fernet

logging.basicConfig(level=logging.INFO)

class HotKeyManager:
    """
    Manage HotKeys for a coldkey (already loaded).
    """

    def __init__(
        self, coldkeys_dict: dict, base_dir="moderntensor", network=Network.TESTNET
    ):
        """
        :param coldkeys_dict: Reference to a dictionary containing loaded coldkeys (name -> wallet info).
        :param base_dir: Directory containing coldkeys.
        :param network: Cardano network (TESTNET/MAINNET). Default: TESTNET.
        """
        self.coldkeys = coldkeys_dict
        self.base_dir = base_dir
        if network is None:
            network = Network.TESTNET
        self.network = network

    def generate_hotkey(self, coldkey_name: str, hotkey_name: str):
        if coldkey_name not in self.coldkeys:
            raise ValueError(f"Coldkey '{coldkey_name}' does not exist.")
        
        wallet_info = self.coldkeys[coldkey_name]
        coldkey_wallet = wallet_info["wallet"]
        cipher_suite: Fernet = wallet_info["cipher_suite"]
        hotkeys_dict = wallet_info["hotkeys"]

        # Kiểm tra trùng tên hotkey
        if hotkey_name in hotkeys_dict:
            raise Exception(f"Hotkey '{hotkey_name}' already exists for coldkey '{coldkey_name}'.")

        idx = len(hotkeys_dict)  # hotkey index = number of current hotkeys

        # Derive payment key
        payment_wallet = coldkey_wallet.derive_from_path(f"m/1852'/1815'/0'/0/{idx}")
        payment_vk = PaymentVerificationKey.from_primitive(payment_wallet.public_key)

        # Derive stake key
        stake_wallet = coldkey_wallet.derive_from_path(f"m/1852'/1815'/0'/2/{idx}")
        stake_vk = StakeVerificationKey.from_primitive(stake_wallet.public_key)

        # Tạo địa chỉ (pycardano Address)
        hotkey_address = Address(
            payment_vk.hash(), stake_vk.hash(), network=self.network
        )

        # Tạo data gồm address, public keys, name...
        hotkey_data = {
            "name": hotkey_name,
            "address": str(hotkey_address),
            "payment_pub_key_hex": payment_wallet.public_key.hex(),
            "stake_pub_key_hex": stake_wallet.public_key.hex(),
        }

        # Mã hoá toàn bộ hotkey_data
        encrypted_hotkey = cipher_suite.encrypt(
            json.dumps(hotkey_data).encode("utf-8")
        ).decode("utf-8")

        # Lưu 2 phần:
        # 1) address ở dạng plaintext
        # 2) chuỗi mã hoá (encrypted_data)
        hotkeys_dict[hotkey_name] = {
            "address": str(hotkey_address),  # plaintext
            "encrypted_data": encrypted_hotkey
        }

        # Ghi file
        coldkey_dir = os.path.join(self.base_dir, coldkey_name)
        hotkey_path = os.path.join(coldkey_dir, "hotkeys.json")
        with open(hotkey_path, "w") as f:
            json.dump({"hotkeys": hotkeys_dict}, f, indent=2)

        logging.info(f"[generate_hotkey] Hot Key '{hotkey_name}' created.")
        return encrypted_hotkey

    def import_hotkey(
        self,
        coldkey_name: str,
        encrypted_hotkey: str,
        hotkey_name: str,
        overwrite=False,
    ):
        if coldkey_name not in self.coldkeys:
            raise ValueError(f"[import_hotkey] Cold Key '{coldkey_name}' does not exist.")

        wallet_info = self.coldkeys[coldkey_name]
        cipher_suite: Fernet = wallet_info["cipher_suite"]
        hotkeys_dict = wallet_info["hotkeys"]

        # Giải mã hotkey_data
        raw_data = cipher_suite.decrypt(encrypted_hotkey.encode("utf-8")).decode("utf-8")
        hotkey_data = json.loads(raw_data)  
        # hotkey_data = { "name":..., "address":..., "payment_pub_key_hex":..., ... }

        # Ghi đè name (theo hotkey_name mà user cung cấp)
        hotkey_data["name"] = hotkey_name

        # Kiểm tra trùng tên
        if hotkey_name in hotkeys_dict:
            if not overwrite:
                response = input(f"Hot Key '{hotkey_name}' already exists. Overwrite? (yes/no): ").strip().lower()
                if response not in ("yes", "y"):
                    logging.warning("[import_hotkey] User canceled overwrite => import aborted.")
                    return
            logging.warning(f"[import_hotkey] Overwriting Hot Key '{hotkey_name}'.")

        # Tạo payload lưu 2 phần (plaintext address + chuỗi mã hoá)
        hotkeys_dict[hotkey_name] = {
            "address": hotkey_data.get("address", None),  # plaintext address
            "encrypted_data": encrypted_hotkey            # full encryption
        }

        # Ghi file
        coldkey_dir = os.path.join(self.base_dir, coldkey_name)
        hotkey_path = os.path.join(coldkey_dir, "hotkeys.json")
        with open(hotkey_path, "w") as f:
            json.dump({"hotkeys": hotkeys_dict}, f, indent=2)

        logging.info(f"[import_hotkey] Hot Key '{hotkey_name}' imported successfully.")
