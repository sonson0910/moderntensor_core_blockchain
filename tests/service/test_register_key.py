import pytest
from pycardano import Address, Network, Redeemer
from sdk.service.context import get_chain_context
from sdk.smartcontract.validator import read_validator
from sdk.service.register_key import register_key
from sdk.metagraph.metagraph_datum import MinerDatum

# Define the network as a constant for consistency
NETWORK = Network.TESTNET

# Fixture to provide a real blockchain context
@pytest.fixture(scope="session")
def chain_context():
    """
    Provides a real blockchain context to interact with the Cardano blockchain.

    This fixture establishes a connection to the Cardano blockchain using BlockFrost, enabling
    real-time queries and transactions on the specified network (TESTNET by default).

    Returns:
        BlockFrostChainContext: A configured chain context for blockchain interaction.
    """
    return get_chain_context(method="blockfrost")

# Fixture to provide the Cardano network
@pytest.fixture(scope="session")
def get_network():
    """
    Provides the Cardano network for the test environment.

    This fixture returns the network constant defined at the module level, set to TESTNET to
    ensure tests do not affect the mainnet.

    Returns:
        Network: The Cardano network (e.g., Network.TESTNET).
    """
    return NETWORK

# Fixture to provide the Plutus script
@pytest.fixture
def script():
    """
    Provides the Plutus script bytes from the validator.

    This fixture retrieves the Plutus script bytes from the validator configuration, which are
    used to interact with the smart contract on the blockchain.

    Returns:
        PlutusV3Script: The bytes of the Plutus script.
    """
    validator = read_validator()
    return validator["script_bytes"]

# Fixture to provide the script hash
@pytest.fixture
def script_hash():
    """
    Provides the script hash of the Plutus smart contract.

    This fixture retrieves the script hash from the validator configuration, used to uniquely
    identify the smart contract on the blockchain.

    Returns:
        ScriptHash: The hash of the Plutus script.
    """
    validator = read_validator()
    return validator["script_hash"]

# Fixture to provide the contract address
@pytest.fixture
def contract_address(get_network):
    """
    Creates the contract address using the script hash and network.

    This fixture constructs the smart contract address by combining the script hash with the
    specified network (TESTNET by default).

    Args:
        get_network (Network): The Cardano network fixture.

    Returns:
        Address: The address of the smart contract on the blockchain.
    """
    validator = read_validator()
    script_hash = validator["script_hash"]
    return Address(payment_part=script_hash, network=get_network)

# Fixture to provide new datum for updating the UTxO
@pytest.fixture
def new_datum():
    """
    Provides new datum to update the UTxO on the blockchain.

    This fixture creates a new MinerDatum instance with sample data for testing purposes.
    The structure should be adjusted to match the actual datum expected by the smart contract.

    Returns:
        MinerDatum: A new instance of MinerDatum with sample data.
    """
    return MinerDatum(
        uid=b"new_miner",
        stake=1000,
        performance=95,
        trust_score=90,
        accumulated_rewards=0,
        last_evaluated=0,
        history_hash=b"new_history_hash",
        wallet_addr_hash=b"new_wallet_hash",
        status=b"active",
        block_reg_at=0,
    )

# Test function to verify register_key with real UTxOs
def test_register_new_key_service_real_utxo(
    chain_context,
    script,
    script_hash,
    contract_address,
    new_datum,
    hotkey_skey_fixture,
    get_network
):
    """
    Tests the register_key function using real UTxOs from a smart contract address.

    This test verifies that the register_key function can successfully update the datum of a
    real UTxO on the Cardano blockchain and return a valid transaction ID.

    Args:
        chain_context (BlockFrostChainContext): Fixture providing the blockchain context.
        script (PlutusV3Script): Fixture providing the Plutus script bytes.
        script_hash (ScriptHash): Fixture providing the script hash.
        contract_address (Address): Fixture providing the contract address.
        new_datum (MinerDatum): Fixture providing the new datum to update the UTxO.
        hotkey_skey_fixture (tuple): Fixture providing payment and stake signing keys.
        get_network (Network): Fixture providing the Cardano network.

    Steps:
        1. Extract payment and stake signing keys from the hotkey_skey_fixture.
        2. Call the register_key function with a simple redeemer (Redeemer(0)).
        3. Verify that the returned transaction ID is valid.

    Asserts:
        - The transaction ID is not None.
        - The transaction ID is a non-empty string.

    Notes:
        - The transaction ID is printed for manual verification (e.g., via a blockchain explorer).
        - Adjust the redeemer value if the smart contract requires a specific one.
    """
    # Extract payment and stake signing keys from the fixture
    payment_xsk, stake_xsk = hotkey_skey_fixture

    # Call the register_key function with the provided parameters
    tx_id = register_key(
        payment_xsk=payment_xsk,
        stake_xsk=stake_xsk,
        script_hash=script_hash,
        new_datum=new_datum,
        script=script,
        context=chain_context,
        network=get_network,
        contract_address=contract_address,
        redeemer=Redeemer(0),  # Adjust this if the script requires a different redeemer
    )

    # Verify the transaction ID is valid
    assert tx_id is not None, "Transaction ID must not be None"
    assert len(tx_id) > 0, "Transaction ID must be a non-empty string"

    # Print the transaction ID for manual inspection
    print(f"Transaction ID: {tx_id}")