# keymanager/wallet_manager.py

import os
import json
import logging
from pycardano import Network
from .coldkey_manager import ColdKeyManager
from .hotkey_manager import HotKeyManager

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class WalletManager:
    """
    A higher-level manager that ties together ColdKeyManager and HotKeyManager.
    This class provides a simple interface to create and load coldkeys, 
    generate/import hotkeys, and list all wallets and their hotkeys from the base directory.
    """

    def __init__(self, network=Network.TESTNET, base_dir="moderntensor"):
        """
        Initialize WalletManager with a specific Cardano network and a base directory.

        Args:
            network (Network): The Cardano network to use (TESTNET or MAINNET). Default is TESTNET.
            base_dir (str): The folder for storing coldkey and hotkey data. Default is "moderntensor".
        """
        self.network = network
        self.base_dir = base_dir

        # Create an instance of ColdKeyManager to handle mnemonic-based coldkeys
        self.ck_manager = ColdKeyManager(base_dir=base_dir)

        # Create a HotKeyManager to handle individual hotkeys. 
        # We pass self.ck_manager.coldkeys so both managers share the same dictionary reference.
        self.hk_manager = HotKeyManager(
            coldkeys_dict=self.ck_manager.coldkeys,
            base_dir=base_dir,
            network=network
        )

    def create_coldkey(self, name: str, password: str):
        """
        Create a new coldkey (and encrypt its mnemonic) under the specified name.

        Args:
            name (str): Unique name for the new coldkey.
            password (str): Password used to encrypt the coldkey's mnemonic.

        Returns:
            None (but writes files to disk and updates self.ck_manager.coldkeys)
        """
        return self.ck_manager.create_coldkey(name, password)

    def load_coldkey(self, name: str, password: str):
        """
        Load a previously created coldkey by decrypting its mnemonic.enc file.

        Args:
            name (str): Name of the coldkey to load.
            password (str): Password used to decrypt the mnemonic.

        Returns:
            None (but updates self.ck_manager.coldkeys with the loaded coldkey data)
        """
        return self.ck_manager.load_coldkey(name, password)

    def generate_hotkey(self, coldkey_name: str, hotkey_name: str):
        """
        Create a new hotkey under an existing coldkey. 

        Args:
            coldkey_name (str): The name of the coldkey to derive this hotkey from.
            hotkey_name (str): A unique identifier for the new hotkey.

        Returns:
            str: The encrypted hotkey data in a base64-encoded string.
        """
        return self.hk_manager.generate_hotkey(coldkey_name, hotkey_name)

    def import_hotkey(
        self,
        coldkey_name: str,
        encrypted_hotkey: str,
        hotkey_name: str,
        overwrite=False,
    ):
        """
        Import a hotkey from an encrypted string. Decrypts the extended signing keys
        and writes them to hotkeys.json.

        Args:
            coldkey_name (str): Name of the coldkey that will own this hotkey.
            encrypted_hotkey (str): The encrypted hotkey data (base64).
            hotkey_name (str): A unique name for the imported hotkey.
            overwrite (bool): If True, overwrite existing hotkey without prompting.

        Returns:
            None
        """
        return self.hk_manager.import_hotkey(
            coldkey_name, encrypted_hotkey, hotkey_name, overwrite
        )

    def load_all_wallets(self):
        """
        Scan the base directory for coldkey folders, read their hotkeys.json files,
        and build a list describing each coldkey and its hotkeys.

        Returns:
            list of dict: Each dictionary has the form:
            [
                {
                    "name": <coldkey_name>,
                    "hotkeys": [
                        {"name": <hotkey_name>, "address": <plaintext_address>},
                        ...
                    ]
                },
                ...
            ]
        """
        wallets = []
        
        # If the base directory does not exist, log a warning and return an empty list.
        if not os.path.isdir(self.base_dir):
            logger.warning(f"Base directory '{self.base_dir}' does not exist.")
            return wallets

        # Scan through each entry in the base directory to find coldkey folders
        for entry in os.scandir(self.base_dir):
            if entry.is_dir():
                coldkey_name = entry.name
                coldkey_dir = os.path.join(self.base_dir, coldkey_name)
                
                # hotkeys.json stores the addresses and encrypted data for each hotkey
                hotkeys_json_path = os.path.join(coldkey_dir, "hotkeys.json")
                hotkeys_list = []

                if os.path.isfile(hotkeys_json_path):
                    with open(hotkeys_json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    # Example data structure:
                    # {
                    #   "hotkeys": {
                    #       "hkName": {
                    #           "address": "...",
                    #           "encrypted_data": "..."
                    #       },
                    #       ...
                    #   }
                    # }
                    
                    if "hotkeys" in data:
                        for hk_name, hk_info in data["hotkeys"].items():
                            # hk_info is a dict: {"address": "...", "encrypted_data": "..."}
                            # We only display the address here without decrypting the private keys
                            address_plaintext = hk_info.get("address", None)
                            hotkeys_list.append({
                                "name": hk_name,
                                "address": address_plaintext
                            })

                wallets.append({
                    "name": coldkey_name,
                    "hotkeys": hotkeys_list
                })

        return wallets
