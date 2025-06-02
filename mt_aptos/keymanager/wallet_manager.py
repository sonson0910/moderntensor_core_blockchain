# sdk/keymanager/wallet_manager.py

import os
import json
from rich.console import Console
from typing import Optional

from mt_aptos.config.settings import settings, logger
from mt_aptos.keymanager.coldkey_manager import ColdKeyManager
from mt_aptos.keymanager.hotkey_manager import HotKeyManager


class WalletManager:
    """
    A higher-level manager that ties together ColdKeyManager and HotKeyManager.
    This class provides a simple interface to create and load coldkeys,
    generate/import hotkeys, and list all wallets and their hotkeys from the base directory.
    """

    def __init__(self, network=None, base_dir=None):
        """
        Initializes WalletManager with a specific Aptos network and a base directory.

        Args:
            network (str, optional): The Aptos network to use (mainnet, testnet, devnet, local).
                                     Defaults to settings.APTOS_NETWORK if None.
            base_dir (str, optional): The folder for storing coldkey and hotkey data.
                                      Defaults to settings.HOTKEY_BASE_DIR if None.
        """
        self.network = network or settings.APTOS_NETWORK
        self.base_dir = base_dir or settings.HOTKEY_BASE_DIR

        # Initialize the ColdKeyManager with the chosen base directory
        self.ck_manager = ColdKeyManager(base_dir=self.base_dir)

        # Create a HotKeyManager, sharing the same coldkeys dictionary
        self.hk_manager = HotKeyManager(
            coldkeys_dict=self.ck_manager.coldkeys,
            base_dir=self.base_dir,
            network=self.network,
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
        Load an existing coldkey, derive its keys, and return key information.

        Args:
            name (str): Name of the coldkey to load.
            password (str): Password used to decrypt the mnemonic.

        Returns:
            dict | None: A dictionary containing key information (like 'payment_xsk',
                         'stake_xsk', 'payment_address') returned by ColdKeyManager,
                         or None if loading fails.
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

    def restore_coldkey_from_mnemonic(
        self, name: str, mnemonic: str, new_password: str, force: bool = False
    ):
        """
        Restores a coldkey from a mnemonic phrase, sets a new password,
        and saves the encrypted data.

        Delegates the actual restoration logic to ColdKeyManager.

        Args:
            name (str): Name for the coldkey.
            mnemonic (str): The mnemonic phrase.
            new_password (str): The new password to encrypt the mnemonic.
            force (bool): Overwrite if the coldkey directory exists.

        Returns:
            None: Writes files to disk and updates internal state.

        Raises:
            FileExistsError: If the coldkey directory exists and force is False.
            Exception: If mnemonic validation or other errors occur during restoration.
        """
        return self.ck_manager.restore_coldkey_from_mnemonic(
            name, mnemonic, new_password, force
        )

    def regenerate_hotkey(
        self,
        coldkey_name: str,
        hotkey_name: str,
        index: int,
        force: bool = False,
    ):
        """
        Regenerates a hotkey's data from the parent coldkey and index.

        Delegates the actual regeneration logic to HotKeyManager.

        Args:
            coldkey_name (str): Name of the parent coldkey (must be loaded).
            hotkey_name (str): Name to assign to the regenerated hotkey.
            index (int): The derivation index used originally.
            force (bool): Overwrite if the hotkey entry already exists.

        Returns:
            None: Writes to hotkeys.json and potentially updates internal state.

        Raises:
            ValueError: If coldkey is not loaded or index is invalid.
            Exception: If regeneration fails.
        """
        # Ensure coldkey is loaded before calling hotkey manager
        if coldkey_name not in self.ck_manager.coldkeys:
            raise ValueError(f"Coldkey '{coldkey_name}' is not loaded. Load it first.")

        # Call the corresponding method in HotKeyManager
        return self.hk_manager.regenerate_hotkey(
            coldkey_name, hotkey_name, index, force
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
            logger.warning(
                f":warning: [yellow]Base directory '{self.base_dir}' does not exist.[/yellow]"
            )
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
                f":cross_mark: [red]Hotkey file not found for coldkey '{coldkey_name}':[/red] {hotkeys_json_path}"
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
                    f":cross_mark: [red]Hotkey '{hotkey_name}' not found under coldkey '{coldkey_name}'.[/red]"
                )
                return None
        except json.JSONDecodeError:
            logger.exception(
                f":exclamation: [bold red]Error decoding JSON from[/bold red] {hotkeys_json_path}"
            )
            return None
        except Exception as e:
            logger.exception(
                f":exclamation: [bold red]An unexpected error occurred while getting hotkey info:[/bold red] {e}"
            )
            return None
