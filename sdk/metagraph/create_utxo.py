from pycardano import (
    TransactionBuilder,
    TransactionOutput,
    Address,
    ScriptHash,
    PlutusData,
    BlockFrostChainContext,
    Network,
    TransactionId, 
    ExtendedSigningKey
)


def create_utxo(
    payment_xsk: ExtendedSigningKey,
    stake_xsk: ExtendedSigningKey,
    amount: int,
    script_hash: ScriptHash,
    datum: PlutusData,
    context: BlockFrostChainContext,
    network: Network
) -> TransactionId:
    """
    Sinh một UTxO với số ADA và datum được khóa vào hợp đồng Plutus.
    
    Args:
        amount: Số lượng lovelace (ví dụ: 2_000_000 cho 2 tADA).
        script_hash: Hash của hợp đồng Plutus (ScriptHash).
        datum: Dữ liệu datum (PlutusData) để gắn vào UTxO.
        signing_key: Khóa ký giao dịch (PaymentSigningKey).
        owner_address: Địa chỉ của chủ sở hữu, dùng làm đầu vào và nhận tiền thừa.
        context: Chain context (BlockFrostChainContext). Nếu không cung cấp, lấy từ get_chain_context().
    
    Returns:
        TransactionId: ID của giao dịch đã gửi lên blockchain.
    """
    network = network or settings.CARDANO_NETWORK

    pay_xvk = payment_xsk.to_verification_key()
    if stake_xsk:
        stk_xvk = stake_xsk.to_verification_key()
        owner_address = Address(payment_part=pay_xvk.hash(), staking_part=stk_xvk.hash(), network=network)
    else:
        owner_address = Address(payment_part=pay_xvk.hash(), network=network)
    
    print(owner_address)

    # Tạo địa chỉ hợp đồng từ script_hash
    contract_address = Address(
        payment_part=script_hash,
        network=network  # Có thể thay đổi thành Network.MAINNET nếu cần
    )

    # Xây dựng giao dịch
    builder = TransactionBuilder(context=context)
    builder.add_input_address(owner_address)
    builder.add_output(
        TransactionOutput(
            address=contract_address,
            amount=amount,
            datum=datum
        )
    )

    # Ký và gửi giao dịch
    signed_tx = builder.build_and_sign(
        signing_keys=[payment_xsk],
        change_address=owner_address
    )
    tx_id = context.submit_tx(signed_tx)

    return tx_id