# sdk/keymanager/hotkey_manager.py

import os
import json
from cryptography.fernet import Fernet
from mt_aptos.account import Account
from rich.console import Console
from typing import cast, Dict, Optional
import binascii

from mt_aptos.config.settings import settings, logger


class HotKeyManager:
    """
    Manages hotkeys for Aptos accounts, storing them securely with encryption.
    """

    def __init__(
        self,
        coldkeys_dict: dict,  # {coldkey_name -> {"account": Account, "cipher_suite": ..., "hotkeys": {...}}}
        base_dir: str = None,  # type: ignore
    ):
        """
        Initializes the HotKeyManager.

        Args:
            coldkeys_dict (dict): A dictionary holding data for existing coldkeys,
                                  including the associated Aptos Account, a Fernet cipher_suite,
                                  and any existing hotkeys.
            base_dir (str, optional): Base directory for coldkeys. If None,
                                      defaults to settings.HOTKEY_BASE_DIR.
        """
        self.coldkeys = coldkeys_dict
        # Determine the base directory explicitly for type checking
        final_base_dir: str
        if base_dir is not None:
            final_base_dir = base_dir
        else:
            resolved_settings_dir = settings.HOTKEY_BASE_DIR
            if resolved_settings_dir:
                final_base_dir = resolved_settings_dir
            else:
                logger.error(
                    ":stop_sign: [bold red]CRITICAL: base_dir is None and settings.HOTKEY_BASE_DIR is not set.[/bold red]"
                )
                raise ValueError(
                    "Could not determine the base directory for HotKeyManager."
                )
        # Use cast to satisfy the linter
        self.base_dir = cast(str, final_base_dir)

    def generate_hotkey(self, coldkey_name: str, hotkey_name: str) -> str:
        """
        Creates a new hotkey by generating a new Aptos account.

        Steps in detail:
          - Generates a new Aptos account
          - Stores the account details encrypted in the hotkeys.json file

        Args:
            coldkey_name (str): The name of the coldkey under which this hotkey will be generated.
            hotkey_name (str): A unique identifier for this hotkey.

        Raises:
            ValueError: If the coldkey_name doesn't exist in self.coldkeys.
            Exception: If the hotkey_name already exists for that coldkey.

        Returns:
            str: The encrypted hotkey data (base64-encoded string).
        """

        # Verify the coldkey exists in memory
        if coldkey_name not in self.coldkeys:
            raise ValueError(
                f"Coldkey '{coldkey_name}' does not exist in self.coldkeys."
            )

        # Extract Account, cipher_suite, and hotkeys dict from the coldkeys data
        wallet_info = self.coldkeys[coldkey_name]
        cipher_suite: Fernet = wallet_info["cipher_suite"]
        hotkeys_dict = wallet_info["hotkeys"]

        # Check if the hotkey already exists
        if hotkey_name in hotkeys_dict:
            raise Exception(
                f"Hotkey '{hotkey_name}' already exists for coldkey '{coldkey_name}'."
            )

        # Generate a new Aptos account
        account = Account.generate()
        address = account.address().hex()
        if not address.startswith("0x"):
            address = f"0x{address}"

        # Get private key as hex
        private_key_hex = account.private_key.hex()

        # Prepare the hotkey data for encryption
        hotkey_data = {
            "name": hotkey_name,
            "address": address,
            "private_key_hex": private_key_hex,
        }

        # Encrypt the hotkey JSON
        enc_bytes = cipher_suite.encrypt(json.dumps(hotkey_data).encode("utf-8"))
        encrypted_hotkey = enc_bytes.decode("utf-8")

        # Update the in-memory dictionary
        hotkeys_dict[hotkey_name] = {
            "address": address,
            "encrypted_data": encrypted_hotkey,
        }

        # Persist changes to hotkeys.json
        coldkey_dir = os.path.join(self.base_dir, coldkey_name)
        os.makedirs(coldkey_dir, exist_ok=True)
        hotkey_path = os.path.join(coldkey_dir, "hotkeys.json")
        with open(hotkey_path, "w") as f:
            json.dump({"hotkeys": hotkeys_dict}, f, indent=2)

        # Decorated logger info
        logger.info(
            f":sparkles: [green]Generated hotkey[/green] '{hotkey_name}' => address=[blue]{address}[/blue]"
        )
        return encrypted_hotkey

    def import_hotkey(
        self,
        coldkey_name: str,
        encrypted_hotkey: str,
        hotkey_name: str,
        overwrite=False,
    ):
        """
        Imports a hotkey by decrypting the provided encrypted hotkey data and storing
        the resulting address info into 'hotkeys.json'.

        Steps:
          - Decrypts the hotkey JSON (which includes private_key_hex)
          - Recreates the Aptos account
          - (Optionally) prompts the user if a hotkey with the same name already exists
            and overwrite is disabled.
          - Writes the final data to 'hotkeys.json'.

        Args:
            coldkey_name (str): Name of the coldkey under which this hotkey will be stored.
            encrypted_hotkey (str): The encrypted hotkey data (base64-encoded, Fernet).
            hotkey_name (str): The name under which this hotkey will be stored.
            overwrite (bool): If True, overwrite an existing hotkey without prompting.

        Raises:
            ValueError: If the specified coldkey doesn't exist in memory.
        """
        # Ensure the coldkey exists in memory
        if coldkey_name not in self.coldkeys:
            raise ValueError(
                f"[import_hotkey] Cold Key '{coldkey_name}' does not exist in self.coldkeys."
            )

        # Retrieve the cipher suite and hotkeys dictionary
        wallet_info = self.coldkeys[coldkey_name]
        cipher_suite: Fernet = wallet_info["cipher_suite"]
        hotkeys_dict = wallet_info["hotkeys"]

        # If the hotkey already exists and overwrite is False, ask the user
        if hotkey_name in hotkeys_dict and not overwrite:
            # Use Console for interactive prompt (already uses input, but can style message)
            console = Console()
            console.print(
                f":warning: [yellow]Hotkey '{hotkey_name}' already exists.[/yellow]"
            )
            resp = input("Overwrite? (yes/no): ").strip().lower()
            if resp not in ("yes", "y"):
                logger.warning(
                    ":stop_sign: [yellow]User canceled overwrite => import aborted.[/yellow]"
                )
                return
            logger.warning(
                f":warning: [yellow]Overwriting hotkey '{hotkey_name}'.[/yellow]"
            )

        # Decrypt the provided hotkey data
        dec_bytes = cipher_suite.decrypt(encrypted_hotkey.encode("utf-8"))
        hotkey_data = json.loads(dec_bytes.decode("utf-8"))
        hotkey_data["name"] = hotkey_name

        # Extract the private key hex from the decrypted data
        private_key_hex = hotkey_data["private_key_hex"]
        
        # Recreate Aptos account from private key
        account = Account.load_key(bytes.fromhex(private_key_hex))
        
        # Get the address
        address = account.address().hex()
        if not address.startswith("0x"):
            address = f"0x{address}"

        # Update the in-memory dictionary
        hotkeys_dict[hotkey_name] = {
            "address": address,
            "encrypted_data": encrypted_hotkey,
        }

        # Write updated hotkeys to disk
        coldkey_dir = os.path.join(self.base_dir, coldkey_name)
        hotkey_path = os.path.join(coldkey_dir, "hotkeys.json")
        with open(hotkey_path, "w") as f:
            json.dump({"hotkeys": hotkeys_dict}, f, indent=2)

        # Decorated logger info
        logger.info(
            f":inbox_tray: [green]Imported hotkey[/green] '{hotkey_name}' => address=[blue]{address}[/blue]"
        )

    def get_hotkey_account(
        self, coldkey_name: str, hotkey_name: str
    ) -> Optional[Account]:
        """
        Loads and returns the Aptos Account object for a specific hotkey.

        Args:
            coldkey_name (str): The name of the coldkey containing this hotkey.
            hotkey_name (str): The name of the hotkey to load.

        Returns:
            Optional[Account]: The Aptos Account for the hotkey, or None if it can't be loaded.
        """
        # Ensure the coldkey exists
        if coldkey_name not in self.coldkeys:
            logger.error(f"Coldkey '{coldkey_name}' does not exist in self.coldkeys.")
            return None

        # Get the cipher suite and hotkeys
        wallet_info = self.coldkeys[coldkey_name]
        cipher_suite = wallet_info["cipher_suite"]
        hotkeys_dict = wallet_info["hotkeys"]

        # Find the hotkey
        if hotkey_name not in hotkeys_dict:
            logger.error(
                f"Hotkey '{hotkey_name}' does not exist in coldkey '{coldkey_name}'."
            )
            return None

        # Decrypt and load the hotkey
        try:
            encrypted_data = hotkeys_dict[hotkey_name]["encrypted_data"]
            dec_bytes = cipher_suite.decrypt(encrypted_data.encode("utf-8"))
            hotkey_data = json.loads(dec_bytes.decode("utf-8"))
            
            # Extract private key and create account
            private_key_hex = hotkey_data["private_key_hex"]
            account = Account.load_key(bytes.fromhex(private_key_hex))
            
            return account
        except Exception as e:
            logger.error(f"Error loading hotkey '{hotkey_name}': {e}")
            return None

    def get_hotkeys_info(self, coldkey_name: str) -> Dict[str, str]:
        """
        Get all hotkeys for a coldkey with their addresses.

        Args:
            coldkey_name (str): Name of the coldkey.

        Returns:
            Dict[str, str]: Dictionary mapping hotkey names to addresses.
        """
        if coldkey_name not in self.coldkeys:
            return {}

        wallet_info = self.coldkeys[coldkey_name]
        hotkeys_dict = wallet_info["hotkeys"]
        
        # Create a map of hotkey_name -> address
        result = {}
        for name, info in hotkeys_dict.items():
            result[name] = info.get("address", "unknown_address")
            
        return result
