# sdk/keymanager/wallet_manager.py

import os
import json

from sdk.config.settings import settings, logger
from sdk.keymanager.coldkey_manager import ColdKeyManager
from sdk.keymanager.hotkey_manager import HotKeyManager


class WalletManager:
    """
    A higher-level manager that ties together ColdKeyManager and HotKeyManager.
    This class provides a simple interface to create and load coldkeys,
    generate/import hotkeys, and list all wallets and their hotkeys from the base directory.
    """

    def __init__(self, network=None, base_dir=None):
        """
        Initializes WalletManager with a specific Cardano network and a base directory.

        Args:
            network (Network, optional): The Cardano network to use (TESTNET or MAINNET).
                                         Defaults to settings.CARDANO_NETWORK if None.
            base_dir (str, optional): The folder for storing coldkey and hotkey data.
                                      Defaults to settings.HOTKEY_BASE_DIR if None.
        """
        self.network = network or settings.CARDANO_NETWORK
        self.base_dir = base_dir or settings.HOTKEY_BASE_DIR

        # Initialize the ColdKeyManager with the chosen base directory
        self.ck_manager = ColdKeyManager(base_dir=self.base_dir)

        # Create a HotKeyManager, sharing the same coldkeys dictionary
        self.hk_manager = HotKeyManager(
            coldkeys_dict=self.ck_manager.coldkeys,
            base_dir=self.base_dir,
            network=self.network,  # type: ignore
        )

    def create_coldkey(self, name: str, password: str):
        """
        Create a new coldkey (and encrypt its mnemonic) under the specified name.

        Args:
            name (str): Unique name for the new coldkey.
            password (str): Password used to encrypt the coldkey's mnemonic.

        Returns:
            None: Writes files to disk and updates self.ck_manager.coldkeys.
        """
        return self.ck_manager.create_coldkey(name, password)

    def load_coldkey(self, name: str, password: str):
        """
        Load a previously created coldkey by decrypting its mnemonic.enc file.

        Args:
            name (str): Name of the coldkey to load.
            password (str): Password used to decrypt the mnemonic.

        Returns:
            None: Updates self.ck_manager.coldkeys with the loaded coldkey data.
        """
        return self.ck_manager.load_coldkey(name, password)

    def generate_hotkey(self, coldkey_name: str, hotkey_name: str):
        """
        Create a new hotkey under an existing coldkey.

        Args:
            coldkey_name (str): The name of the coldkey from which to derive this hotkey.
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
            encrypted_hotkey (str): The encrypted hotkey data (base64-encoded).
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
            list of dict: A list of dictionaries, each describing a coldkey and its hotkeys.
            Example:
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

        if not os.path.isdir(self.base_dir):
            logger.warning(f"Base directory '{self.base_dir}' does not exist.")
            return wallets

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
                            # We only display the address without decrypting keys
                            address_plaintext = hk_info.get("address", None)
                            hotkeys_list.append(
                                {"name": hk_name, "address": address_plaintext}
                            )

                wallets.append({"name": coldkey_name, "hotkeys": hotkeys_list})

        return wallets

    def get_hotkey_info(self, coldkey_name: str, hotkey_name: str):
        """
        Retrieve information about a specific hotkey under a given coldkey.

        Args:
            coldkey_name (str): The name of the parent coldkey.
            hotkey_name (str): The name of the hotkey to retrieve.

        Returns:
            dict | None: A dictionary containing the hotkey's info (e.g., 'address', 'encrypted_data')
                         if found, otherwise None.
        """
        coldkey_dir = os.path.join(self.base_dir, coldkey_name)
        hotkeys_json_path = os.path.join(coldkey_dir, "hotkeys.json")

        if not os.path.isfile(hotkeys_json_path):
            logger.error(
                f"Hotkey file not found for coldkey '{coldkey_name}': {hotkeys_json_path}"
            )
            return None

        try:
            with open(hotkeys_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            hotkey_data = data.get("hotkeys", {}).get(hotkey_name)
            if hotkey_data:
                # Return the whole info dict for that hotkey
                return hotkey_data
            else:
                logger.error(
                    f"Hotkey '{hotkey_name}' not found under coldkey '{coldkey_name}'."
                )
                return None
        except json.JSONDecodeError:
            logger.exception(f"Error decoding JSON from {hotkeys_json_path}")
            return None
        except Exception as e:
            logger.exception(
                f"An unexpected error occurred while getting hotkey info: {e}"
            )
            return None
