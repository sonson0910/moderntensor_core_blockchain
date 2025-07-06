# keymanager/coldkey_manager.py

import os
import json
from bip_utils import (
    Bip39MnemonicGenerator,
    Bip39Languages,
)
from cryptography.fernet import InvalidToken
from ..account import Account
from rich.console import Console
from typing import cast, Optional

from .encryption_utils import get_cipher_suite
from ..config.settings import settings, logger


class ColdKeyManager:
    """
    Manages the creation and loading of ColdKeys. A ColdKey typically stores a
    mnemonic (encrypted on disk), and is used to derive an Aptos Account.
    """

    def __init__(self, base_dir: str = None):  # type: ignore
        """
        Initialize the ColdKeyManager.

        Args:
            base_dir (str, optional): Custom base directory for storing coldkeys.
                                      If None, defaults to settings.HOTKEY_BASE_DIR.
        """
        # Determine the base directory
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
                    "Could not determine the base directory for ColdKeyManager."
                )

        # Use cast to assure the type checker
        self.base_dir = cast(str, final_base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

        # Dictionary to store coldkeys that are loaded or newly created:
        # {
        #   "coldkey_name": {
        #       "account": Account_object,
        #       "cipher_suite": Fernet_object,
        #       "hotkeys": {...}
        #   },
        #   ...
        # }
        self.coldkeys = {}

    def create_coldkey(self, name: str, password: str, words_num: int = 24):
        """
        Create a new ColdKey by generating a mnemonic (commonly 24 words).

        This method:
          1. Checks whether the coldkey name already exists (in memory or on disk).
          2. Creates an encryption key (Fernet) derived from `password`.
          3. Generates a mnemonic, encrypts, and saves it to 'mnemonic.enc'.
          4. Initializes a corresponding Aptos Account.
          5. Creates a 'hotkeys.json' file to store any future hotkeys.
          6. Stores the resulting data in self.coldkeys.

        Args:
            name (str): Unique name for the coldkey.
            password (str): Password used to encrypt the mnemonic.
            words_num (int): Number of words in the mnemonic (commonly 24).

        Raises:
            Exception: If the coldkey name already exists in memory or on disk.
        """
        # Use Console for user-facing messages
        console = Console()

        # 1) Check if the coldkey name already exists in memory
        if name in self.coldkeys:
            # Use console for error message
            console.print(
                f":cross_mark: [bold red]Error:[/bold red] Coldkey '{name}' already exists in memory."
            )
            raise Exception(f"Coldkey '{name}' already exists in memory.")

        # 2) Create the path for the coldkey (folder name matches the coldkey name)
        coldkey_dir = os.path.join(self.base_dir, name)
        # Prevent overwriting an existing directory for a coldkey
        if os.path.exists(coldkey_dir):
            # Use console for error message
            console.print(
                f":cross_mark: [bold red]Error:[/bold red] Coldkey folder '{coldkey_dir}' already exists."
            )
            raise Exception(f"Coldkey folder '{coldkey_dir}' already exists.")

        os.makedirs(coldkey_dir, exist_ok=True)

        # Create a Fernet cipher suite using the user-provided password + salt
        cipher_suite = get_cipher_suite(password, coldkey_dir)

        # 3) Generate the mnemonic
        mnemonic = str(
            Bip39MnemonicGenerator(lang=Bip39Languages.ENGLISH).FromWordsNumber(
                words_num
            )
        )
        # --- Print mnemonic to console ---
        console.print(f"\n[bold yellow]🔑 Generated Mnemonic:[/bold yellow] {mnemonic}")
        console.print(
            "[bold red]🚨 IMPORTANT: Store this mnemonic phrase securely! It cannot be recovered if lost. 🚨[/bold red]\n"
        )
        # Change logger message to debug level
        logger.debug(
            f":information_source: [dim]Mnemonic generated for Cold Key '{name}'.[/dim]"
        )

        # Encrypt and save the mnemonic in "mnemonic.enc"
        enc_path = os.path.join(coldkey_dir, "mnemonic.enc")
        with open(enc_path, "wb") as f:
            f.write(cipher_suite.encrypt(mnemonic.encode("utf-8")))

        # 4) Initialize an Aptos Account from the generated mnemonic
        account = Account.generate_from_mnemonic(mnemonic)

        # 5) Create an empty "hotkeys.json" file if it doesn't already exist
        hotkeys_path = os.path.join(coldkey_dir, "hotkeys.json")
        if not os.path.exists(hotkeys_path):
            with open(hotkeys_path, "w") as f:
                json.dump({"hotkeys": {}}, f)

        # 6) Store the newly created coldkey data in memory
        self.coldkeys[name] = {
            "account": account,
            "cipher_suite": cipher_suite,
            "hotkeys": {},
        }

        # Use rich markup for final success log message
        logger.info(
            f":heavy_check_mark: [bold green]Cold Key '{name}' created successfully.[/bold green]"
        )

    def load_coldkey(self, name: str, password: str):
        """
        Load an existing coldkey, and return Aptos account information.

        Steps:
          1. Reads 'mnemonic.enc', 'salt.bin'.
          2. Decrypts the mnemonic using the provided password.
          3. Initializes an Aptos Account from the mnemonic.
          4. Returns a dictionary containing essential account info.

        Args:
            name (str): The coldkey name (folder) to load.
            password (str): Password used to decrypt the mnemonic.

        Returns:
            dict: A dictionary containing 'mnemonic', 'account', 'address', 'cipher_suite'.
                  Returns None if loading or decryption fails.
        """
        console = Console()
        coldkey_dir = os.path.join(self.base_dir, name)
        mnemonic_path = os.path.join(coldkey_dir, "mnemonic.enc")

        if not os.path.exists(mnemonic_path):
            console.print(
                f":cross_mark: [bold red]Error:[/bold red] mnemonic.enc not found for Cold Key '{name}'."
            )
            return None

        try:
            cipher_suite = get_cipher_suite(password, coldkey_dir)
            with open(mnemonic_path, "rb") as f:
                encrypted_mnemonic = f.read()
            mnemonic = cipher_suite.decrypt(encrypted_mnemonic).decode("utf-8")

            # Create Aptos account from mnemonic
            account = Account.generate_from_mnemonic(mnemonic)
            address = account.address().hex()
            if not address.startswith("0x"):
                address = f"0x{address}"
            
            # Update internal state (Optional - Load hotkeys if needed for other methods)
            hotkeys_data = {}
            hotkey_path = os.path.join(coldkey_dir, "hotkeys.json")
            if os.path.exists(hotkey_path):
                try:
                    with open(hotkey_path, "r") as f:
                        hotkeys_data = json.load(f)
                    if "hotkeys" not in hotkeys_data:
                        hotkeys_data["hotkeys"] = {}
                except json.JSONDecodeError:
                    logger.warning(
                        f"Could not decode hotkeys.json for {name}, initializing empty."
                    )
                    hotkeys_data["hotkeys"] = {}
            else:
                hotkeys_data["hotkeys"] = {}

            self.coldkeys[name] = {
                "account": account,
                "cipher_suite": cipher_suite,
                "hotkeys": hotkeys_data.get("hotkeys", {}),
            }

            # Return loaded coldkey info
            return {
                "mnemonic": mnemonic,
                "account": account,
                "address": address,
                "cipher_suite": cipher_suite,
            }

        except InvalidToken:
            console.print(
                f":cross_mark: [bold red]Error:[/bold red] Invalid password for Cold Key '{name}'."
            )
            logger.error(f"Invalid password used for Cold Key '{name}'.")
            return None
        except Exception as e:
            console.print(
                f":cross_mark: [bold red]Error:[/bold red] Failed to load Cold Key '{name}': {e}"
            )
            logger.error(f"Error loading Cold Key '{name}': {e}")
            return None

    def restore_coldkey_from_mnemonic(
        self, name: str, mnemonic: str, new_password: str, force: bool = False
    ):
        """
        Restores a coldkey from a provided mnemonic phrase.

        Args:
            name (str): Name to give the restored coldkey.
            mnemonic (str): The mnemonic phrase to restore from.
            new_password (str): Password to encrypt the coldkey.
            force (bool): If True, overwrites an existing coldkey with the same name.

        Returns:
            bool: True if restoration was successful, False otherwise.
        """
        console = Console()

        # Validate the mnemonic (basic check)
        # This could be improved with actual mnemonic validation
        if not mnemonic or len(mnemonic.split()) < 12:
            console.print(
                f":cross_mark: [bold red]Error:[/bold red] Invalid mnemonic phrase (too short or empty)."
            )
            return False

        # Check if the coldkey already exists and handle accordingly
        coldkey_dir = os.path.join(self.base_dir, name)
        if os.path.exists(coldkey_dir) and not force:
            console.print(
                f":warning: [bold yellow]Warning:[/bold yellow] Coldkey '{name}' already exists."
            )
            user_input = input("Overwrite? (yes/no): ").strip().lower()
            if user_input not in ["yes", "y"]:
                console.print(
                    f":information_source: [bold blue]Info:[/bold blue] Restoration cancelled."
                )
                return False

        # Create the coldkey directory if needed
        os.makedirs(coldkey_dir, exist_ok=True)

        # Create cipher suite
        cipher_suite = get_cipher_suite(new_password, coldkey_dir)

        # Encrypt and save the mnemonic
        enc_path = os.path.join(coldkey_dir, "mnemonic.enc")
        with open(enc_path, "wb") as f:
            f.write(cipher_suite.encrypt(mnemonic.encode("utf-8")))

        # Create Aptos account from mnemonic
        try:
            account = Account.generate_from_mnemonic(mnemonic)
        except Exception as e:
            console.print(
                f":cross_mark: [bold red]Error:[/bold red] Failed to create Aptos account from mnemonic: {e}"
            )
            return False

        # Create/reset hotkeys.json
        hotkeys_path = os.path.join(coldkey_dir, "hotkeys.json")
        with open(hotkeys_path, "w") as f:
            json.dump({"hotkeys": {}}, f)

        # Update in-memory state
        self.coldkeys[name] = {
            "account": account,
            "cipher_suite": cipher_suite,
            "hotkeys": {},
        }

        console.print(
            f":heavy_check_mark: [bold green]Success:[/bold green] Coldkey '{name}' restored successfully."
        )
        return True

    def get_coldkey_address(self, name: str) -> Optional[str]:
        """
        Get the Aptos address for a coldkey.

        Args:
            name (str): Name of the coldkey.

        Returns:
            Optional[str]: The Aptos address, or None if the coldkey doesn't exist.
        """
        if name not in self.coldkeys:
            return None

        account = self.coldkeys[name]["account"]
        address = account.address().hex()
        if not address.startswith("0x"):
            address = f"0x{address}"
            
        return address
