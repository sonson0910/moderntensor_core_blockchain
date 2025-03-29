import pytest
from pycardano import TransactionId, Network, BlockFrostChainContext
from sdk.metagraph.metagraph_datum import MinerDatum
from sdk.metagraph.hash.hash_datum import hash_data
from sdk.metagraph.hash.verify_hash import verify_hash
from sdk.metagraph.create_utxo import create_utxo
from sdk.service.context import get_chain_context
from sdk.smartcontract.validator import read_validator
from sdk.config.settings import settings, logger

# Fixture to provide the blockchain context
@pytest.fixture(scope="session")
def chain_context_fixture():
    """
    Creates a chain context, specifically a BlockFrostChainContext in TESTNET mode,
    for use throughout the test session.

    Steps:
      1) Reads the BLOCKFROST_PROJECT_ID from environment or settings (if implemented).
      2) Calls get_chain_context() with method="blockfrost".
      3) Returns the resulting chain context, which can be injected into test functions.

    Returns:
        BlockFrostChainContext: A chain context configured for Cardano TESTNET via Blockfrost.
    """
    # Uncomment the lines below to use a specific project_id from settings
    # project_id = settings.BLOCKFROST_PROJECT_ID
    # return get_chain_context(method="blockfrost", project_id=project_id, network=Network.TESTNET)
    return get_chain_context(method="blockfrost")

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
        "history": [80, 85, 90],  # Historical performance data to be hashed
        "wallet_addr": "addr_test1xyz",  # Wallet address to be hashed
        "status": "active",
        "block_reg_at": 50000,
    }

# Fixture to create a MinerDatum object from miner data
@pytest.fixture
def miner_datum(miner_data):
    """
    Creates a MinerDatum object with hashed fields from the provided miner data.

    Steps:
      1) Hashes the 'history' and 'wallet_addr' fields using hash_data.
      2) Encodes string fields (uid and status) to bytes.
      3) Constructs and returns a MinerDatum object with the processed data.

    Args:
        miner_data (dict): The sample miner data.

    Returns:
        MinerDatum: An instance of MinerDatum with hashed and encoded fields.
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

# Main test function to verify create_utxo
@pytest.mark.integration
def test_create_utxo(chain_context_fixture, miner_datum, miner_data, hotkey_skey_fixture):
    """
    Tests the create_utxo function by creating a UTxO with a MinerDatum.

    This test verifies that the create_utxo function successfully creates a UTxO locked in a Plutus
    smart contract with the provided MinerDatum. It checks that the transaction ID is returned and
    is a non-empty string.

    Args:
        chain_context_fixture (BlockFrostChainContext): The blockchain context fixture.
        miner_datum (MinerDatum): The MinerDatum fixture.
        miner_data (dict): The sample miner data fixture.
        hotkey_skey_fixture (tuple): The signing keys fixture (payment_xsk, stake_xsk).

    Asserts:
        - The transaction ID is not None.
        - The transaction ID is a non-empty string.
    """
    # Load the validator details from the Plutus script
    validator = read_validator()

    # Sample parameters for creating the UTxO
    amount = 2_000_000  # 2 tADA (test ADA)
    script_hash = validator["script_hash"]  # Hash of the Plutus script
    network = Network.TESTNET
    payment_xsk, stake_xsk = hotkey_skey_fixture

    # Call the create_utxo function to create the UTxO
    tx_id = create_utxo(
        payment_xsk=payment_xsk,
        stake_xsk=stake_xsk,
        amount=amount,
        script_hash=script_hash,
        datum=miner_datum,
        context=chain_context_fixture,
        network=network,
    )

    # Verify the transaction ID
    assert tx_id is not None, "Transaction ID should not be None"
    logger.info(f"Transaction ID: {tx_id}")
    assert isinstance(tx_id, TransactionId), "Transaction ID should be of type TransactionId"
    assert len(tx_id) > 0, "Transaction ID should be a non-empty string"

    # Optional: Verify hash integrity (uncomment to enable)
    # assert verify_hash(miner_data["history"], miner_datum.history_hash), "History hash does not match"
    # assert verify_hash(miner_data["wallet_addr"], miner_datum.wallet_addr_hash), "Wallet address hash does not match"