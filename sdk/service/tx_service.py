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
    VerificationKeyWitness,
    Network,
    BlockFrostChainContext,
    TransactionBuilder,
    ScriptHash,
    AssetName
)

from sdk.keymanager.encryption_utils import get_or_create_salt, generate_encryption_key
from sdk.keymanager.decryption_utils import decode_hotkey_skey
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


def send_token(
    chain_context: BlockFrostChainContext,
    base_dir: str,
    coldkey_name: str,
    hotkey_name: str,
    password: str,
    to_address_str: str,
    policy_id_hex: str,
    asset_name: str,
    token_amount: int,
    fee: int = 200_000,
    network: Network = Network.TESTNET
) -> str:
    """
    Gửi 1 phần token (policy_id, asset_name, token_amount) và 2 ADA (demo) cho địa chỉ đích,
    còn lại token + ADA => output change => from_address => tránh ValueNotConservedUTxO.
    """
    # 1) Decode hotkey => (payment_xsk, stake_xsk)
    payment_xsk, stake_xsk = decode_hotkey_skey(base_dir, coldkey_name, hotkey_name, password)
    if not payment_xsk:
        raise ValueError(f"Decode Payment ExtendedSigningKey fail for hotkey {hotkey_name}")

    pay_xvk = payment_xsk.to_verification_key()
    stake_xvk = stake_xsk.to_verification_key() if stake_xsk else None

    from_address = Address(
        payment_part=pay_xvk.hash(),
        staking_part=stake_xvk.hash() if stake_xvk else None,
        network=network
    )
    logger.info(f"[send_token] from_address={from_address}")

    utxos = chain_context.utxos(from_address)
    if not utxos:
        raise ValueError(f"No UTxOs found at {from_address}")

    # 2) Gom inputs => tính tổng coin, tổng token
    tx_inputs = []
    total_coin_input = 0
    # Lưu trữ multi_asset input => {policy_id -> {asset_name -> quantity}}
    from pycardano import MultiAsset, Asset

    input_multiasset = MultiAsset()

    for utxo in utxos:
        tx_inputs.append(utxo.input)
        val = utxo.output.amount
        # Cộng coin
        total_coin_input += val.coin
        # Cộng multi-asset
        if val.multi_asset:
            for pid, assets_map in val.multi_asset.items():
                # pid là ScriptHash
                if pid not in input_multiasset:
                    input_multiasset[pid] = Asset()
                for aname, qty in assets_map.items():
                    # aname là AssetName
                    if aname not in input_multiasset[pid]:
                        input_multiasset[pid][aname] = 0
                    input_multiasset[pid][aname] += qty


    # 3) Kiểm tra token trong input_multiasset
    pid_bytes = bytes.fromhex(policy_id_hex)
    aname_bytes = asset_name.encode("utf-8")
    # print(utxos)

    policy_obj = ScriptHash.from_primitive(bytes.fromhex(policy_id_hex))
    # hoặc ScriptHash(hex=policy_id_hex) tuỳ PyCardano version

    asset_obj = AssetName(asset_name.encode("utf-8"))
    # => asset_obj = AssetName(b"MIT")

    # Tổng số token (policy_id, asset_name) trong inputs
    total_token_input = input_multiasset.get(policy_obj, Asset()).get(asset_obj, 0)

    if total_token_input < token_amount:
        raise ValueError(f"Not enough {asset_name} token in input to send {token_amount}. Found {total_token_input}.")

    # 4) Xác định ta sẽ “gắn” 2 ADA trong output #1 => multi-asset
    #    => Tối thiểu 1.4-2 ADA => 
    out1_coin = 2_000_000  # 2 ADA
    if total_coin_input < fee + out1_coin:
        raise ValueError("Not enough coin for fee + out1_coin")

    # 5) Tạo output #1 => to_address => chứa token_amount + out1_coin
    #    => Tạo structure => [coin, {pid: {aname: token_amount}}]
    ma_value_out1 = [
        out1_coin,
        {
            pid_bytes: {
                aname_bytes: token_amount
            }
        }
    ]
    from pycardano import Value, TransactionOutput, TransactionBody, Transaction, TransactionWitnessSet, VerificationKeyWitness
    val_out1 = Value.from_primitive(ma_value_out1)
    out_token = TransactionOutput(Address.from_primitive(to_address_str), val_out1)

    # 6) Tính coin change => total_coin_input - fee - out1_coin
    coin_change = total_coin_input - fee - out1_coin
    if coin_change < 0:
        raise ValueError("Not enough coin for fee + out1_coin => negative change")

    # 7) Tính token change => 
    #    Tức total_token_input - token_amount => leftover
    token_change = total_token_input - token_amount

    # => copy input_multiasset => subtract token_amount
    out_change_multiasset = MultiAsset()
    # Sao chép multiasset
    for pid, assets_map in input_multiasset.items():
        out_change_multiasset[pid] = Asset()
        for aname, qty in assets_map.items():
            out_change_multiasset[pid][aname] = qty

    out_change_multiasset[policy_obj][asset_obj] -= token_amount
    if out_change_multiasset[policy_obj][asset_obj] == 0:
        del out_change_multiasset[policy_obj][asset_obj]
    if len(out_change_multiasset[policy_obj]) == 0:
        del out_change_multiasset[policy_obj]


    # 8) output #2 => from_address => coin_change + out_change_multiasset
    val_change = Value(coin_change, out_change_multiasset)  # coin + leftover multiasset
    out_change = TransactionOutput(from_address, val_change)

    # 9) Tạo TransactionBody => 2 outputs
    tx_body = TransactionBody(
        inputs=tx_inputs,
        outputs=[out_token, out_change],
        fee=fee
    )

    # 10) Ký
    signature = payment_xsk.sign(tx_body.hash())
    vk_witness = VerificationKeyWitness(pay_xvk, signature)
    witness_set = TransactionWitnessSet(vkey_witnesses=[vk_witness])

    # 11) Tạo Transaction => submit
    signed_tx = Transaction(tx_body, witness_set)
    tx_id = chain_context.submit_tx(signed_tx.to_cbor())

    logger.info(f"[send_token] => TX ID: {tx_id}")
    return tx_id

