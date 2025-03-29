from pycardano import (
    Address,
    BlockFrostChainContext,
    UTxO,
)
import cbor2
from typing import Type

def get_utxo_from_str(contract_address: Address, datumclass: Type, context: BlockFrostChainContext) -> UTxO:
    for utxo in context.utxos(str(contract_address)):
        outputdatum = cbor2.loads(utxo.output.datum.cbor)
        # Truyền tất cả giá trị từ outputdatum.value vào datumclass
        param = datumclass(*outputdatum.value)
        # So sánh owner (bytes) trực tiếp với b"miner_001"
        if b"miner_002" == param.uid:
            return utxo
    raise Exception(f"UTxO not found for transaction")


def get_utxo_with_lowest_incentive(
    contract_address: Address,
    datumclass: Type,
    context: BlockFrostChainContext
) -> UTxO:
    """
    Tìm UTxO có giá trị incentive thấp nhất từ hợp đồng thông minh.

    Hàm này duyệt qua tất cả UTxO tại địa chỉ hợp đồng, giải mã datum của chúng,
    và xác định UTxO có giá trị 'incentive' nhỏ nhất trong datum.

    Args:
        contract_address (Address): Địa chỉ của hợp đồng thông minh Plutus.
        datumclass (Type): Kiểu lớp của datum (ví dụ: MinerDatum).
        context (BlockFrostChainContext): Context blockchain để truy vấn UTxO.

    Returns:
        UTxO: UTxO có giá trị incentive thấp nhất.

    Raises:
        Exception: Nếu không tìm thấy UTxO nào tại địa chỉ hợp đồng.
    """
    lowest_incentive_utxo = None
    lowest_incentive = None

    for utxo in context.utxos(str(contract_address)):
        # Giải mã datum từ CBOR
        outputdatum = cbor2.loads(utxo.output.datum.cbor)
        # Ánh xạ datum vào lớp datumclass
        param = datumclass(*outputdatum.value)
        # Lấy giá trị incentive (giả sử 'incentive' là một trường trong datumclass)
        incentive = param.incentive

        # Theo dõi UTxO có incentive thấp nhất
        if lowest_incentive is None or incentive < lowest_incentive:
            lowest_incentive = incentive
            lowest_incentive_utxo = utxo

    if lowest_incentive_utxo is None:
        raise Exception("Không tìm thấy UTxO nào tại địa chỉ hợp đồng.")
    
    return lowest_incentive_utxo