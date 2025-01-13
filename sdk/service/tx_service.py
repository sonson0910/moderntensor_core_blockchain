# sdk/service/tx_service.py

import logging
from typing import Optional
from pycardano import (
    Address,
    TransactionBuilder,
    TransactionOutput,
    Network,
)

logger = logging.getLogger(__name__)

def send_ada(
    chain_context,
    payment_xsk,     # ExtendedSigningKey (hoặc PaymentSigningKey)
    stake_xsk=None,  # ExtendedSigningKey stake (optional) - nếu cần
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

    # 4) Thêm output => gửi ADA
    builder.add_output(TransactionOutput(to_address, lovelace_amount))

    # 5) Tạo signed_tx
    signed_tx = builder.build_and_sign(
        signing_keys=[payment_xsk],  # Ký = payment_xsk
        change_address=change_address
    )

    # 6) submit
    tx_id = chain_context.submit_tx(signed_tx.to_cbor())
    logger.info(f"[send_ada] => TX ID: {tx_id}")
    return tx_id
