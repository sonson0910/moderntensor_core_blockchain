from pycardano import TransactionBuilder, TransactionOutput, Address, UTxO, PlutusData, Redeemer, ScriptHash, Network, BlockFrostChainContext, ExtendedSigningKey, PlutusV3Script, RawCBOR, PaymentExtendedVerificationKey
from sdk.service.context import get_chain_context

from sdk.config.settings import settings  # Cấu hình mạng Cardano
from dataclasses import dataclass


def update_datum(
    payment_xsk: ExtendedSigningKey,
    stake_xsk: ExtendedSigningKey,
    into: ScriptHash,
    utxo: UTxO,
    new_datum: PlutusData,
    script: PlutusV3Script,
    context: BlockFrostChainContext,
    network: Network
):
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
    # context = get_chain_context(method="blockfrost")
    print(utxo)
    network = network

    pay_xvk = PaymentExtendedVerificationKey.from_signing_key(payment_xsk)
    if stake_xsk:
        stk_xvk = stake_xsk.to_verification_key()
        owner_address = Address(payment_part=pay_xvk.hash(), staking_part=stk_xvk.hash(), network=network)
    else:
        owner_address = Address(payment_part=pay_xvk.hash(), network=network)
    print(owner_address)
    owner=PaymentExtendedVerificationKey.from_signing_key(payment_xsk).hash()

    # # Lấy địa chỉ hợp đồng từ UTxO hiện tại
    # contract_address = Address(
    #     payment_part=utxo.output.address.payment_part,
    #     network=network
    # )
        # Tạo địa chỉ hợp đồng từ script_hash
    contract_address = Address(
        payment_part=into,
        network=network  # Có thể thay đổi thành Network.MAINNET nếu cần
    )
    redeemer = Redeemer(data=HelloWorldRedeemer())

    # Tạo giao dịch
    builder = TransactionBuilder(context=context)
    builder.add_script_input(
        utxo=utxo,
        script=script,
        redeemer=redeemer,
    )
    builder.add_input_address(owner_address)

    print("CBOR của MinerDatum:", new_datum.to_cbor_hex())

    # Yêu cầu chữ ký từ owner
    builder.required_signers = [owner]

    # Tạo UTxO mới với datum đã cập nhật
    builder.add_output(
        TransactionOutput(
            address=contract_address,
            amount=utxo.output.amount.coin,  # Giữ nguyên số tiền
            datum=new_datum    # Datum mới
        )
    )

    # Ký và gửi giao dịch
    signed_tx = builder.build_and_sign(
        signing_keys=[payment_xsk],
        change_address=owner_address
    )

    return context.submit_tx(signed_tx)

@dataclass
class HelloWorldRedeemer(PlutusData):
    CONSTR_ID = 0