# sdk/keymanager/hotkey_manager.py

import os
import json
import logging
from cryptography.fernet import Fernet
from pycardano import (
    Address,
    Network,
    ExtendedSigningKey  # used for stake & payment derivation
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class HotKeyManager:
    """
    Manages hotkeys by deriving two ExtendedSigningKeys (payment and stake),
    converting them to CBOR (hex format), and then encrypting that data 
    into 'hotkeys.json'. 
    """

    def __init__(
        self,
        coldkeys_dict: dict,  # {coldkey_name -> {"wallet": HDWallet, "cipher_suite": ..., "hotkeys": {...}}}
        base_dir="moderntensor",
        network=Network.TESTNET
    ):
        """
        Initializes the HotKeyManager.

        Args:
            coldkeys_dict (dict): A dictionary that holds data for existing coldkeys,
                                  including the associated HDWallet, a Fernet cipher_suite,
                                  and any existing hotkeys.
            base_dir (str): Base directory where coldkey folders (and their hotkeys.json) are stored.
            network (Network): Indicates which Cardano network to use. Default is TESTNET.
        """
        self.coldkeys = coldkeys_dict
        self.base_dir = base_dir
        self.network = network or Network.TESTNET

    def generate_hotkey(self, coldkey_name: str, hotkey_name: str):
        """
        Creates a new hotkey by:
          1) Deriving payment_xsk & stake_xsk from the coldkey's HDWallet using child paths.
             - Then converting them to CBOR (hex) for storage.
          2) Generating an address from payment and stake verification keys.
          3) Encrypting and writing the hotkey data (CBOR hex) into 'hotkeys.json'.
        
        Steps in detail:
          - Uses the next available index (based on how many hotkeys exist) to derive paths.
          - Derives child keys for payment (m/1852'/1815'/0'/0/idx) and stake (m/1852'/1815'/0'/2/idx).
          - Constructs an Address object using payment and stake verification keys.
          - Stores the extended signing keys in hex-encoded CBOR form, encrypts, and writes to disk.

        Args:
            coldkey_name (str): The name of the coldkey under which this hotkey will be generated.
            hotkey_name (str): A unique identifier for this hotkey.

        Raises:
            ValueError: If the given coldkey doesn't exist.
            Exception: If the specified hotkey already exists.

        Returns:
            str: The encrypted hotkey data (base64-encoded string).
        """
        import binascii

        # Check if coldkey_name exists in the manager
        if coldkey_name not in self.coldkeys:
            raise ValueError(f"Coldkey '{coldkey_name}' does not exist.")

        # Extract the HDWallet and cipher suite from the stored coldkeys data
        wallet_info = self.coldkeys[coldkey_name]
        hd_wallet = wallet_info["wallet"]        # HDWallet object
        cipher_suite: Fernet = wallet_info["cipher_suite"]
        hotkeys_dict = wallet_info["hotkeys"]    # Current hotkeys for this coldkey

        # If the hotkey already exists, raise an exception
        if hotkey_name in hotkeys_dict:
            raise Exception(f"Hotkey '{hotkey_name}' already exists for coldkey '{coldkey_name}'.")

        # Use the length of existing hotkeys as an index for derivation
        idx = len(hotkeys_dict)

        # 1) Derive the payment extended signing key using the standard Cardano derivation path
        payment_child = hd_wallet.derive_from_path(f"m/1852'/1815'/0'/0/{idx}")
        payment_xsk = ExtendedSigningKey.from_hdwallet(payment_child)
        payment_xvk = payment_xsk.to_verification_key()

        # 2) Derive the stake extended signing key
        stake_child = hd_wallet.derive_from_path(f"m/1852'/1815'/0'/2/{idx}")
        stake_xsk = ExtendedSigningKey.from_hdwallet(stake_child)
        stake_xvk = stake_xsk.to_verification_key()

        # 3) Construct an address from the payment part and the stake part
        hotkey_address = Address(
            payment_part=payment_xvk.hash(),
            staking_part=stake_xvk.hash(),
            network=self.network
        )

        # 4) Convert the extended signing keys to CBOR bytes, then to hex strings
        pay_cbor_hex = binascii.hexlify(payment_xsk.to_cbor()).decode("utf-8")
        stk_cbor_hex = binascii.hexlify(stake_xsk.to_cbor()).decode("utf-8")

        # Store these in a dictionary to be encrypted
        hotkey_data = {
            "name": hotkey_name,
            "address": str(hotkey_address),
            "payment_xsk_cbor_hex": pay_cbor_hex,
            "stake_xsk_cbor_hex": stk_cbor_hex
        }

        # Encrypt the hotkey JSON using the Fernet cipher suite
        enc_bytes = cipher_suite.encrypt(json.dumps(hotkey_data).encode("utf-8"))
        encrypted_hotkey = enc_bytes.decode("utf-8")

        # Update the local dictionary for hotkeys
        hotkeys_dict[hotkey_name] = {
            "address": str(hotkey_address),
            "encrypted_data": encrypted_hotkey
        }

        # Write the updated hotkeys dictionary to 'hotkeys.json'
        coldkey_dir = os.path.join(self.base_dir, coldkey_name)
        os.makedirs(coldkey_dir, exist_ok=True)
        hotkey_path = os.path.join(coldkey_dir, "hotkeys.json")
        with open(hotkey_path, "w") as f:
            json.dump({"hotkeys": hotkeys_dict}, f, indent=2)

        logger.info(f"[generate_hotkey] => {hotkey_name} => address={hotkey_address}")
        return encrypted_hotkey

    def import_hotkey(
        self,
        coldkey_name: str,
        encrypted_hotkey: str,
        hotkey_name: str,
        overwrite=False
    ):
        """
        Imports a hotkey by decrypting the provided encrypted hotkey data and storing 
        the resulting address info into 'hotkeys.json'.

        Steps in detail:
          - Decrypts the hotkey JSON (which includes payment_xsk_cbor_hex and stake_xsk_cbor_hex).
          - Reconstructs the extended signing keys from the hex-encoded CBOR.
          - (Optionally) prompts the user if a hotkey with the same name already exists 
            and overwrite is disabled.
          - Writes the final data to 'hotkeys.json'.

        Args:
            coldkey_name (str): The name of the coldkey to which this hotkey will be imported.
            encrypted_hotkey (str): The encrypted hotkey data (base64-encoded, Fernet).
            hotkey_name (str): The name under which this hotkey will be stored.
            overwrite (bool): If True, overwrite an existing hotkey without prompting.

        Raises:
            ValueError: If the given coldkey doesn't exist.

        Returns:
            None: Writes hotkey data to disk. Logs completion status.
        """
        import binascii

        # Verify that the specified coldkey exists
        if coldkey_name not in self.coldkeys:
            raise ValueError(f"[import_hotkey] Cold Key '{coldkey_name}' does not exist.")

        # Fetch cipher suite and hotkeys dictionary
        wallet_info = self.coldkeys[coldkey_name]
        cipher_suite: Fernet = wallet_info["cipher_suite"]
        hotkeys_dict = wallet_info["hotkeys"]

        # Check if hotkey already exists
        if hotkey_name in hotkeys_dict and not overwrite:
            resp = input(f"Hot Key '{hotkey_name}' exists. Overwrite? (yes/no): ").strip().lower()
            if resp not in ("yes", "y"):
                logging.warning("[import_hotkey] User canceled overwrite => import aborted.")
                return
            logging.warning(f"[import_hotkey] Overwriting '{hotkey_name}'.")

        # Decrypt the provided hotkey data
        dec_bytes = cipher_suite.decrypt(encrypted_hotkey.encode("utf-8"))
        hotkey_data = json.loads(dec_bytes.decode("utf-8"))
        hotkey_data["name"] = hotkey_name

        pay_cbor_hex = hotkey_data["payment_xsk_cbor_hex"]
        stk_cbor_hex = hotkey_data["stake_xsk_cbor_hex"]

        # Convert hex-encoded CBOR back to ExtendedSigningKey objects
        from pycardano import ExtendedSigningKey
        payment_xsk = ExtendedSigningKey.from_cbor(binascii.unhexlify(pay_cbor_hex))
        stake_xsk = ExtendedSigningKey.from_cbor(binascii.unhexlify(stk_cbor_hex))

        # Reconstruct the address from verification keys, if needed
        pay_xvk = payment_xsk.to_verification_key()
        stake_xvk = stake_xsk.to_verification_key()
        final_address = hotkey_data["address"]

        # Update the in-memory hotkeys dictionary
        hotkeys_dict[hotkey_name] = {
            "address": final_address,
            "encrypted_data": encrypted_hotkey
        }

        # Write the updated hotkeys dictionary back to 'hotkeys.json'
        coldkey_dir = os.path.join(self.base_dir, coldkey_name)
        hotkey_path = os.path.join(coldkey_dir, "hotkeys.json")
        with open(hotkey_path, "w") as f:
            json.dump({"hotkeys": hotkeys_dict}, f, indent=2)

        logger.info(f"[import_hotkey] => {hotkey_name} => address={final_address}")
