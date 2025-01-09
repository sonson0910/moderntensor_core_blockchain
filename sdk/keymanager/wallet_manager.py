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
        Quét thư mục base_dir, trả về list dict:
        [
          {
            "name": <tên coldkey>,
            "address": <chuỗi address (nếu có)>,
            "hotkeys": [
              {"name": ..., "address": ...},
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
                
                # [1] Parse address coldkey (nếu bạn lưu address ở file, hoặc auto-lấy?)
                #    Ở đây ta ví dụ address chưa có => để rỗng
                coldkey_address = None

                # [2] Lấy thông tin hotkeys
                hotkeys_json = os.path.join(coldkey_dir, "hotkeys.json")
                hotkeys_list = []
                if os.path.isfile(hotkeys_json):
                    with open(hotkeys_json, "r") as f:
                        data = json.load(f)
                    # data = {"hotkeys": {"hkName": "<encrypted>"...}}
                    if "hotkeys" in data:
                        for hk_name, encrypted in data["hotkeys"].items():
                            # Giả sử ta chưa parse "address" do encrypted => chỉ hiển thị name
                            # Nếu bạn có code parse => decode => JSON => address
                            hotkey_info = {
                                "name": hk_name,
                                "address": None  # Chưa giải mã
                            }
                            hotkeys_list.append(hotkey_info)
                
                wallets.append({
                    "name": coldkey_name,
                    "address": coldkey_address,
                    "hotkeys": hotkeys_list
                })
        
        return wallets