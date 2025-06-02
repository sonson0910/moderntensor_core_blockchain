# keymanager/decryption_utils.py

import os
import json
import binascii
from cryptography.fernet import Fernet, InvalidToken
from mt_aptos.account import Account
from rich.console import Console
from typing import cast, Tuple, Optional

from mt_aptos.keymanager.encryption_utils import get_or_create_salt, generate_encryption_key
from mt_aptos.config.settings import settings, logger


def decode_hotkey_account(
    base_dir: Optional[str] = None,
    coldkey_name: str = "",
    hotkey_name: str = "",
    password: str = "",
) -> Optional[Account]:
    """
    Decrypts and returns an Aptos Account for a specific hotkey.

    Retrieves the encrypted data for the specified hotkey from the corresponding
    'hotkeys.json' file within the coldkey's directory. It then uses the provided
    password to derive the encryption key (via Fernet) and decrypts the data.
    Finally, it reconstructs the Aptos Account object from the private key.

    Steps:
        1. Determine the correct base directory for coldkeys (uses settings if None).
        2. Construct the path to the specific coldkey directory.
        3. Get the salt for the coldkey directory.
        4. Generate the Fernet encryption key using the password and salt.
        5. Read 'hotkeys.json' from the coldkey directory.
        6. Locate the specified hotkey entry and extract its 'encrypted_data'.
        7. Decrypt the data using the Fernet cipher.
        8. Parse the decrypted JSON data.
        9. Extract the private key hex.
        10. Create an Aptos Account from the private key.

    Args:
        base_dir (Optional[str], optional): Base directory path for coldkeys.
            Defaults to `settings.HOTKEY_BASE_DIR` if None.
        coldkey_name (str): The name (folder name) of the coldkey.
        hotkey_name (str): The name of the specific hotkey within `hotkeys.json`.
        password (str): The password associated with the coldkey, required for decryption.

    Returns:
        Optional[Account]: The Aptos Account for the hotkey, or None if it can't be loaded.

    Raises:
        ValueError: If the base directory cannot be determined.
        FileNotFoundError: If the `hotkeys.json` file does not exist or the
                           specified `hotkey_name` is not found within the file.
        KeyError: If essential keys are missing in the `hotkeys.json` structure or the decrypted data.
        cryptography.fernet.InvalidToken: If decryption fails, likely due to an
                                         incorrect password or corrupted data.
        Exception: Catches other potential errors during file I/O or JSON parsing.
    """

    # ----------------------------------------------------------------
    # 1) Determine the base directory (use settings if not provided)
    # ----------------------------------------------------------------
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
                "Could not determine the base directory for decoding hotkey."
            )

    # Use cast here for os.path.join because final_base_dir is confirmed str
    coldkey_dir = os.path.join(cast(str, final_base_dir), coldkey_name)

    # ----------------------------------------------------------------
    # 2) Retrieve or create the salt for this coldkey directory
    #    and generate the Fernet encryption key
    # ----------------------------------------------------------------
    # Propagates exceptions from get_or_create_salt (IOError, OSError)
    salt = get_or_create_salt(coldkey_dir)
    # Propagates exceptions from generate_encryption_key (ValueError)
    enc_key = generate_encryption_key(password, salt)
    cipher = Fernet(enc_key)

    # ----------------------------------------------------------------
    # 3) Read hotkeys.json, then find the relevant encrypted_data
    # ----------------------------------------------------------------
    hotkeys_json_path = os.path.join(coldkey_dir, "hotkeys.json")
    if not os.path.exists(hotkeys_json_path):
        logger.error(
            f":file_folder: [red]hotkeys.json not found at {hotkeys_json_path}[/red]"
        )
        raise FileNotFoundError(f"hotkeys.json not found at {hotkeys_json_path}")

    try:
        with open(hotkeys_json_path, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(
            f":warning: [red]Failed to parse JSON from {hotkeys_json_path}: {e}[/red]"
        )
        raise Exception(f"Failed to parse {hotkeys_json_path}")
    except IOError as e:
        logger.error(f":warning: [red]Failed to read {hotkeys_json_path}: {e}[/red]")
        raise

    if "hotkeys" not in data:
        logger.error(
            f":warning: [red]'hotkeys' key missing in {hotkeys_json_path}[/red]"
        )
        raise KeyError("'hotkeys' field is missing in hotkeys.json")

    if hotkey_name not in data["hotkeys"]:
        logger.error(
            f":mag: [red]Hotkey '{hotkey_name}' not found in {hotkeys_json_path}[/red]"
        )
        raise FileNotFoundError(f"Hotkey '{hotkey_name}' not found in hotkeys.json")

    encrypted_data = data["hotkeys"][hotkey_name].get("encrypted_data")
    if not encrypted_data:
        logger.error(
            f":lock: [red]'encrypted_data' missing for hotkey '{hotkey_name}'[/red]"
        )
        raise KeyError(f"'encrypted_data' missing for hotkey '{hotkey_name}'")

    # ----------------------------------------------------------------
    # 4) Decrypt the hotkey data and parse JSON
    # ----------------------------------------------------------------
    try:
        decrypted_bytes = cipher.decrypt(encrypted_data.encode("utf-8"))
    except InvalidToken:
        # This is the specific exception for Fernet decryption failure (wrong password/token)
        logger.error(
            f":cross_mark: [bold red]Decryption failed for hotkey '{hotkey_name}'. Invalid password or corrupted data.[/bold red]"
        )
        raise
    except Exception as e:
        # Catch other potential unexpected errors during decryption
        logger.error(
            f":rotating_light: [red]Unexpected error during decryption for '{hotkey_name}': {e}[/red]"
        )
        raise Exception(f"Unexpected decryption error for hotkey '{hotkey_name}'.")

    try:
        hotkey_data = json.loads(decrypted_bytes.decode("utf-8"))
    except json.JSONDecodeError as e:
        logger.error(
            f":warning: [red]Failed to parse decrypted JSON for hotkey '{hotkey_name}': {e}[/red]"
        )
        raise Exception(f"Failed to parse decrypted data for hotkey '{hotkey_name}'.")
    except UnicodeDecodeError as e:
        logger.error(
            f":warning: [red]Failed to decode decrypted bytes as UTF-8 for hotkey '{hotkey_name}': {e}[/red]"
        )
        raise Exception(f"Failed to decode decrypted data for hotkey '{hotkey_name}'.")

    # ----------------------------------------------------------------
    # 5) Extract the private key hex and create Aptos Account
    # ----------------------------------------------------------------
    private_key_hex = hotkey_data.get("private_key_hex")

    if not private_key_hex:
        logger.error(
            f":warning: [red]'private_key_hex' missing in decrypted data for '{hotkey_name}'[/red]"
        )
        raise KeyError(
            f"Missing 'private_key_hex' in decrypted data for hotkey '{hotkey_name}'."
        )

    # ----------------------------------------------------------------
    # 6) Convert to Aptos Account
    # ----------------------------------------------------------------
    try:
        # Convert the hex string to bytes and create an Aptos Account
        private_key_bytes = bytes.fromhex(private_key_hex)
        account = Account.load_key(private_key_bytes)
        
        # Basic validation - check if the address matches
        expected_address = hotkey_data.get("address")
        actual_address = account.address().hex()
        if not actual_address.startswith("0x"):
            actual_address = f"0x{actual_address}"
            
        if expected_address and expected_address != actual_address:
            logger.warning(
                f":warning: [yellow]Address mismatch for hotkey '{hotkey_name}'. "
                f"Stored: {expected_address}, Derived: {actual_address}[/yellow]"
            )
            
    except ValueError as e:
        logger.error(
            f":warning: [red]Invalid private key hex for hotkey '{hotkey_name}': {e}[/red]"
        )
        raise ValueError(
            f"Invalid private key format for hotkey '{hotkey_name}'."
        )
    except Exception as e:
        logger.error(
            f":rotating_light: [red]Failed to create Aptos Account for '{hotkey_name}': {e}[/red]"
        )
        raise Exception(f"Failed to create Aptos Account for hotkey '{hotkey_name}'.")

    logger.info(
        f":unlock: [green]Successfully decoded hotkey[/green] [bold blue]'{hotkey_name}'[/bold blue] "
        f"[dim]under coldkey[/dim] [bold cyan]'{coldkey_name}'[/bold cyan]."
    )

    return account
