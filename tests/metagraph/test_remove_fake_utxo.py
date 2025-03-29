from dataclasses import dataclass
import pytest
from pycardano import (
    Address,
    Network,
    PlutusData,
)
from sdk.metagraph.remove_fake_utxo import remove_fake_utxos
from sdk.service.context import get_chain_context
from sdk.smartcontract.validator import read_validator
from sdk.config.settings import logger


# Mock HelloWorldDatum class to simulate datum from unlock.py
@dataclass
class HelloWorldDatum(PlutusData):
    """A mock Plutus data class representing the HelloWorldDatum."""
    CONSTR_ID = 0


# Fixture for blockchain context
@pytest.fixture(scope="session")
def chain_context_fixture():
    """
    Provides a blockchain context for the Cardano TESTNET using BlockFrost.

    This fixture creates a BlockFrostChainContext configured for the TESTNET, which is reused
    throughout the test session for efficiency.

    Steps:
        1. Optionally retrieves BLOCKFROST_PROJECT_ID from settings (commented out).
        2. Calls get_chain_context with the "blockfrost" method.
        3. Returns the configured chain context.

    Returns:
        BlockFrostChainContext: A chain context for interacting with Cardano TESTNET.
    """
    # Uncomment to use a specific project ID from settings if needed:
    # project_id = settings.BLOCKFROST_PROJECT_ID
    # return get_chain_context(method="blockfrost", project_id=project_id, network=Network.TESTNET)
    return get_chain_context(method="blockfrost")


# Fixture for fake UTxOs
@pytest.fixture
def fake_utxos(chain_context_fixture):
    """
    Simulates a list of fake UTxOs associated with a Plutus contract address.

    This fixture constructs a contract address using the validator's script hash and retrieves
    all UTxOs from that address using the provided chain context.

    Args:
        chain_context_fixture (BlockFrostChainContext): The blockchain context fixture.

    Returns:
        List[UTxO]: A list of UTxOs from the contract address.
    """
    validator = read_validator()
    script_hash = validator["script_hash"]
    contract_address = Address(
        payment_part=script_hash,
        network=Network.TESTNET,
    )
    utxos = chain_context_fixture.utxos(str(contract_address))
    return utxos


# Fixture for Plutus contract script
@pytest.fixture
def script():
    """
    Provides the Plutus contract script for testing.

    This fixture loads the script bytes from the validator, representing the Plutus smart contract.

    Returns:
        PlutusV3Script: The Plutus script bytes.
    """
    validator = read_validator()
    return validator["script_bytes"]


# Main test function
@pytest.mark.integration
def test_remove_fake_utxos(chain_context_fixture, fake_utxos, script, hotkey_skey_fixture):
    """
    Tests the remove_fake_utxos function to ensure it removes fake UTxOs successfully.

    This integration test verifies that the remove_fake_utxos function processes a list of fake
    UTxOs, submits a transaction to the Cardano TESTNET, and returns a valid transaction ID.

    Args:
        chain_context_fixture (BlockFrostChainContext): The blockchain context fixture.
        fake_utxos (List[UTxO]): The list of fake UTxOs to remove.
        script (PlutusV3Script): The Plutus contract script.
        hotkey_skey_fixture (tuple): A tuple containing payment and stake signing keys.

    Asserts:
        - The transaction ID is not None.
        - The transaction ID is a non-empty string.
    """
    # Unpack signing keys
    payment_xsk, stake_xsk = hotkey_skey_fixture

    # Define network
    network = Network.TESTNET

    # Execute the function to remove fake UTxOs
    tx_id = remove_fake_utxos(
        payment_xsk=payment_xsk,
        stake_xsk=stake_xsk,
        fake_utxos=fake_utxos,
        script=script,
        context=chain_context_fixture,
        network=network,
    )

    # Validate the transaction ID
    assert tx_id is not None, "Transaction ID must not be None"
    logger.info(f"Transaction ID: {tx_id}")
    assert len(tx_id) > 0, "Transaction ID must be a non-empty string"