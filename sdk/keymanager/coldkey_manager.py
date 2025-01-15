# keymanager/coldkey_manager.py

import os
import json
import logging
from bip_utils import Bip39MnemonicGenerator, Bip39Languages
from cryptography.fernet import InvalidToken
from pycardano import HDWallet
from .encryption_utils import get_cipher_suite

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ColdKeyManager:
    def __init__(self, base_dir="moderntensor"):
        """
        Initialize the ColdKeyManager class.
        
        :param base_dir: Base directory (default: 'moderntensor') where 
                         mnemonic files, hotkeys.json, etc. will be stored.
        """
        # Set the base directory
        self.base_dir = base_dir
        # Create the base directory if it doesn't exist
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Dictionary to store coldkeys that are loaded or newly created.
        # Structure: 
        # {
        #   "coldkey_name": {
        #       "wallet": HDWallet_object, 
        #       "cipher_suite": Fernet_object,
        #       "hotkeys": { ... }
        #   },
        #   ...
        # }
        self.coldkeys = {}

    def create_coldkey(self, name: str, password: str, words_num=24):
        """
        Create a new Cold Key and generate its mnemonic (commonly 24 words).
        
        Args:
            name (str): Unique name for the coldkey.
            password (str): Password used to encrypt the mnemonic.
            words_num (int): Number of words in the mnemonic (commonly 24).

        Raises:
            Exception: If the coldkey name already exists in memory 
                       (self.coldkeys) or if the directory already exists.
        
        Returns:
            None
        """
        # 1) Check if the coldkey name already exists in memory
        if name in self.coldkeys:
            raise Exception(f"Coldkey '{name}' already exists in memory.")
        
        # 2) Create the path for the coldkey (directory name is the same as the coldkey name)
        coldkey_dir = os.path.join(self.base_dir, name)
        # If the directory already exists, raise an exception to prevent overwriting
        if os.path.exists(coldkey_dir):
            raise Exception(f"Coldkey folder '{coldkey_dir}' already exists.")
        
        # Create the coldkey directory
        os.makedirs(coldkey_dir, exist_ok=True)

        # Create the cipher_suite (Fernet) using the user-provided password
        cipher_suite = get_cipher_suite(password, coldkey_dir)

        # Generate the mnemonic (with 'words_num' words, default language is English)
        mnemonic = str(
            Bip39MnemonicGenerator(lang=Bip39Languages.ENGLISH).FromWordsNumber(words_num)
        )
        logger.warning(
            f"[create_coldkey] Mnemonic for Cold Key '{name}' has been created. "
            "Please store it securely."
        )

        # Encrypt and save the mnemonic to the mnemonic.enc file
        enc_path = os.path.join(coldkey_dir, "mnemonic.enc")
        with open(enc_path, "wb") as f:
            # Encrypt the mnemonic string (converted to bytes) with the cipher_suite
            f.write(cipher_suite.encrypt(mnemonic.encode("utf-8")))

        # Create an HDWallet from the mnemonic (used for generating addresses, keys, etc.)
        hdwallet = HDWallet.from_mnemonic(mnemonic)

        # Create an empty hotkeys.json file (if it does not already exist) to store hotkeys
        hotkeys_path = os.path.join(coldkey_dir, "hotkeys.json")
        if not os.path.exists(hotkeys_path):
            with open(hotkeys_path, "w") as f:
                json.dump({"hotkeys": {}}, f)

        # Store the newly created coldkey info in self.coldkeys
        self.coldkeys[name] = {
            "wallet": hdwallet,
            "cipher_suite": cipher_suite,
            "hotkeys": {},
        }
        logger.info(
            f"[create_coldkey] Cold Key '{name}' has been successfully created."
        )

    def load_coldkey(self, name: str, password: str):
        """
        Read mnemonic.enc, salt.bin, and hotkeys.json. Decrypt the mnemonic 
        to create an HDWallet and store it in self.coldkeys.

        Args:
            name (str): The name of the coldkey to be loaded.
            password (str): Password used to decrypt the mnemonic.

        Raises:
            FileNotFoundError: If mnemonic.enc does not exist.
            Exception: If the password is invalid (when decrypting mnemonic).
        
        Returns:
            None
        """
        # Construct the coldkey directory path based on 'name'
        coldkey_dir = os.path.join(self.base_dir, name)
        # Path to the encrypted mnemonic
        mnemonic_path = os.path.join(coldkey_dir, "mnemonic.enc")
        # Path to the hotkeys.json file
        hotkey_path = os.path.join(coldkey_dir, "hotkeys.json")

        # Check if mnemonic.enc exists
        if not os.path.exists(mnemonic_path):
            raise FileNotFoundError(
                f"mnemonic.enc not found for Cold Key '{name}'."
            )

        # Create cipher_suite for decrypting the mnemonic (using the user's password)
        cipher_suite = get_cipher_suite(password, coldkey_dir)

        # Read the encrypted mnemonic from file
        with open(mnemonic_path, "rb") as f:
            encrypted_mnemonic = f.read()

        # Decrypt the mnemonic
        try:
            mnemonic = cipher_suite.decrypt(encrypted_mnemonic).decode("utf-8")
        except InvalidToken:
            # If decryption fails => password is incorrect
            raise Exception("Invalid password: failed to decrypt mnemonic.")

        # Create an HDWallet from the mnemonic (same process as in create_coldkey)
        hdwallet = HDWallet.from_mnemonic(mnemonic)

        # Read the hotkeys.json file to retrieve the list of hotkeys
        with open(hotkey_path, "r") as f:
            hotkeys_data = json.load(f)
        
        # Ensure the "hotkeys" field exists in the JSON. If not, initialize it.
        if "hotkeys" not in hotkeys_data:
            hotkeys_data["hotkeys"] = {}

        # Store the coldkey information (hdwallet, cipher_suite, hotkeys) in self.coldkeys
        self.coldkeys[name] = {
            "wallet": hdwallet,
            "cipher_suite": cipher_suite,
            "hotkeys": hotkeys_data["hotkeys"],
        }
        logger.info(f"[load_coldkey] Cold Key '{name}' has been successfully loaded.")
