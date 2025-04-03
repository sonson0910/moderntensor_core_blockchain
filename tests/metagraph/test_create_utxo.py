# tests/metagraph/test_create_utxo.py
import pytest
from pycardano import TransactionId, Network, BlockFrostChainContext

# Import các thành phần đã cập nhật
from sdk.metagraph.metagraph_datum import MinerDatum, STATUS_ACTIVE # Import STATUS_* nếu cần
from sdk.metagraph.hash.hash_datum import hash_data
from sdk.metagraph.hash.verify_hash import verify_hash
from sdk.metagraph.create_utxo import create_utxo
from sdk.service.context import get_chain_context
from sdk.smartcontract.validator import read_validator
from sdk.config.settings import settings, logger # Import settings

# Fixture để cung cấp context (giữ nguyên)
@pytest.fixture(scope="session")
def chain_context_fixture():
    """Provides a BlockFrostChainContext for the test session."""
    # Sử dụng project_id từ settings nếu được cấu hình
    # project_id = settings.BLOCKFROST_PROJECT_ID
    # return get_chain_context(method="blockfrost", project_id=project_id, network=settings.CARDANO_NETWORK)
    # Hoặc dùng default nếu settings không có hoặc dùng cho testnet mặc định
    try:
        # Cố gắng lấy network từ settings đã được validate
        network = settings.CARDANO_NETWORK
    except AttributeError:
        network = Network.TESTNET # Mặc định nếu settings load lỗi
    return get_chain_context(method="blockfrost")

# Fixture cung cấp dữ liệu miner mẫu (cập nhật theo cấu trúc mới)
@pytest.fixture
def miner_data():
    """Provides sample raw data for a miner, updated for new fields."""
    return {
        "uid": "miner_test_001",
        "subnet_uid": 1, # <<<--- Trường mới
        "stake": 600_000_000, # Ví dụ: 600 ADA (lovelace)
        "last_performance": 0.95, # <<<--- Tên mới (giá trị float gốc)
        "trust_score": 0.88, # <<<--- Giá trị float gốc
        "accumulated_rewards": 250_000_000, # Ví dụ: 250 ADA
        "last_update_slot": 110000, # <<<--- Tên mới
        "history": [0.80, 0.85, 0.95], # Dữ liệu gốc để hash
        "wallet_addr": "addr_test1qzkxr3kpzex93m646qr7w82d56md2kchtsv9jy39dykn4cmcxuuneyeqhdc4wy7de9mk54fndmckahxwqtwy3qg8pumsabcde", # Địa chỉ ví gốc để hash
        "status": STATUS_ACTIVE, # <<<--- Dùng hằng số int
        "registration_slot": 55000, # <<<--- Tên mới
        "api_endpoint": "http://miner2.example.com:9000", # <<<--- Trường mới
    }

# Fixture tạo đối tượng MinerDatum (cập nhật theo cấu trúc mới)
@pytest.fixture
def miner_datum(miner_data):
    """
    Creates an updated MinerDatum object with scaled, hashed, and encoded fields.
    """
    # Lấy hệ số scale từ settings
    divisor = settings.METAGRAPH_DATUM_INT_DIVISOR

    # Hash các trường cần thiết
    history_hash = hash_data(miner_data["history"])
    wallet_addr_hash = hash_data(miner_data["wallet_addr"])

    # Encode các trường bytes/Optional[bytes]
    uid_bytes = miner_data["uid"].encode('utf-8')
    api_endpoint_bytes = miner_data["api_endpoint"].encode('utf-8') if miner_data["api_endpoint"] else None

    # Tạo đối tượng MinerDatum với các trường đã cập nhật và scale
    return MinerDatum(
        uid=uid_bytes,
        subnet_uid=miner_data["subnet_uid"],
        stake=miner_data["stake"],
        # Scale các giá trị float thành int
        scaled_last_performance=int(miner_data["last_performance"] * divisor),
        scaled_trust_score=int(miner_data["trust_score"] * divisor),
        accumulated_rewards=miner_data["accumulated_rewards"],
        last_update_slot=miner_data["last_update_slot"],
        performance_history_hash=history_hash,
        wallet_addr_hash=wallet_addr_hash,
        status=miner_data["status"], # Đã là int
        registration_slot=miner_data["registration_slot"],
        api_endpoint=api_endpoint_bytes,
    )

# Hàm test chính (giữ nguyên logic gọi create_utxo)
@pytest.mark.integration
def test_create_utxo(chain_context_fixture, miner_datum, miner_data, hotkey_skey_fixture):
    """
    Tests the create_utxo function by creating a UTxO with the updated MinerDatum.

    Verifies successful UTxO creation with the new datum structure.
    """
    # Load validator script details
    validator = read_validator()
    if not validator:
        pytest.fail("Failed to load validator script details.")

    # Parameters for UTxO creation
    amount = 2_000_000  # 2 ADA (lovelace) - Đảm bảo đủ ADA tối thiểu cho UTXO + Datum
    script_hash = validator["script_hash"]
    network = Network.TESTNET # Lấy network từ settings
    payment_xsk, stake_xsk = hotkey_skey_fixture

    logger.info(f"Attempting to create UTxO at script {script_hash} on {network}...")
    logger.info(f"Using Datum: {miner_datum}")

    # Call the function under test
    try:
        tx_id_obj = create_utxo( # Giả sử create_utxo trả về TransactionId object
            payment_xsk=payment_xsk,
            stake_xsk=stake_xsk, # Có thể là None nếu không dùng stake key
            amount=amount,
            script_hash=script_hash,
            datum=miner_datum, # Sử dụng miner_datum đã cập nhật
            context=chain_context_fixture,
            network=network,
        )
    except Exception as e:
        logger.exception(f"create_utxo failed with exception: {e}")
        pytest.fail(f"create_utxo raised an exception: {e}")

    # Verify the result (TransactionId object)
    assert tx_id_obj is not None, "Transaction ID object should not be None"
    # assert isinstance(tx_id_obj, TransactionId), f"Expected TransactionId, got {type(tx_id_obj)}"

    tx_id_hex = str(tx_id_obj) # Chuyển sang hex string để kiểm tra độ dài
    logger.info(f"UTxO creation successful. Transaction ID: {tx_id_hex}")
    assert len(tx_id_hex) == 64, "Transaction ID hex should be 64 characters long" # Độ dài chuẩn của Tx Hash

    # Optional: Verify hash integrity (uncomment to enable)
    # logger.info("Verifying data hashes...")
    # assert verify_hash(miner_data["history"], miner_datum.performance_history_hash), "History hash does not match"
    # assert verify_hash(miner_data["wallet_addr"], miner_datum.wallet_addr_hash), "Wallet address hash does not match"
    # logger.info("Data hashes verified successfully.")

