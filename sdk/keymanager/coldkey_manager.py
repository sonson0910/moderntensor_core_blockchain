# keymanager/coldkey_manager.py
import os
import json
import logging
from bip_utils import Bip39MnemonicGenerator, Bip39Languages
from pycardano import HDWallet
from .encryption_utils import get_cipher_suite

logging.basicConfig(level=logging.INFO)


class ColdKeyManager:
    def __init__(self, base_dir="moderntensor"):
        """
        :param base_dir: Base directory for storing mnemonic files, hotkeys.json, etc.
        """
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        # Store {coldkey_name: {"wallet": hdwallet, "cipher_suite": Fernet, "hotkeys": {...}}}
        self.coldkeys = {}

    def create_coldkey(self, name: str, password: str, words_num=24):
        """
        Create a Cold Key (24-word mnemonic), encrypted using password + salt.
        Initialize an empty hotkeys.json file to store the list of hotkeys.
        """
        coldkey_dir = os.path.join(self.base_dir, name)
        os.makedirs(coldkey_dir, exist_ok=True)

        cipher_suite = get_cipher_suite(password, coldkey_dir)

        # Generate mnemonic
        mnemonic = str(
            Bip39MnemonicGenerator(lang=Bip39Languages.ENGLISH).FromWordsNumber(
                words_num
            )
        )
        logging.warning(
            f"[create_coldkey] Mnemonic for Cold Key '{name}' has been created. Please store it securely."
        )

        # Save mnemonic.enc
        enc_path = os.path.join(coldkey_dir, "mnemonic.enc")
        with open(enc_path, "wb") as f:
            f.write(cipher_suite.encrypt(mnemonic.encode("utf-8")))

        # Create HDWallet
        hdwallet = HDWallet.from_mnemonic(mnemonic)

        # Create an empty hotkeys.json file
        hotkeys_path = os.path.join(coldkey_dir, "hotkeys.json")
        if not os.path.exists(hotkeys_path):
            with open(hotkeys_path, "w") as f:
                json.dump({"hotkeys": {}}, f)

        # Store in self.coldkeys
        self.coldkeys[name] = {
            "wallet": hdwallet,
            "cipher_suite": cipher_suite,
            "hotkeys": {},
        }
        logging.info(
            f"[create_coldkey] Cold Key '{name}' has been successfully created."
        )

    def load_coldkey(self, name: str, password: str):
        """
        Read mnemonic.enc, salt.bin, hotkeys.json. Decrypt mnemonic to create HDWallet.
        Store in self.coldkeys for use.
        """
        coldkey_dir = os.path.join(self.base_dir, name)
        mnemonic_path = os.path.join(coldkey_dir, "mnemonic.enc")
        hotkey_path = os.path.join(coldkey_dir, "hotkeys.json")

        if not os.path.exists(mnemonic_path):
            raise FileNotFoundError(
                f"[load_coldkey] Cannot find mnemonic.enc for Cold Key '{name}'."
            )

        # Create cipher_suite
        cipher_suite = get_cipher_suite(password, coldkey_dir)

        # Decrypt mnemonic
        with open(mnemonic_path, "rb") as f:
            encrypted_mnemonic = f.read()
        mnemonic = cipher_suite.decrypt(encrypted_mnemonic).decode("utf-8")
        hdwallet = HDWallet.from_mnemonic(mnemonic)

        # Read hotkeys.json
        with open(hotkey_path, "r") as f:
            hotkeys_data = json.load(f)
        if "hotkeys" not in hotkeys_data:
            hotkeys_data["hotkeys"] = {}

        # Store in self.coldkeys
        self.coldkeys[name] = {
            "wallet": hdwallet,
            "cipher_suite": cipher_suite,
            "hotkeys": hotkeys_data["hotkeys"],
        }
        logging.info(f"[load_coldkey] Cold Key '{name}' has been successfully loaded.")
