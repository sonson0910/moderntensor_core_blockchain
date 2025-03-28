import pytest
from pycardano import TransactionId, Network, BlockFrostChainContext, UTxO, TransactionInput, TransactionOutput, Address, Value
from sdk.metagraph.update_metagraph import update_datum      # Giả định service của bạn
from sdk.metagraph.metagraph_datum import MinerDatum  # Lớp MinerDatum từ file metagraph_datum.py
from sdk.service.context import get_chain_context
from sdk.smartcontract.validator import read_validator
from sdk.service.utxos import get_utxo_from_str
from sdk.metagraph.hash.hash_datum import hash_data    # Hàm hash từ hash_datum.py
from sdk.metagraph.hash.verify_hash import verify_hash  # Hàm kiểm tra hash từ verify_datum.py
from sdk.config.settings import settings, logger  # Use the global logger & settings



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
    # If you want to pass in a specific project_id, you can read from settings:
    # project_id = settings.BLOCKFROST_PROJECT_ID
    # return get_chain_context(method="blockfrost", project_id=project_id, network=Network.TESTNET)
    return get_chain_context(method="blockfrost")

# Fixture tạo UTxO giả lập
@pytest.fixture
def mock_utxo(chain_context_fixture):
    """Tạo một UTxO giả lập với datum ban đầu."""
    validator=read_validator()
    script_hash = validator["script_hash"]  # Thay bằng hash của hợp đồng Plutus
    contract_address = Address(
        payment_part = script_hash,
        network=Network.TESTNET,
    )
    utxo=get_utxo_from_str(contract_address=contract_address, datumclass=MinerDatum, context=chain_context_fixture)
    print(utxo)
    return utxo

# Fixture cung cấp dữ liệu miner mẫu
@pytest.fixture
def miner_data():
    """Dữ liệu mẫu cho miner."""
    return {
        "uid": "miner_001",
        "stake": 500,
        "performance": 90,
        "trust_score": 85,
        "accumulated_rewards": 200,
        "last_evaluated": 100000,
        "history": [75, 85, 90],  # Dữ liệu lịch sử cần hash
        "wallet_addr": "addr_test1xyz",  # Địa chỉ ví cần hash
        "status": "active",
        "block_reg_at": 50000
    }

# Fixture tạo datum mới
@pytest.fixture
def new_datum(miner_data):
    """Tạo datum mới để cập nhật."""
    """Tạo MinerDatum với các hash từ dữ liệu miner."""
    history_hash = hash_data(miner_data["history"])  # Hash lịch sử
    wallet_addr_hash = hash_data(miner_data["wallet_addr"])  # Hash địa chỉ ví
    return MinerDatum(
        uid=miner_data["uid"].encode() if isinstance(miner_data["uid"], str) else miner_data["uid"],  # uid (bytes)
        stake=miner_data["stake"],
        performance=miner_data["performance"],  # Là int
        trust_score=miner_data["trust_score"],  # Là int
        accumulated_rewards=miner_data["accumulated_rewards"],
        last_evaluated=miner_data["last_evaluated"],
        history_hash=history_hash,
        wallet_addr_hash=wallet_addr_hash,
        status=miner_data["status"].encode() if isinstance(miner_data["status"], str) else miner_data["status"],  # status (bytes)
        block_reg_at=miner_data["block_reg_at"]
    )

# Hàm kiểm thử chính
@pytest.mark.integration
def test_update_datum(chain_context_fixture, mock_utxo, new_datum, hotkey_skey_fixture):
    """
    Kiểm thử hàm update_datum trong update_metagraph.py.
    Đầu vào: chain_context, mock_utxo (UTxO giả lập), new_datum (datum mới).
    """
    # Tham số mẫu (thay bằng giá trị thực tế khi chạy)
    (payment_xsk, stake_xsk) = hotkey_skey_fixture
    network = Network.TESTNET
    validator=read_validator()
    script = validator["script_bytes"]  # Thay bằng hash của hợp đồng Plutus
    script_hash = validator["script_hash"]  # Thay bằng hash của hợp đồng Plutus

    print("payment_xsk " + str(payment_xsk))
    print("stake_xsk " + str(stake_xsk))
    # Gọi hàm update_datum
    tx_id = update_datum(
        payment_xsk=payment_xsk,
        stake_xsk=stake_xsk,
        into=script_hash,
        utxo=mock_utxo,
        script=script,
        new_datum=new_datum,
        context=chain_context_fixture,
        network=network
    )

    # Kiểm tra kết quả
    assert tx_id is not None, "Transaction ID không được rỗng"
    logger.info(f"send_ada => {tx_id}")
    assert len(tx_id) > 0, "Transaction ID should be a non-empty string upon success."