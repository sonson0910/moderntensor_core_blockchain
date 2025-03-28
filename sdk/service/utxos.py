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