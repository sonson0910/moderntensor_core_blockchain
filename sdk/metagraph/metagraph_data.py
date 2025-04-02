from typing import (
    List, 
    Type, 
    Dict, 
    Any
)
from pycardano import (
    Address, 
    BlockFrostChainContext, 
    PlutusData, 
    ScriptHash, 
    Network    
)
import cbor2

def get_all_utxo_data(
    script_hash: ScriptHash,
    datumclass: Type[PlutusData],
    context: BlockFrostChainContext,
    network: Network
) -> List[Dict[str, Any]]:
    """
    Retrieves all UTxO data from a Plutus smart contract on the Cardano blockchain and returns it as an array.

    This service fetches all UTxOs at the specified contract address, decodes their datums using the provided
    datum class, and returns a list of dictionaries containing the UTxO details and datum fields.

    Args:
        contract_address (Address): The address of the Plutus smart contract.
        datumclass (Type[PlutusData]): The class type of the datum (e.g., MinerDatum).
        context (BlockFrostChainContext): The blockchain context to query UTxOs.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, where each dictionary contains:
            - tx_id: The transaction ID of the UTxO.
            - index: The output index of the UTxO.
            - amount: The amount of lovelace in the UTxO.
            - datum: A dictionary of the decoded datum fields.

    Raises:
        Exception: If there is an error decoding the datum or if no UTxOs are found.
    """
    # Initialize an empty list to store UTxO data
    utxo_data_list = []

    # Create the contract address using the provided script hash
    contract_address = Address(
        payment_part=script_hash,
        network=network
    )

    # Fetch all UTxOs from the contract address
    utxos = context.utxos(str(contract_address))

    # Iterate through each UTxO
    for utxo in utxos:
        try:
            # Decode the datum from CBOR format
            outputdatum = cbor2.loads(utxo.output.datum.cbor)
            # Map the decoded datum values into the datumclass
            param = datumclass(*outputdatum.value)

            # Extract datum fields into a dictionary
            # Assuming datumclass has fields like uid, stake, etc.
            datum_dict = {
                "uid": param.uid.decode() if isinstance(param.uid, bytes) else param.uid,
                "stake": param.stake,
                "performance": param.performance,
                "trust_score": param.trust_score,
                "accumulated_rewards": param.accumulated_rewards,
                "last_evaluated": param.last_evaluated,
                "history_hash": param.history_hash.hex() if isinstance(param.history_hash, bytes) else param.history_hash,
                "wallet_addr_hash": param.wallet_addr_hash.hex() if isinstance(param.wallet_addr_hash, bytes) else param.wallet_addr_hash,
                "status": param.status.decode() if isinstance(param.status, bytes) else param.status,
                "block_reg_at": param.block_reg_at,
            }

            # Construct the UTxO data dictionary
            utxo_data = {
                "tx_id": str(utxo.input.transaction_id),
                "index": utxo.input.index,
                "amount": utxo.output.amount.coin,
                "datum": datum_dict,
            }

            # Add the UTxO data to the list
            utxo_data_list.append(utxo_data)

        except Exception as e:
            # Log the error and continue with the next UTxO
            print(f"Error decoding datum for UTxO {utxo.input.transaction_id}: {str(e)}")
            continue

    # Check if any UTxOs were found
    if not utxo_data_list:
        raise Exception("No UTxOs found at the contract address.")

    return utxo_data_list