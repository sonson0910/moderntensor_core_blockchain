from typing import Optional
from pycardano import (
    ExtendedSigningKey,
    ScriptHash,
    PlutusV3Script,
    BlockFrostChainContext,
    Network,
    PlutusData,
    Redeemer,
    UTxO,
)
from sdk.service.utxos import get_utxo_with_lowest_incentive
from sdk.metagraph.update_metagraph import update_datum
from sdk.metagraph.metagraph_datum import MinerDatum  # Giả sử đây là lớp datum của bạn
from sdk.config.settings import settings

def register_key(
    payment_xsk: ExtendedSigningKey,
    stake_xsk: Optional[ExtendedSigningKey],
    script_hash: ScriptHash,
    new_datum: PlutusData,
    script: PlutusV3Script,
    context: BlockFrostChainContext,
    network: Optional[Network] = None,
    contract_address: ScriptHash = None,
    redeemer: Optional[Redeemer] = None,
) -> str:
    """
    Dịch vụ đăng ký khóa mới bằng cách cập nhật UTxO có incentive thấp nhất.

    Dịch vụ này tìm UTxO có incentive thấp nhất từ hợp đồng thông minh, sau đó sử dụng hàm update_datum
    để cập nhật UTxO đó với dữ liệu mới được cung cấp.

    Args:
        payment_xsk (ExtendedSigningKey): Khóa ký thanh toán của người dùng.
        stake_xsk (Optional[ExtendedSigningKey]): Khóa ký staking của người dùng (tùy chọn).
        new_datum (PlutusData): Dữ liệu mới để gắn vào UTxO.
        script (PlutusV3Script): Script Plutus của hợp đồng thông minh.
        context (BlockFrostChainContext): Context blockchain để tương tác với mạng Cardano.
        network (Optional[Network]): Mạng Cardano (mainnet hoặc testnet). Mặc định là settings.CARDANO_NETWORK.
        contract_address (ScriptHash): Địa chỉ của hợp đồng thông minh. Mặc định là settings.CONTRACT_ADDRESS.
        redeemer (Optional[Redeemer]): Redeemer dùng để xác thực script. Mặc định là Redeemer(0).

    Returns:
        str: ID giao dịch của giao dịch đã được gửi.

    Raises:
        ValueError: Nếu không tìm thấy UTxO nào tại địa chỉ hợp đồng.
    """
    # Sử dụng giá trị mặc định từ settings nếu không được cung cấp
    network = network or settings.CARDANO_NETWORK
    contract_address = contract_address or settings.TEST_CONTRACT_ADDRESS

    # Tìm UTxO có incentive thấp nhất
    lowest_utxo: UTxO = get_utxo_with_lowest_incentive(
        contract_address=contract_address, 
        datumclass=MinerDatum, 
        context=context
    )
    if not lowest_utxo:
        raise ValueError("Không tìm thấy UTxO nào tại địa chỉ hợp đồng.")

    # Cập nhật UTxO với dữ liệu mới bằng hàm update_datum
    tx_id = update_datum(
        payment_xsk=payment_xsk,
        stake_xsk=stake_xsk,
        script_hash=script_hash,
        utxo=lowest_utxo,
        new_datum=new_datum,
        script=script,
        context=context,
        network=network,
        redeemer=redeemer or Redeemer(0),
    )

    return tx_id