import pytest
from pycardano import Network, Address
from sdk.metagraph.update_metagraph import update_datum
from sdk.metagraph.metagraph_datum import MinerDatum
from sdk.service.context import get_chain_context
from sdk.smartcontract.validator import read_validator
from sdk.service.utxos import get_utxo_from_str
from sdk.metagraph.hash.hash_datum import hash_data
from sdk.config.settings import logger

# Fixture to provide the blockchain context
@pytest.fixture(scope="session")
def chain_context_fixture():
    """
    Creates a chain context, specifically a BlockFrostChainContext in TESTNET mode,
    for use throughout the test session.

    Steps:
        1) Reads the BLOCKFROST_PROJECT_ID from environment or settings (if available).
        2) Calls get_chain_context() with method="blockfrost".
        3) Returns the resulting chain context for injection into test functions.

    Returns:
        BlockFrostChainContext: A chain context configured for Cardano TESTNET via Blockfrost.
    """
    # Optionally, uncomment to use a specific project ID from settings:
    # project_id = settings.BLOCKFROST_PROJECT_ID
    # return get_chain_context(method="blockfrost", project_id=project_id, network=Network.TESTNET)
    return get_chain_context(method="blockfrost")

# Fixture to create a mock UTxO with an initial datum
@pytest.fixture
def mock_utxo(chain_context_fixture):
    """
    Creates a mock UTxO with an initial datum for testing.

    Steps:
        1) Loads the validator script hash from the Plutus script.
        2) Constructs the contract address using the script hash.
        3) Retrieves a UTxO from the contract address using get_utxo_from_str.
        4) Prints the UTxO for debugging purposes.
        5) Returns the UTxO.

    Args:
        chain_context_fixture (BlockFrostChainContext): The blockchain context fixture.

    Returns:
        UTxO: A UTxO from the contract address with an initial datum.
    """
    validator = read_validator()
    script_hash = validator["script_hash"]  # Script hash of the Plutus contract
    contract_address = Address(
        payment_part=script_hash,
        network=Network.TESTNET,
    )
    utxo = get_utxo_from_str(
        contract_address=contract_address,
        datumclass=MinerDatum,
        context=chain_context_fixture,
    )
    print(utxo)
    return utxo

# Fixture to provide sample miner data
@pytest.fixture
def miner_data():
    """
    Provides sample data for a miner.

    Returns:
        dict: A dictionary containing sample miner data, including UID, stake, performance,
              trust score, accumulated rewards, evaluation history, wallet address, status,
              and registration block.
    """
    return {
        "uid": "miner_001",
        "stake": 500,
        "performance": 90,
        "trust_score": 85,
        "accumulated_rewards": 200,
        "last_evaluated": 100000,
        "history": [75, 85, 90],  # Historical performance data to be hashed
        "wallet_addr": "addr_test1xyz",  # Wallet address to be hashed
        "status": "active",
        "block_reg_at": 50000,
    }

# Fixture to create a new MinerDatum object for updating
@pytest.fixture
def new_datum(miner_data):
    """
    Creates a new MinerDatum object with hashed fields for updating.

    Steps:
        1) Hashes the 'history' and 'wallet_addr' fields using hash_data.
        2) Encodes string fields (uid and status) to bytes.
        3) Constructs and returns a new MinerDatum object with the processed data.

    Args:
        miner_data (dict): The sample miner data.

    Returns:
        MinerDatum: A new instance of MinerDatum with hashed and encoded fields.
    """
    history_hash = hash_data(miner_data["history"])  # Hash of historical data
    wallet_addr_hash = hash_data(miner_data["wallet_addr"])  # Hash of wallet address
    return MinerDatum(
        uid=miner_data["uid"].encode() if isinstance(miner_data["uid"], str) else miner_data["uid"],
        stake=miner_data["stake"],
        performance=miner_data["performance"],
        trust_score=miner_data["trust_score"],
        accumulated_rewards=miner_data["accumulated_rewards"],
        last_evaluated=miner_data["last_evaluated"],
        history_hash=history_hash,
        wallet_addr_hash=wallet_addr_hash,
        status=miner_data["status"].encode() if isinstance(miner_data["status"], str) else miner_data["status"],
        block_reg_at=miner_data["block_reg_at"],
    )

# Main test function to verify update_datum
@pytest.mark.integration
def test_update_datum(chain_context_fixture, mock_utxo, new_datum, hotkey_skey_fixture):
    """
    Tests the update_datum function in update_metagraph.py.

    This test verifies that the update_datum function successfully updates the datum of a UTxO
    locked in a Plutus smart contract. It checks that the transaction ID is returned and is a
    non-empty string.

    Args:
        chain_context_fixture (BlockFrostChainContext): The blockchain context fixture.
        mock_utxo (UTxO): The mock UTxO fixture.
        new_datum (MinerDatum): The new MinerDatum fixture for updating.
        hotkey_skey_fixture (tuple): The signing keys fixture (payment_xsk, stake_xsk).

    Asserts:
        - The transaction ID is not None.
        - The transaction ID is a non-empty string.
    """
    # Unpack signing keys from fixture
    payment_xsk, stake_xsk = hotkey_skey_fixture

    # Set network to TESTNET
    network = Network.TESTNET

    # Load validator details
    validator = read_validator()
    script = validator["script_bytes"]  # Plutus script bytes
    script_hash = validator["script_hash"]  # Script hash of the Plutus contract

    # Log signing keys for debugging
    print(f"Payment Signing Key: {payment_xsk}")
    print(f"Stake Signing Key: {stake_xsk}")

    # Call the update_datum function to update the UTxO's datum
    tx_id = update_datum(
        payment_xsk=payment_xsk,
        stake_xsk=stake_xsk,
        into=script_hash,
        utxo=mock_utxo,
        script=script,
        new_datum=new_datum,
        context=chain_context_fixture,
        network=network,
    )

    # Verify the transaction ID
    assert tx_id is not None, "Transaction ID should not be None"
    logger.info(f"Transaction ID: {tx_id}")
    assert len(tx_id) > 0, "Transaction ID should be a non-empty string"