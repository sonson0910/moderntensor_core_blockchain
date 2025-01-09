# keymanager/wallet_manager.py
import os
import json
import logging
from pycardano import Network
from .coldkey_manager import ColdKeyManager
from .hotkey_manager import HotKeyManager

logging.basicConfig(level=logging.INFO)


class WalletManager:
    def __init__(self, network=Network.TESTNET, base_dir="moderntensor"):
        self.network = network
        self.base_dir = base_dir

        # Create an instance of ColdKeyManager
        self.ck_manager = ColdKeyManager(base_dir=base_dir)
        # Instead of ck_manager storing the dict locally, we reference ck_manager.coldkeys
        self.hk_manager = HotKeyManager(
            coldkeys_dict=self.ck_manager.coldkeys, base_dir=base_dir, network=network
        )

    def create_coldkey(self, name: str, password: str):
        return self.ck_manager.create_coldkey(name, password)

    def load_coldkey(self, name: str, password: str):
        return self.ck_manager.load_coldkey(name, password)

    def generate_hotkey(self, coldkey_name: str, hotkey_name: str):
        return self.hk_manager.generate_hotkey(coldkey_name, hotkey_name)

    def import_hotkey(
        self,
        coldkey_name: str,
        encrypted_hotkey: str,
        hotkey_name: str,
        overwrite=False,
    ):
        return self.hk_manager.import_hotkey(
            coldkey_name, encrypted_hotkey, hotkey_name, overwrite
        )

    def load_all_wallets(self):
        """
        Duyệt thư mục base_dir, trả về list dict:
        [
        {
            "name": <tên coldkey>,
            "address": <chuỗi address (nếu có)>,
            "hotkeys": [
            {"name": ..., "address": ...},  # Plaintext address
            ...
            ]
        },
        ...
        ]
        """
        wallets = []
        if not os.path.isdir(self.base_dir):
            logging.warning(f"Base dir {self.base_dir} không tồn tại.")
            return wallets

        for entry in os.scandir(self.base_dir):
            if entry.is_dir():
                coldkey_name = entry.name
                coldkey_dir = os.path.join(self.base_dir, coldkey_name)
                
                # Nếu bạn muốn có address của coldkey, bạn có thể derive ở đây
                # hoặc để None nếu chưa triển khai:
                coldkey_address = None

                hotkeys_json = os.path.join(coldkey_dir, "hotkeys.json")
                hotkeys_list = []
                if os.path.isfile(hotkeys_json):
                    with open(hotkeys_json, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    # data = {
                    #   "hotkeys": {
                    #     "hkName": {
                    #       "address": "addr_test1...",
                    #       "encrypted_data": "gAAAAAB..."
                    #     },
                    #     ...
                    #   }
                    # }

                    if "hotkeys" in data:
                        for hk_name, hk_info in data["hotkeys"].items():
                            # Mỗi hk_info là 1 dict: {"address": "...", "encrypted_data": "..."}
                            address_plaintext = hk_info.get("address", None)
                            # Chưa giải mã "encrypted_data" (chứa private/pub key), ta chỉ hiển thị address
                            
                            hotkeys_list.append({
                                "name": hk_name,
                                "address": address_plaintext
                            })

                wallets.append({
                    "name": coldkey_name,
                    "hotkeys": hotkeys_list
                })

        return wallets
