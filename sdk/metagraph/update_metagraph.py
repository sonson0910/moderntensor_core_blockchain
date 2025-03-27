from pycardano import TransactionBuilder, TransactionOutput, Address, UTxO, PlutusData, Redeemer, ScriptHash, Network, BlockFrostChainContext, ExtendedSigningKey

from sdk.config.settings import settings  # Cấu hình mạng Cardano

def update_datum(
    payment_xsk: ExtendedSigningKey,
    stake_xsk: ExtendedSigningKey,
    utxo: UTxO,
    new_datum: PlutusData,
    script_hash: ScriptHash,
    context: BlockFrostChainContext,
    network: Network
) -> str:
    """
    Cập nhật datum của UTxO cho bất kỳ đối tượng nào.

    Args:
        utxo: UTxO hiện có chứa datum cần cập nhật
        new_datum: Datum mới đã được cập nhật
        signing_key: Khóa ký giao dịch
        owner_address: Địa chỉ của chủ sở hữu (nhận tiền thừa nếu có)
        script_hash: Hash của hợp đồng Plutus (nếu có)

    Returns:
        tx_id: ID của giao dịch đã gửi lên blockchain
    """

    network = network or settings.CARDANO_NETWORK

    pay_xvk = payment_xsk.to_verification_key()
    if stake_xsk:
        stk_xvk = stake_xsk.to_verification_key()
        owner_address = Address(payment_part=pay_xvk.hash(), staking_part=stk_xvk.hash(), network=network)
    else:
        owner_address = Address(payment_part=pay_xvk.hash(), network=network)

    owner=pay_xvk.hash()

    # Lấy địa chỉ hợp đồng từ UTxO hiện tại
    contract_address = Address(
        payment_part=utxo.output.address.payment_part,
        network=network
    )

    # Tạo giao dịch
    builder = TransactionBuilder(context=context)
    builder.add_input(utxo)  # Tiêu thụ UTxO cũ

    # Nếu có script_hash, thêm redeemer (giả định là 0)
    if script_hash:
        redeemer = Redeemer(0)
        builder.add_script_input(utxo=utxo, script_hash=script_hash, redeemer=redeemer)
    

    # Tạo UTxO mới với datum đã cập nhật
    builder.add_output(
        TransactionOutput(
            address=contract_address,
            amount=utxo.output.amount,  # Giữ nguyên số tiền
            datum=new_datum             # Datum mới
        )
    )

    # Yêu cầu chữ ký từ owner
    builder.required_signers = [owner]

    # Ký và gửi giao dịch
    signed_tx = builder.build_and_sign(
        signing_keys=[payment_xsk],
        change_address=owner_address
    )
    tx_id = context.submit_tx(signed_tx)

    return tx_id