import pytest
from pycardano import (
    Address,
    Network,
    Redeemer,
)
from sdk.service.context import get_chain_context
from sdk.smartcontract.validator import read_validator
from sdk.service.register_key import register_key
from sdk.metagraph.metagraph_datum import MinerDatum  # Giả sử đây là lớp datum của bạn

# Định nghĩa mạng (sử dụng testnet để tránh ảnh hưởng đến mainnet)

# Fixture cho chain context thực tế
@pytest.fixture(scope="session")
def chain_context():
    """Cung cấp kết nối thực tế đến blockchain Cardano qua BlockFrost."""
    return get_chain_context(method="blockfrost")

# Fixture cho chain context thực tế
@pytest.fixture(scope="session")
def get_network():
    """Cung cấp kết nối thực tế đến blockchain Cardano qua BlockFrost."""
    return Network.TESTNET

# Fixture cho script Plutus
@pytest.fixture
def script():
    """Cung cấp script Plutus thực tế từ validator."""
    validator = read_validator()
    return validator["script_bytes"]

# Fixture cho script Plutus
@pytest.fixture
def script_hash():
    """Cung cấp script hash thực tế từ validator."""
    validator = read_validator()
    return validator["script_hash"]

# Fixture cho địa chỉ hợp đồng
@pytest.fixture
def contract_address(get_network):
    """Tạo địa chỉ hợp đồng thực tế từ script hash."""
    validator = read_validator()
    script_hash = validator["script_hash"]
    return Address(payment_part=script_hash, network=get_network)

# Fixture cho dữ liệu mới (new_datum)
@pytest.fixture
def new_datum():
    """
    Cung cấp dữ liệu mới để cập nhật UTxO.
    Điều chỉnh theo cấu trúc datum của hợp đồng.
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

# Test hàm register_new_key_service với UTxO thực tế
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
    Kiểm tra hàm register_new_key_service với hợp đồng và UTxO thực tế.
    
    Các bước:
    1. Lấy payment_xsk và stake_xsk thực tế.
    2. Gọi hàm với redeemer đơn giản (Redeemer(0)).
    3. Kiểm tra transaction ID trả về.
    
    Kết quả mong đợi:
    - Transaction ID không rỗng.
    """
    payment_xsk, stake_xsk = hotkey_skey_fixture

    # Gọi hàm register_new_key_service
    tx_id = register_key(
        payment_xsk=payment_xsk,
        stake_xsk=stake_xsk,
        script_hash=script_hash,
        new_datum=new_datum,
        script=script,
        context=chain_context,
        network=get_network,
        contract_address=contract_address,
        redeemer=Redeemer(0),  # Điều chỉnh nếu script yêu cầu redeemer khác
    )

    # Kiểm tra kết quả
    assert tx_id is not None, "Transaction ID không được là None"
    assert len(tx_id) > 0, "Transaction ID phải là chuỗi không rỗng"

    # In transaction ID để kiểm tra thủ công
    print(f"Transaction ID: {tx_id}")