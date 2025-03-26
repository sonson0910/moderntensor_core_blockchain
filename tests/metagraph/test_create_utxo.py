import pytest
from pycardano import TransactionId, Network, BlockFrostChainContext
from sdk.metagraph.metagraph_datum import MinerDatum  # Lớp MinerDatum từ file metagraph_datum.py
from sdk.metagraph.hash.hash_datum import hash_data    # Hàm hash từ hash_datum.py
from sdk.metagraph.hash.verify_datum import verify_hash  # Hàm kiểm tra hash từ verify_datum.py
from your_project.utxo_service import create_utxo      # Giả định service của bạn

# Fixture cung cấp chain context
@pytest.fixture
def chain_context():
    """Tạo ngữ cảnh chuỗi blockchain cho testnet."""
    return BlockFrostChainContext("your_blockfrost_api_key", Network.TESTNET)

# Fixture cung cấp dữ liệu miner mẫu
@pytest.fixture
def miner_data():
    """Dữ liệu mẫu cho miner."""
    return {
        "uid": "miner_001",
        "stake": 500,
        "performance": 90.0,
        "trust_score": 0.85,
        "accumulated_rewards": 200,
        "last_evaluated": 100000,
        "history": [0.8, 0.85, 0.9],  # Dữ liệu lịch sử cần hash
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
        uid=miner_data["uid"],
        stake=miner_data["stake"],
        performance=miner_data["performance"],
        trust_score=miner_data["trust_score"],
        accumulated_rewards=miner_data["accumulated_rewards"],
        last_evaluated=miner_data["last_evaluated"],
        history_hash=history_hash,
        wallet_addr_hash=wallet_addr_hash,
        status=miner_data["status"],
        block_reg_at=miner_data["block_reg_at"]
    )

# Hàm kiểm thử chính
def test_create_utxo(chain_context, miner_datum, miner_data):
    """
    Kiểm thử service sinh UTxO với MinerDatum.
    Tham số: chain_context, miner_datum, miner_data (dữ liệu gốc để kiểm tra hash).
    """
    # Tham số mẫu cho việc tạo UTxO (bạn cần thay thế bằng giá trị thực tế khi chạy)
    amount = 2_000_000  # 2 tADA
    signing_key = "your_signing_key"  # Thay bằng khóa ký thực tế
    owner_address = "your_owner_address"  # Thay bằng địa chỉ ví thực tế
    script_hash = "your_script_hash"  # Thay bằng hash của hợp đồng Plutus

    # Gọi service để tạo UTxO
    tx_id = create_utxo(
        amount=amount,
        script_hash=script_hash,
        datum=miner_datum,
        signing_key=signing_key,
        owner_address=owner_address,
        context=chain_context
    )

    # Kiểm tra TransactionId
    assert tx_id is not None, "Transaction ID không được rỗng"
    assert isinstance(tx_id, TransactionId), "Transaction ID không hợp lệ"

    # Kiểm tra tính toàn vẹn của hash trong datum
    assert verify_hash(miner_data["history"], miner_datum.history_hash), "Hash của history không khớp"
    assert verify_hash(miner_data["wallet_addr"], miner_datum.wallet_addr_hash), "Hash của wallet_addr không khớp"

    # (Tùy chọn) Nếu bạn có thể truy xuất UTxO từ blockchain, thêm kiểm tra ở đây
    # Ví dụ:
    # utxos = chain_context.utxos(owner_address)
    # assert len(utxos) > 0, "Không tìm thấy UTxO"