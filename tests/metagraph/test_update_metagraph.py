import pytest
from pycardano import TransactionId, Network, BlockFrostChainContext, UTxO, TransactionInput, TransactionOutput, Address, Value
from sdk.metagraph.update_metagraph import update_datum      # Giả định service của bạn
from sdk.metagraph.metagraph_datum import MinerDatum  # Lớp MinerDatum từ file metagraph_datum.py
from sdk.service.context import get_chain_context
from sdk.smartcontract.validator import read_validator
from sdk.service.utxos import get_utxo_from_str


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
    return utxo

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
def test_update_datum(chain_context_fixture, mock_utxo, new_datum, hotkey_skey_fixture):
    """
    Kiểm thử hàm update_datum trong update_metagraph.py.
    Đầu vào: chain_context, mock_utxo (UTxO giả lập), new_datum (datum mới).
    """
    # Tham số mẫu (thay bằng giá trị thực tế khi chạy)
    (payment_xsk, stake_xsk) = hotkey_skey_fixture
    network = Network.TESTNET
    validator=read_validator()
    script_hash = validator["script_hash"]  # Thay bằng hash của hợp đồng Plutus

    # Gọi hàm update_datum
    tx_id = update_datum(
        payment_xsk=payment_xsk,
        stake_xsk=stake_xsk,
        utxo=mock_utxo,
        script_hash=script_hash,
        new_datum=new_datum,
        context=chain_context_fixture,
        network=network
    )

    # Kiểm tra kết quả
    assert tx_id is not None, "Transaction ID không được rỗng"
    assert isinstance(tx_id, TransactionId), "Transaction ID không hợp lệ"