import pytest
from pycardano import TransactionId, Network, BlockFrostChainContext, UTxO, TransactionInput, TransactionOutput, Address, Value
from update_metagraph import update_datum  # Import hàm từ file update_metagraph.py
from your_project.metagraph_datum import MinerDatum  # Giả định lớp datum của bạn

# Fixture cung cấp chain context
@pytest.fixture
def chain_context():
    """Tạo ngữ cảnh chuỗi blockchain cho testnet."""
    api_key = "your_blockfrost_api_key"  # Thay bằng API key thực tế của bạn
    return BlockFrostChainContext(api_key, Network.TESTNET)

# Fixture tạo UTxO giả lập
@pytest.fixture
def mock_utxo():
    """Tạo một UTxO giả lập với datum ban đầu."""
    # Tạo datum ban đầu
    initial_datum = MinerDatum(
        uid="miner_001",
        stake=500,
        performance=90.0,
        trust_score=0.85,
        accumulated_rewards=200,
        last_evaluated=100000,
        history_hash=b'fake_history_hash',
        wallet_addr_hash=b'fake_wallet_hash',
        status="active",
        block_reg_at=50000
    )
    # Giả lập địa chỉ hợp đồng
    contract_address = Address.from_primitive("your_contract_address")  # Thay bằng địa chỉ thực
    # Tạo TransactionInput và TransactionOutput
    tx_input = TransactionInput.from_primitive(["fake_tx_hash", 0])
    tx_output = TransactionOutput(
        address=contract_address,
        amount=Value(2_000_000),  # 2 tADA
        datum=initial_datum
    )
    return UTxO(input=tx_input, output=tx_output)

# Fixture tạo datum mới
@pytest.fixture
def new_datum():
    """Tạo datum mới để cập nhật."""
    return MinerDatum(
        uid="miner_001",
        stake=500,
        performance=95.0,  # Giá trị mới
        trust_score=0.9,   # Giá trị mới
        accumulated_rewards=200,
        last_evaluated=100000,
        history_hash=b'fake_history_hash',
        wallet_addr_hash=b'fake_wallet_hash',
        status="active",
        block_reg_at=50000
    )

# Hàm kiểm thử chính
def test_update_datum(chain_context, mock_utxo, new_datum):
    """
    Kiểm thử hàm update_datum trong update_metagraph.py.
    Đầu vào: chain_context, mock_utxo (UTxO giả lập), new_datum (datum mới).
    """
    # Tham số mẫu (thay bằng giá trị thực tế khi chạy)
    signing_key = "your_signing_key"  # Thay bằng khóa ký thực tế
    owner_address = "your_owner_address"  # Thay bằng địa chỉ ví thực tế

    # Gọi hàm update_datum
    tx_id = update_datum(
        utxo=mock_utxo,
        new_datum=new_datum,
        signing_key=signing_key,
        owner_address=owner_address
    )

    # Kiểm tra kết quả
    assert tx_id is not None, "Transaction ID không được rỗng"
    assert isinstance(tx_id, TransactionId), "Transaction ID không hợp lệ"