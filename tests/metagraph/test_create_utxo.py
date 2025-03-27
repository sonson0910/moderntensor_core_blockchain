import pytest
from pycardano import TransactionId, Network, BlockFrostChainContext
from sdk.metagraph.metagraph_datum import MinerDatum  # Lớp MinerDatum từ file metagraph_datum.py
from sdk.metagraph.hash.hash_datum import hash_data    # Hàm hash từ hash_datum.py
from sdk.metagraph.hash.verify_hash import verify_hash  # Hàm kiểm tra hash từ verify_datum.py
from sdk.metagraph.create_utxo import create_utxo      # Giả định service của bạn
from sdk.service.context import get_chain_context
from sdk.smartcontract.validator import read_validator
from sdk.config.settings import settings, logger  # Use the global logger & settings


# Fixture cung cấp chain context
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
        "history": [80, 85, 90],  # Dữ liệu lịch sử cần hash
        "wallet_addr": "addr_test1xyz",  # Địa chỉ ví cần hash
        "status": "active",
        "block_reg_at": 50000
    }

# Fixture tạo datum từ dữ liệu miner
@pytest.fixture
def miner_datum(miner_data):
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
def test_create_utxo(chain_context_fixture, miner_datum, miner_data, hotkey_skey_fixture):
    """
    Kiểm thử service sinh UTxO với MinerDatum.
    Tham số: chain_context, miner_datum, miner_data (dữ liệu gốc để kiểm tra hash).
    """
    validator = read_validator()

    # Tham số mẫu cho việc tạo UTxO (bạn cần thay thế bằng giá trị thực tế khi chạy)
    amount = 2_000_000  # 2 tADA
    script_hash = validator["script_hash"]  # Thay bằng hash của hợp đồng Plutus
    network = Network.TESTNET
    (payment_xsk, stake_xsk) = hotkey_skey_fixture
    # Gọi service để tạo UTxO
    tx_id = create_utxo(
        payment_xsk=payment_xsk,
        stake_xsk=stake_xsk,
        amount=amount,
        script_hash=script_hash,
        datum=miner_datum,
        context=chain_context_fixture,
        network=network
    )

    # Kiểm tra TransactionId
    assert tx_id is not None, "Transaction ID không được rỗng"
    logger.info(f"send_ada => {tx_id}")
    assert len(tx_id) > 0, "Transaction ID should be a non-empty string upon success."

    # # Kiểm tra tính toàn vẹn của hash trong datum
    # assert verify_hash(miner_data["history"], miner_datum.history_hash), "Hash của history không khớp"
    # assert verify_hash(miner_data["wallet_addr"], miner_datum.wallet_addr_hash), "Hash của wallet_addr không khớp"

    # # (Tùy chọn) Nếu bạn có thể truy xuất UTxO từ blockchain, thêm kiểm tra ở đây
    # # Ví dụ:
    # # utxos = chain_context.utxos(owner_address)
    # # assert len(utxos) > 0, "Không tìm thấy UTxO"