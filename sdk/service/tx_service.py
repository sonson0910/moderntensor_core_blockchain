# sdk/node/cardano_service/tx_service.py

import logging
from typing import Optional
from pycardano import (
    Address, 
    TransactionBuilder,
    TransactionOutput,
    Value,
    MultiAsset,
    AssetClass,
    PaymentSigningKey,
    Transaction,
    TransactionWitnessSet,
    Network,
)

logger = logging.getLogger(__name__)

def send_ada(
    chain_context,
    from_signing_key: PaymentSigningKey,
    to_address_str: str,
    lovelace_amount: int,
    network: Network,
    change_address_str: Optional[str] = None
) -> str:
    """
    Gửi ADA (lovelace) từ 'from_signing_key' => 'to_address_str'.
    """
    from_address = Address(
        payment_part=from_signing_key.to_public_key().hash(),
        network=network
    )
    to_address = Address.from_primitive(to_address_str)
    change_address = Address.from_primitive(change_address_str) if change_address_str else from_address

    builder = TransactionBuilder(chain_context)
    utxos = chain_context.utxos(from_address)
    for utxo in utxos:
        builder.add_input(utxo)

    builder.add_output(TransactionOutput(to_address, lovelace_amount))
    tx_body = builder.build(change_address=change_address)

    tx_id = _sign_and_submit(chain_context, tx_body, from_signing_key)
    logger.info(f"[send_ada] Sent {lovelace_amount} lovelace => {to_address_str}, tx_id={tx_id}")
    return tx_id

def send_token(
    chain_context,
    from_signing_key: PaymentSigningKey,
    to_address_str: str,
    policy_id: str,
    asset_name: str,
    token_amount: int,
    lovelace_amount: int,
    network: Network,
    change_address_str: Optional[str] = None
) -> str:
    """
    Gửi native token, kèm lovelace, từ from_signing_key => to_address_str
    """
    from_address = Address(
        payment_part=from_signing_key.to_public_key().hash(),
        network=network
    )
    to_address = Address.from_primitive(to_address_str)
    change_address = Address.from_primitive(change_address_str) if change_address_str else from_address

    builder = TransactionBuilder(chain_context)
    utxos = chain_context.utxos(from_address)
    for utxo in utxos:
        builder.add_input(utxo)

    # Tạo multi_asset
    asset_class = AssetClass(bytes.fromhex(policy_id), asset_name.encode('utf-8'))
    multi_asset = MultiAsset.from_assets({asset_class: token_amount})
    value = Value(lovelace_amount, multi_asset)

    builder.add_output(TransactionOutput(to_address, value))
    tx_body = builder.build(change_address=change_address)

    tx_id = _sign_and_submit(chain_context, tx_body, from_signing_key)
    logger.info(f"[send_token] Sent {token_amount} {asset_name} => {to_address_str}, tx_id={tx_id}")
    return tx_id

def _sign_and_submit(chain_context, tx_body, signing_key: PaymentSigningKey) -> str:
    """
    Ký transaction và submit. 
    """
    from pycardano import TransactionWitnessSet
    witness = TransactionWitnessSet()
    witness.signatures[signing_key.hash()] = signing_key.sign(tx_body.hash())

    tx = Transaction(tx_body, witness_set=witness)
    tx_id = chain_context.submit_tx(tx)
    return tx_id
