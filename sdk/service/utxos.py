from typing import Type
from pycardano import Address, BlockFrostChainContext, UTxO
import cbor2

def get_utxo_from_str(
    contract_address: Address,
    datumclass: Type,
    context: BlockFrostChainContext,
    search_uid: bytes = b"miner_002"
) -> UTxO:
    """
    Retrieve a UTxO from the contract address based on a specific UID in the datum.

    This function iterates through all UTxOs at the given contract address, decodes their datums,
    and checks if the 'uid' field matches the provided search_uid.

    Args:
        contract_address (Address): The address of the Plutus smart contract.
        datumclass (Type): The class type of the datum (e.g., MinerDatum).
        context (BlockFrostChainContext): The blockchain context to query UTxOs.
        search_uid (bytes): The UID to search for in the datum (default: b"miner_002").

    Returns:
        UTxO: The UTxO with the matching UID.

    Raises:
        Exception: If no UTxO with the specified UID is found.
    """
    for utxo in context.utxos(str(contract_address)):
        # Decode the datum from CBOR format
        outputdatum = cbor2.loads(utxo.output.datum.cbor)
        # Map the decoded datum values into the datumclass
        param = datumclass(*outputdatum.value)
        # Compare the UID directly with the search_uid
        if search_uid == param.uid:
            return utxo
    raise Exception(f"UTxO not found for UID: {search_uid}")

def get_utxo_with_lowest_incentive(
    contract_address: Address,
    datumclass: Type,
    context: BlockFrostChainContext
) -> UTxO:
    """
    Find the UTxO with the lowest 'incentive' value from the smart contract.

    This function iterates through all UTxOs at the contract address, decodes their datums,
    and identifies the UTxO with the smallest 'incentive' value in the datum.

    Args:
        contract_address (Address): The address of the Plutus smart contract.
        datumclass (Type): The class type of the datum (e.g., MinerDatum).
        context (BlockFrostChainContext): The blockchain context to query UTxOs.

    Returns:
        UTxO: The UTxO with the lowest incentive value.

    Raises:
        Exception: If no UTxOs are found at the contract address.
    """
    lowest_performance_utxo = None
    lowest_performance = None

    for utxo in context.utxos(str(contract_address)):
        # Decode the datum from CBOR format
        outputdatum = cbor2.loads(utxo.output.datum.cbor)
        # Map the decoded datum values into the datumclass
        param = datumclass(*outputdatum.value)
        # Get the incentive value (assumes 'incentive' is a field in datumclass)
        performance = param.performance

        # Track the UTxO with the lowest incentive
        if lowest_performance is None or performance < lowest_performance:
            lowest_incentive = performance
            lowest_performance_utxo = utxo

    if lowest_performance_utxo is None:
        raise Exception("No UTxOs found at the contract address.")
    
    return lowest_performance_utxo