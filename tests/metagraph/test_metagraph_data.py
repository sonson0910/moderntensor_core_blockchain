import pytest
from pycardano import Address, Network
from sdk.service.context import get_chain_context
from sdk.metagraph.metagraph_data import get_all_utxo_data
from sdk.smartcontract.validator import read_validator
from sdk.metagraph.metagraph_datum import MinerDatum

# Define the network as a constant for consistency

# Fixture to provide a real blockchain context
@pytest.fixture(scope="session")
def real_chain_context():
    """
    Provides a real blockchain context to query the Cardano blockchain.

    This fixture sets up a BlockFrostChainContext for the specified network (TESTNET by default),
    allowing the test to interact with the Cardano blockchain in real-time.

    Returns:
        BlockFrostChainContext: A configured chain context for querying the blockchain.
    """
    return get_chain_context(method="blockfrost")

# Test function to verify get_all_utxo_data with real UTxOs
def test_get_all_utxo_data_real_utxos(real_chain_context):
    """
    Tests the get_all_utxo_data function with real UTxOs from a smart contract address.

    This integration test verifies that the get_all_utxo_data function correctly retrieves and
    structures data for all unspent transaction outputs (UTxOs) at the specified contract address
    on the Cardano blockchain.

    Args:
        real_chain_context (BlockFrostChainContext): Fixture providing the blockchain context.

    Asserts:
        - The result is a non-empty list of UTxO data.
        - Each UTxO data dictionary contains required keys: 'tx_id', 'index', 'amount', and 'datum'.
        - Each 'datum' dictionary contains expected fields: 'uid', 'stake', and 'performance'.

    Notes:
        - The test prints details of the first UTxO for manual verification.
        - The contract address is derived from the script hash loaded from the validator.
    """
    # Load validator details and extract the script hash
    validator = read_validator()
    script_hash = validator["script_hash"]  # Hash of the Plutus script
    network = Network.TESTNET

    # Retrieve UTxO data from the contract address
    utxo_data_list = get_all_utxo_data(
        script_hash=script_hash,
        datumclass=MinerDatum,
        context=real_chain_context,
        network=network
    )

    # Verify basic properties of the result
    assert isinstance(utxo_data_list, list), "Result must be a list"
    assert len(utxo_data_list) > 0, "At least one UTxO should exist at the contract address"

    # Validate the structure of each UTxO data entry
    for utxo_data in utxo_data_list:
        assert "tx_id" in utxo_data, "UTxO data must include 'tx_id'"
        assert "index" in utxo_data, "UTxO data must include 'index'"
        assert "amount" in utxo_data, "UTxO data must include 'amount'"
        assert "datum" in utxo_data, "UTxO data must include 'datum'"

        # Check the structure of the datum
        datum = utxo_data["datum"]
        assert "uid" in datum, "Datum must include 'uid'"
        assert "stake" in datum, "Datum must include 'stake'"
        assert "performance" in datum, "Datum must include 'performance'"

    # Print details of the first UTxO for manual inspection
    first_utxo_data = utxo_data_list[0]
    print(f"First UTxO: {first_utxo_data['tx_id']}#{first_utxo_data['index']}")
    print(f"Amount: {first_utxo_data['amount']} lovelace")
    print(f"Datum: {first_utxo_data['datum']}")
