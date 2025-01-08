# keymanager/wallet_manager.py
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
