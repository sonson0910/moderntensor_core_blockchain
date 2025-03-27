from pycardano import (
    Address,
    BlockFrostChainContext,
    UTxO,
    VerificationKeyHash,
)
import cbor2
from typing import Type
 
def get_utxo_from_str(contract_address: Address, datumclass: Type, context: BlockFrostChainContext) -> UTxO:
    # print(contract_address)
    # print(context.utxos(str(contract_address)))
    for utxo in context.utxos(str(contract_address)):
        outputdatum = cbor2.loads(utxo.output.datum.cbor)
        param = datumclass(uid=outputdatum.value[0])
        if "miner_001" == str(param.owner.hex()):
            # print(str(param.owner.hex()) + " - " + str(paymentkey_hash))
            return utxo
    raise Exception(f"UTxO not found for transaction")