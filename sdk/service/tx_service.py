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
    AssetName,
)

from sdk.keymanager.encryption_utils import get_or_create_salt, generate_encryption_key
from sdk.keymanager.decryption_utils import decode_hotkey_skey
from cryptography.fernet import Fernet
import json
import os

logger = logging.getLogger(__name__)


def send_ada(
    chain_context,
    payment_xsk,     # ExtendedSigningKey (payment key)
    stake_xsk=None,  # ExtendedSigningKey (stake key) - optional
    to_address_str: str = "",
    lovelace_amount: int = 1_000_000,
    network: Network = Network.TESTNET,
    change_address_str: Optional[str] = None
) -> str:
    """
    Sends ADA (lovelace) to a specified address using the given signing key(s).

    Steps:
      1) Create the source address (from_address) from payment_xsk 
         (and stake_xsk if provided).
      2) Build a transaction builder, adding the from_address as an input.
      3) Create a transaction output that sends the specified lovelace_amount 
         to the to_address.
      4) Sign the transaction with payment_xsk (and optionally stake_xsk if needed).
      5) Submit the transaction to the network and return the TX ID.

    Args:
        chain_context: The chain context (e.g., BlockFrostChainContext) used to build/submit tx.
        payment_xsk: An ExtendedSigningKey for payment. This key is required to sign inputs.
        stake_xsk: Optional ExtendedSigningKey for stake. If provided, the source address will 
                   include the stake verification key hash.
        to_address_str (str): The address to send ADA to (in bech32 or base58 format).
        lovelace_amount (int): The amount of ADA to send, in lovelace (1_000_000 lovelace = 1 ADA).
        network (Network): The Cardano network, default is TESTNET.
        change_address_str (str): If provided, any leftover change from the transaction 
                                  will be sent here. Otherwise, it defaults to from_address.

    Returns:
        str: The transaction ID (TX ID) as returned by the chain context upon successful submission.
    """

    # 1) Create the source (from_address) from the payment verification key and optional stake key
    pay_xvk = payment_xsk.to_verification_key()
    if stake_xsk is not None:
        stk_xvk = stake_xsk.to_verification_key()
        from_address = Address(pay_xvk.hash(), stk_xvk.hash(), network=network)
    else:
        from_address = Address(pay_xvk.hash(), network=network)

    # If no to_address_str is provided, we default to sending funds back to ourselves
    to_address = Address.from_primitive(to_address_str) if to_address_str else from_address
    # If no change address is specified, default change to source address
    change_address = Address.from_primitive(change_address_str) if change_address_str else from_address

    # 2) Create a TransactionBuilder and add inputs from the source address
    builder = TransactionBuilder(chain_context)
    builder.add_input_address(from_address)

    # 3) Create an output to send the lovelace_amount to the to_address
    builder.add_output(TransactionOutput(to_address, lovelace_amount))

    # 4) Build and sign the transaction (sign only with the payment_xsk)
    signed_tx = builder.build_and_sign(
        signing_keys=[payment_xsk],  
        change_address=change_address
    )

    # 5) Submit the signed transaction to the network
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
    Sends a specified amount of a native token (policy_id + asset_name) 
    along with a small ADA amount (e.g., 2 ADA) to a destination address.
    
    The remainder of the tokens and ADA are returned as change to the from_address 
    to maintain value conservation in the transaction.

    Steps:
      1) Decode the hotkey using `decode_hotkey_skey` to retrieve the payment and stake keys.
      2) Gather all UTxOs (inputs) from the from_address, summing total coin (lovelace) and 
         multi-asset balances.
      3) Check if there's enough of the specified token to send token_amount.
      4) Prepare the first output with 2 ADA (example) plus the requested token_amount.
      5) Calculate change (both coin and leftover tokens) and place it into a second output.
      6) Build the transaction body, sign it with the payment_xsk, and submit the transaction.
      7) Return the resulting transaction ID.

    Args:
        chain_context (BlockFrostChainContext): The chain context to build and submit the transaction.
        base_dir (str): The base directory path where the coldkey/hotkey data is stored.
        coldkey_name (str): The name of the coldkey folder containing salt.bin, mnemonic.enc, etc.
        hotkey_name (str): The hotkey identifier used to decode the correct signing keys.
        password (str): The password needed to decrypt the hotkey's extended signing keys.
        to_address_str (str): Destination address in bech32 or base58 format.
        policy_id_hex (str): Hex representation of the policy ID for the native token.
        asset_name (str): The string name for the token within the policy.
        token_amount (int): The number of tokens to send.
        fee (int): The transaction fee in lovelace, default is 200_000 (0.2 ADA).
        network (Network): The Cardano network, default is TESTNET.

    Returns:
        str: The transaction ID (TX ID) after successful submission.
    """

    # 1) Decode the hotkey to retrieve the payment_xsk and stake_xsk (if any)
    payment_xsk, stake_xsk = decode_hotkey_skey(base_dir, coldkey_name, hotkey_name, password)
    if not payment_xsk:
        raise ValueError(f"Failed to decode Payment ExtendedSigningKey for hotkey '{hotkey_name}'")

    pay_xvk = payment_xsk.to_verification_key()
    stake_xvk = stake_xsk.to_verification_key() if stake_xsk else None

    # Construct the from_address using the payment and optional stake verification keys
    from_address = Address(
        payment_part=pay_xvk.hash(),
        staking_part=stake_xvk.hash() if stake_xvk else None,
        network=network
    )
    logger.info(f"[send_token] from_address={from_address}")

    # Get all UTxOs from the from_address
    utxos = chain_context.utxos(from_address)
    if not utxos:
        raise ValueError(f"No UTxOs found at {from_address}")

    # 2) Aggregate all inputs' coin and multi-assets
    tx_inputs = []
    total_coin_input = 0

    from pycardano import MultiAsset, Asset
    input_multiasset = MultiAsset()

    # Loop through each UTxO and accumulate coin + token balances
    for utxo in utxos:
        tx_inputs.append(utxo.input)
        val = utxo.output.amount

        # Add this UTxO's coin (lovelace) to the total coin input
        total_coin_input += val.coin

        # If there's any multi-asset, accumulate it in input_multiasset
        if val.multi_asset:
            for pid, assets_map in val.multi_asset.items():
                if pid not in input_multiasset:
                    input_multiasset[pid] = Asset()
                for aname, qty in assets_map.items():
                    if aname not in input_multiasset[pid]:
                        input_multiasset[pid][aname] = 0
                    input_multiasset[pid][aname] += qty

    # 3) Check the total tokens available for (policy_id, asset_name)
    pid_bytes = bytes.fromhex(policy_id_hex)
    aname_bytes = asset_name.encode("utf-8")

    policy_obj = ScriptHash.from_primitive(pid_bytes)
    # Alternatively, ScriptHash(hex=policy_id_hex) depending on the pycardano version
    
    asset_obj = AssetName(aname_bytes)

    # The total number of tokens we have for this specific policy and asset name
    total_token_input = input_multiasset.get(policy_obj, Asset()).get(asset_obj, 0)
    if total_token_input < token_amount:
        raise ValueError(
            f"Not enough '{asset_name}' tokens (policy={policy_id_hex}). "
            f"Needed: {token_amount}, found: {total_token_input}"
        )

    # 4) Prepare to send 2 ADA (as an example amount) to the destination 
    out1_coin = 2_000_000  # 2 ADA in lovelace
    if total_coin_input < fee + out1_coin:
        raise ValueError("Insufficient coin to cover both the fee and 2 ADA in the output.")

    # 5) Create output #1, which contains out1_coin lovelace + token_amount
    #    This is a 2-element list in the "Value.from_primitive" format:
    #    [coin_amount, {policy_id_bytes: {asset_name_bytes: token_amount}}]
    ma_value_out1 = [
        out1_coin,
        {
            pid_bytes: {
                aname_bytes: token_amount
            }
        }
    ]
    from pycardano import (
        Value, TransactionOutput, TransactionBody, Transaction, TransactionWitnessSet, VerificationKeyWitness
    )
    val_out1 = Value.from_primitive(ma_value_out1)
    out_token = TransactionOutput(Address.from_primitive(to_address_str), val_out1)

    # 6) Calculate the leftover coin after sending 2 ADA and covering the fee
    coin_change = total_coin_input - fee - out1_coin
    if coin_change < 0:
        raise ValueError("Coin change cannot be negative. Not enough funds.")

    # 7) Calculate the leftover tokens => total_token_input - token_amount
    token_change = total_token_input - token_amount

    # Clone the original input_multiasset and reduce the token_amount from it
    out_change_multiasset = MultiAsset()
    for pid, assets_map in input_multiasset.items():
        out_change_multiasset[pid] = Asset()
        for aname, qty in assets_map.items():
            out_change_multiasset[pid][aname] = qty

    # Subtract the token_amount from the specific policy/asset
    out_change_multiasset[policy_obj][asset_obj] -= token_amount

    # If the leftover of that asset is 0, remove it from the dictionary
    if out_change_multiasset[policy_obj][asset_obj] == 0:
        del out_change_multiasset[policy_obj][asset_obj]
    # If the policy itself has no remaining assets, delete the policy from the multi-asset
    if len(out_change_multiasset[policy_obj]) == 0:
        del out_change_multiasset[policy_obj]

    # 8) Create the change output with leftover coin and leftover tokens
    val_change = Value(coin_change, out_change_multiasset)
    out_change = TransactionOutput(from_address, val_change)

    # 9) Build the transaction body with the two outputs
    tx_body = TransactionBody(
        inputs=tx_inputs,
        outputs=[out_token, out_change],
        fee=fee
    )

    # 10) Sign the transaction body with our payment ExtendedSigningKey
    signature = payment_xsk.sign(tx_body.hash())
    vk_witness = VerificationKeyWitness(pay_xvk, signature)
    witness_set = TransactionWitnessSet(vkey_witnesses=[vk_witness])

    # 11) Construct the transaction and submit it to the network
    signed_tx = Transaction(tx_body, witness_set)
    tx_id = chain_context.submit_tx(signed_tx.to_cbor())

    logger.info(f"[send_token] => TX ID: {tx_id}")
    return tx_id
