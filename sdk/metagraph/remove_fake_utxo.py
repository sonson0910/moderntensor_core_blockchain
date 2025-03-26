from pycardano import (
    TransactionBuilder,
    TransactionOutput,
    Address,
    UTxO,
    PlutusV3Script,
    Redeemer,
    PaymentSigningKey,
    BlockFrostChainContext,
    TransactionId,
    VerificationKeyHash,
)
from typing import List

def remove_fake_utxos(
    fake_utxos: List[UTxO],
    script: PlutusV3Script,
    redeemer: Redeemer,
    signing_key: PaymentSigningKey,
    owner: VerificationKeyHash,
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
    # Đọc địa chỉ của người thực hiện từ file me.addr
    with open("me.addr", "r") as f:
        owner_address = Address.from_primitive(f.read())

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
        signing_keys=[signing_key],
        change_address=owner_address,
    )
    tx_id = context.submit_tx(signed_tx)

    return tx_id