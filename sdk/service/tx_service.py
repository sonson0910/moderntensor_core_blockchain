# sdk/service/tx_service.py

import logging
import binascii
from typing import Optional
from pycardano import (
    Address,
    TransactionInput,
    TransactionOutput,
    TransactionBody,
    Transaction,
    TransactionWitnessSet,
    Value,
    ExtendedSigningKey,         # Thay đổi: ta dùng ExtendedSigningKey
    PaymentVerificationKey,
    VerificationKeyWitness,
    Network,
    BlockFrostChainContext,
)

from sdk.keymanager.encryption_utils import get_or_create_salt, generate_encryption_key
from cryptography.fernet import Fernet
import json
import os

logger = logging.getLogger(__name__)

def send_ada(
    chain_context,
    payment_xsk,     # ExtendedSigningKey (or PaymentSigningKey)
    stake_xsk=None,  # ExtendedSigningKey stake (optional) - if needed
    to_address_str: str = "",
    lovelace_amount: int = 1_000_000,
    network: Network = Network.TESTNET,
    change_address_str: Optional[str] = None
) -> str:
    """
    Gửi ADA:
      - Tạo `from_address` = Address(pay_xvk.hash(), stake_xvk.hash() nếu có).
      - add_input_address(from_address)
      - build_and_sign(signing_keys=[payment_xsk], change_address=from_address)
    """
    from pycardano import Address, TransactionBuilder, TransactionOutput

    # 1) Tạo from_address
    pay_xvk = payment_xsk.to_verification_key()
    if stake_xsk is not None:
        stk_xvk = stake_xsk.to_verification_key()
        from_address = Address(pay_xvk.hash(), stk_xvk.hash(), network=network)
    else:
        from_address = Address(pay_xvk.hash(), network=network)

    # 2) to_address
    to_address = Address.from_primitive(to_address_str) if to_address_str else from_address
    change_address = Address.from_primitive(change_address_str) if change_address_str else from_address

    # 3) Tạo builder, add inputs
    builder = TransactionBuilder(chain_context)
    builder.add_input_address(from_address)

    # 4) Add output => send ADA
    builder.add_output(TransactionOutput(to_address, lovelace_amount))

    # 5) Create signed_tx
    signed_tx = builder.build_and_sign(
        signing_keys=[payment_xsk],  # Sign = payment_xsk
        change_address=change_address
    )

    # 6) submit
    tx_id = chain_context.submit_tx(signed_tx.to_cbor())
    logger.info(f"[send_ada] => TX ID: {tx_id}")
    return tx_id


def send_token_lowlevel_hotkey(
    chain_context: BlockFrostChainContext,
    base_dir: str,
    coldkey_name: str,
    hotkey_name: str,
    password: str,
    to_address_str: str,
    policy_id_hex: str,
    asset_name: str,
    token_amount: int,
    lovelace_amount: int = 2_000_000,  # Số ADA kèm theo output
    fee: int = 200_000,               # Phí fix cứng - DEMO
    network: Network = Network.TESTNET
) -> str:
    """
    Tạo 1 transaction “low-level style”, dùng hotkey (ExtendedSigningKey),
    để chuyển 1 token (policy_id_hex + asset_name) + `lovelace_amount` 
    từ ví hotkey => `to_address_str`, với fee cố định = `fee`.
    
    - Giải mã (payment_xsk, stake_xsk) => Tạo from_address (có stake part).
    - Gom UTxO => add as inputs (demo).
    - Tạo 1 output = multi-asset => (lovelace_amount + token_amount).
    - build TransactionBody => Ký = payment_xsk.
    - Submit => trả tx_id.

    Args:
      chain_context (BlockFrostChainContext): Kết nối Blockfrost.
      base_dir (str): Thư mục chứa coldkey_name => hotkeys.json
      coldkey_name (str): Tên coldkey
      hotkey_name (str): Tên hotkey
      password (str): Password để giải mã hotkey
      to_address_str (str): Địa chỉ bech32 người nhận
      policy_id_hex (str): policy_id (56 hex) 
      asset_name (str): Tên token ASCII
      token_amount (int): Số token cần gửi
      lovelace_amount (int): Số ADA kèm theo
      fee (int): phí (demo)
      network (Network): TESTNET / MAINNET

    Returns:
      str: Transaction ID sau khi submit
    """

    # 1) Giải mã (payment_xsk, stake_xsk) => ExtendedSigningKey
    payment_xsk, stake_xsk = _decode_hotkey_as_extended_keys(base_dir, coldkey_name, hotkey_name, password)
    if not payment_xsk:
        raise ValueError(f"Could not decode Payment ExtendedSigningKey for hotkey '{hotkey_name}'.")

    # 2) Tạo from_address = Address(payment, stake, network)
    pay_xvk = payment_xsk.to_verification_key()
    stk_xvk = stake_xsk.to_verification_key() if stake_xsk else None
    from_address = Address(
        payment_part=pay_xvk.hash(),
        staking_part=stk_xvk.hash() if stk_xvk else None,
        network=network
    )

    logger.info(f"[send_token_lowlevel_hotkey] from_address = {from_address}")

    # 3) Lấy UTxO => Tạo input
    utxos = chain_context.utxos(from_address)
    if not utxos:
        raise ValueError(f"No UTxOs found for address: {from_address}")

    tx_inputs = []
    total_lovelace_input = 0

    # Demo: add ALL utxos
    for utxo in utxos:
        tx_inputs.append(utxo.input)
        total_lovelace_input += utxo.output.amount.coin

    if total_lovelace_input < (fee + lovelace_amount):
        raise ValueError("Not enough ADA to pay fee + output. total_lovelace_input < needed")

    # 4) Tạo Output => (lovelace_amount + token)
    to_addr = Address.from_primitive(to_address_str)

    policy_id = bytes.fromhex(policy_id_hex)  
    multi_asset_value = [
        lovelace_amount,
        {
            policy_id: {
                asset_name.encode("utf-8"): token_amount
            }
        }
    ]
    ma_value = Value.from_primitive(multi_asset_value)
    tx_output = TransactionOutput(to_addr, ma_value)

    # 5) Tạo TransactionBody (chưa set TTL, etc.)
    tx_body = TransactionBody(
        inputs=tx_inputs,
        outputs=[tx_output],
        fee=fee,
    )

    # 6) Ký => Payment ExtendedSigningKey => sign tx_body.hash()
    # Thường stake key không cần ký nếu chỉ send token
    signature = payment_xsk.sign(tx_body.hash())
    from_vkey = pay_xvk  # PaymentVerificationKey

    # 7) witness
    vk_witness = VerificationKeyWitness(from_vkey, signature)
    witness_set = TransactionWitnessSet(vkey_witnesses=[vk_witness])

    # 8) Tạo Transaction => sign
    signed_tx = Transaction(body=tx_body, witness_set=witness_set)

    # 9) Submit
    tx_id = chain_context.submit_tx(signed_tx.to_cbor())
    logger.info(f"[send_token_lowlevel_hotkey] => TX ID: {tx_id}")
    return tx_id


def _decode_hotkey_as_extended_keys(
    base_dir: str,
    coldkey_name: str,
    hotkey_name: str,
    password: str
) -> tuple[Optional[ExtendedSigningKey], Optional[ExtendedSigningKey]]:
    """
    Ví dụ decode (payment_xsk, stake_xsk) => ExtendedSigningKey, 
    từ hotkeys.json, tuỳ logic generate_hotkey cũ.

    Returns:
      (payment_xsk, stake_xsk) as ExtendedSigningKey or None
    """
    coldkey_dir = os.path.join(base_dir, coldkey_name)
    salt = get_or_create_salt(coldkey_dir)
    enc_key = generate_encryption_key(password, salt)
    cipher_suite = Fernet(enc_key)

    hotkeys_json_path = os.path.join(coldkey_dir, "hotkeys.json")
    if not os.path.isfile(hotkeys_json_path):
        return (None, None)

    with open(hotkeys_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if hotkey_name not in data["hotkeys"]:
        return (None, None)

    enc_data = data["hotkeys"][hotkey_name]["encrypted_data"]
    dec = cipher_suite.decrypt(enc_data.encode("utf-8"))
    hotkey_data = json.loads(dec.decode("utf-8"))
    # => { "payment_xsk_cbor_hex":..., "stake_xsk_cbor_hex":..., ...}

    pay_hex = hotkey_data.get("payment_xsk_cbor_hex")
    stk_hex = hotkey_data.get("stake_xsk_cbor_hex")

    payment_xsk = None
    stake_xsk = None

    if pay_hex:
        pay_bytes = binascii.unhexlify(pay_hex)
        payment_xsk = ExtendedSigningKey.from_cbor(pay_bytes)

    if stk_hex:
        stk_bytes = binascii.unhexlify(stk_hex)
        stake_xsk = ExtendedSigningKey.from_cbor(stk_bytes)

    return (payment_xsk, stake_xsk)