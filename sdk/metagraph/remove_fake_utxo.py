from pycardano import (
    TransactionBuilder,
    TransactionOutput,
    Address,
    UTxO,
    PlutusV3Script,
    Redeemer,
    BlockFrostChainContext,
    TransactionId,
    ExtendedSigningKey,
    Network
)
from typing import List
from sdk.config.settings import settings, logger

def remove_fake_utxos(
    payment_xsk: ExtendedSigningKey,
    stake_xsk: ExtendedSigningKey,
    fake_utxos: List[UTxO],
    script: PlutusV3Script,
    redeemer: Redeemer,
    network: Network,
    context: BlockFrostChainContext,
) -> TransactionId:
    """
    Xóa các UTxO giả mạo khỏi hợp đồng thông minh.

    Args:
        fake_utxos: Danh sách UTxO giả mạo cần xóa.
        script: Mã hợp đồng Plutus.
        redeemer: Redeemer để thực thi hợp đồng.
        signing_key: Khóa ký giao dịch.
        owner: Hash của khóa xác minh của người thực hiện.
        context: Chain context để tương tác với blockchain.

    Returns:
        TransactionId: ID của giao dịch đã gửi.
    """

    network = network or settings.CARDANO_NETWORK

    pay_xvk = payment_xsk.to_verification_key()
    if stake_xsk:
        stk_xvk = stake_xsk.to_verification_key()
        owner_address = Address(payment_part=pay_xvk.hash(), staking_part=stk_xvk.hash(), network=network)
    else:
        owner_address = Address(payment_part=pay_xvk.hash(), network=network)

    owner=pay_xvk.hash()

    # Xây dựng giao dịch
    builder = TransactionBuilder(context=context)

    # Thêm từng UTxO giả mạo làm đầu vào
    for utxo in fake_utxos:
        builder.add_script_input(
            utxo=utxo,
            script=script,
            redeemer=redeemer,
        )

    # Thêm đầu vào từ địa chỉ của người thực hiện (để trả phí nếu cần)
    builder.add_input_address(owner_address)

    # Tính tổng ADA từ các UTxO giả mạo
    total_amount = sum(utxo.output.amount.coin for utxo in fake_utxos)

    # Thêm đầu ra trả lại tổng ADA về địa chỉ của người thực hiện
    builder.add_output(
        TransactionOutput(
            address=owner_address,
            amount=total_amount,
        )
    )

    # Yêu cầu chữ ký từ owner
    builder.required_signers = [owner]

    # Ký và gửi giao dịch
    signed_tx = builder.build_and_sign(
        signing_keys=[payment_xsk],
        change_address=owner_address,
    )
    tx_id = context.submit_tx(signed_tx)

    return tx_id