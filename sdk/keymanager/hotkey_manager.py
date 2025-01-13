# sdk/keymanager/hotkey_manager.py

import os
import json
import logging
from cryptography.fernet import Fernet
from pycardano import (
    Address,
    Network,
    ExtendedSigningKey  # stake & payment
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class HotKeyManager:
    """
    Lưu 2 ExtendedSigningKey (payment, stake) => cbor => mã hoá => hotkeys.json.
    """

    def __init__(
        self,
        coldkeys_dict: dict,  # { coldkey_name -> { "wallet": HDWallet, "cipher_suite":..., "hotkeys": {...} } }
        base_dir="moderntensor",
        network=Network.TESTNET
    ):
        self.coldkeys = coldkeys_dict
        self.base_dir = base_dir
        self.network = network or Network.TESTNET

    def generate_hotkey(self, coldkey_name: str, hotkey_name: str):
        """
        1) Tạo payment_xsk & stake_xsk => .to_cbor() => hex => JSON => mã hoá => 'encrypted_data'
        2) Address = Address(payment_xvk.hash(), stake_xvk.hash(), network=...)
        3) Ghi hotkeys.json => return encrypted_hotkey
        """
        import binascii

        if coldkey_name not in self.coldkeys:
            raise ValueError(f"Coldkey '{coldkey_name}' does not exist.")

        wallet_info = self.coldkeys[coldkey_name]
        hd_wallet = wallet_info["wallet"]  # HDWallet
        cipher_suite: Fernet = wallet_info["cipher_suite"]
        hotkeys_dict = wallet_info["hotkeys"]

        if hotkey_name in hotkeys_dict:
            raise Exception(f"Hotkey '{hotkey_name}' already exists for coldkey '{coldkey_name}'.")

        idx = len(hotkeys_dict)

        # 1) Dẫn xuất child => ExtendedSigningKey cho payment
        payment_child = hd_wallet.derive_from_path(f"m/1852'/1815'/0'/0/{idx}")
        payment_xsk = ExtendedSigningKey.from_hdwallet(payment_child)
        payment_xvk = payment_xsk.to_verification_key()

        # 2) Dẫn xuất child => ExtendedSigningKey cho stake
        stake_child = hd_wallet.derive_from_path(f"m/1852'/1815'/0'/2/{idx}")
        stake_xsk = ExtendedSigningKey.from_hdwallet(stake_child)
        stake_xvk = stake_xsk.to_verification_key()

        # 3) Địa chỉ => có payment_part & staking_part
        hotkey_address = Address(
            payment_part=payment_xvk.hash(),
            staking_part=stake_xvk.hash(),
            network=self.network
        )

        # 4) Lưu cbor => hex => JSON => mã hoá
        pay_cbor_hex = binascii.hexlify(payment_xsk.to_cbor()).decode("utf-8")
        stk_cbor_hex = binascii.hexlify(stake_xsk.to_cbor()).decode("utf-8")

        hotkey_data = {
            "name": hotkey_name,
            "address": str(hotkey_address),
            "payment_xsk_cbor_hex": pay_cbor_hex,
            "stake_xsk_cbor_hex": stk_cbor_hex
        }

        enc_bytes = cipher_suite.encrypt(json.dumps(hotkey_data).encode("utf-8"))
        encrypted_hotkey = enc_bytes.decode("utf-8")

        hotkeys_dict[hotkey_name] = {
            "address": str(hotkey_address),
            "encrypted_data": encrypted_hotkey
        }

        # Ghi file
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
        Giải mã => parse => payment_xsk, stake_xsk => address => ghi hotkeys.json
        """
        import binascii

        if coldkey_name not in self.coldkeys:
            raise ValueError(f"[import_hotkey] Cold Key '{coldkey_name}' does not exist.")

        wallet_info = self.coldkeys[coldkey_name]
        cipher_suite: Fernet = wallet_info["cipher_suite"]
        hotkeys_dict = wallet_info["hotkeys"]

        if hotkey_name in hotkeys_dict and not overwrite:
            resp = input(f"Hot Key '{hotkey_name}' exists. Overwrite? (yes/no): ").strip().lower()
            if resp not in ("yes","y"):
                logging.warning("[import_hotkey] User canceled overwrite => import aborted.")
                return
            logging.warning(f"[import_hotkey] Overwriting '{hotkey_name}'.")

        dec_bytes = cipher_suite.decrypt(encrypted_hotkey.encode("utf-8"))
        hotkey_data = json.loads(dec_bytes.decode("utf-8"))
        hotkey_data["name"] = hotkey_name

        pay_cbor_hex = hotkey_data["payment_xsk_cbor_hex"]
        stk_cbor_hex = hotkey_data["stake_xsk_cbor_hex"]

        from pycardano import ExtendedSigningKey
        payment_xsk = ExtendedSigningKey.from_cbor(binascii.unhexlify(pay_cbor_hex))
        stake_xsk = ExtendedSigningKey.from_cbor(binascii.unhexlify(stk_cbor_hex))

        pay_xvk = payment_xsk.to_verification_key()
        stake_xvk = stake_xsk.to_verification_key()
        final_address = hotkey_data["address"]

        hotkeys_dict[hotkey_name] = {
            "address": final_address,
            "encrypted_data": encrypted_hotkey
        }

        coldkey_dir = os.path.join(self.base_dir, coldkey_name)
        hotkey_path = os.path.join(coldkey_dir, "hotkeys.json")
        with open(hotkey_path, "w") as f:
            json.dump({"hotkeys": hotkeys_dict}, f, indent=2)

        logger.info(f"[import_hotkey] => {hotkey_name} => address={final_address}")
