# sdk/config/settings.py

import logging
import math
import os
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pycardano import Network


class Settings(BaseSettings):
    """
    Quản lý cấu hình tập trung cho dự án, load từ biến môi trường hoặc file .env.
    Đã cập nhật để bao gồm các tham số và hằng số cho module đồng thuận.
    """

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix='MODERNTENSOR_' # Giữ nguyên tiền tố (hoặc bỏ nếu không muốn)
    )

    # --- Các trường cấu hình gốc của bạn ---
    BLOCKFROST_PROJECT_ID: str = Field(default="preprod06dzhzKlynuTInzvxHDH5cXbdHo524DE", alias="BLOCKFROST_PROJECT_ID")
    HOTKEY_BASE_DIR: str = Field(default="moderntensor", alias="HOTKEY_BASE_DIR")
    COLDKEY_NAME: str = Field(default="kickoff", alias="COLDKEY_NAME")
    HOTKEY_NAME: str = Field(default="hk1", alias="HOTKEY_NAME")
    HOTKEY_PASSWORD: str = Field(default="sonlearn2003", alias="HOTKEY_PASSWORD")
    TEST_RECEIVER_ADDRESS: str = Field(default="addr_test1qpkxr3kpzex93m646qr7w82d56md2kchtsv9jy39dykn4cmcxuuneyeqhdc4wy7de9mk54fndmckahxwqtwy3qg8pums5vlxhz", alias="TEST_RECEIVER_ADDRESS")
    TEST_POLICY_ID_HEX: str = Field(default="b9107b627e28700da1c5c2077c40b1c7d1fe2e9b23ff20e0e6b8fec1", alias="TEST_POLICY_ID_HEX")
    TEST_CONTRACT_ADDRESS: str = Field(default="addr_test1wqlerxnfzfcgx72zpuepgchl6p5mnjsxm27cwjxqq9wuthch489d5", alias="TEST_CONTRACT_ADDRESS")
    CARDANO_NETWORK: str = Field(default="TESTNET", alias="CARDANO_NETWORK")

    # --- Thêm các trường cấu hình Node (Ví dụ) ---
    API_PORT: int = Field(8000, alias="API_PORT", description="Port cho FastAPI server")
    VALIDATOR_UID: Optional[str] = Field(None, alias="VALIDATOR_UID", description="UID của validator này (nếu chạy node)")
    VALIDATOR_ADDRESS: Optional[str] = Field(None, alias="VALIDATOR_ADDRESS", description="Địa chỉ Cardano của validator này")
    VALIDATOR_API_ENDPOINT: Optional[str] = Field(None, alias="VALIDATOR_API_ENDPOINT", description="Địa chỉ API đầy đủ mà các node khác có thể gọi đến validator này")

    # --- Cấu hình Đồng thuận (Consensus) - Tham số & Hằng số ---

    # Hằng số Chu kỳ & Thời gian
    CONSENSUS_METAGRAPH_UPDATE_INTERVAL_MINUTES: int = Field(60, alias="CONSENSUS_METAGRAPH_UPDATE_INTERVAL_MINUTES", description="Khoảng thời gian (phút) giữa các lần cập nhật metagraph")
    CONSENSUS_SEND_SCORE_OFFSET_MINUTES: int = Field(2, alias="CONSENSUS_SEND_SCORE_OFFSET_MINUTES", description="Gửi điểm số trước thời điểm cập nhật metagraph bao nhiêu phút")
    CONSENSUS_CONSENSUS_TIMEOUT_OFFSET_MINUTES: int = Field(1, alias="CONSENSUS_CONSENSUS_TIMEOUT_OFFSET_MINUTES", description="Timeout chờ điểm đồng thuận trước thời điểm cập nhật metagraph bao nhiêu phút")
    CONSENSUS_COMMIT_OFFSET_SECONDS: int = Field(15, alias="CONSENSUS_COMMIT_OFFSET_SECONDS", description="Commit lên blockchain trước thời điểm cập nhật metagraph bao nhiêu giây")
    CONSENSUS_CYCLE_MIN_WAIT_SECONDS: int = Field(10, alias="CONSENSUS_CYCLE_MIN_WAIT_SECONDS", description="Thời gian chờ tối thiểu giữa các chu kỳ (giây)")
    CONSENSUS_NETWORK_TIMEOUT_SECONDS: int = Field(10, alias="CONSENSUS_NETWORK_TIMEOUT_SECONDS", description="Timeout cho các yêu cầu mạng P2P (giây)")

    # Hằng số Cấu trúc & Giới hạn
    CONSENSUS_MAX_PERFORMANCE_HISTORY_LEN: int = Field(100, alias="CONSENSUS_MAX_PERFORMANCE_HISTORY_LEN", description="Độ dài tối đa của lịch sử hiệu suất lưu trữ")
    METAGRAPH_DATUM_INT_DIVISOR: float = Field(1_000_000.0, alias="METAGRAPH_DATUM_INT_DIVISOR", description="Hệ số scale khi lưu float thành int trong Datum") # <<<--- Di chuyển vào đây

    # Tham số Thuật toán (Nên cho phép DAO quản trị)
    CONSENSUS_NUM_MINERS_TO_SELECT: int = Field(5, alias="CONSENSUS_NUM_MINERS_TO_SELECT", description="Số lượng miner mỗi validator chọn trong một chu kỳ")
    CONSENSUS_MIN_VALIDATORS_FOR_CONSENSUS: int = Field(3, alias="CONSENSUS_MIN_VALIDATORS_FOR_CONSENSUS", description="Số validator tối thiểu cần gửi điểm để chạy đồng thuận")
    CONSENSUS_PARAM_BETA: float = Field(0.2, alias="CONSENSUS_PARAM_BETA", description="Hệ số bonus công bằng khi chọn miner (beta)")
    CONSENSUS_PARAM_MAX_TIME_BONUS: int = Field(10, alias="CONSENSUS_PARAM_MAX_TIME_BONUS", description="Số chu kỳ tối đa bonus thời gian chờ có tác dụng")
    CONSENSUS_PARAM_DELTA_TRUST: float = Field(0.1, alias="CONSENSUS_PARAM_DELTA_TRUST", description="Hằng số suy giảm trust score (delta_trust)")
    CONSENSUS_PARAM_ALPHA_BASE: float = Field(0.1, alias="CONSENSUS_PARAM_ALPHA_BASE", description="Learning rate cơ bản cho trust score (alpha_base)")
    CONSENSUS_PARAM_K_ALPHA: float = Field(1.0, alias="CONSENSUS_PARAM_K_ALPHA", description="Hệ số điều chỉnh độ nhạy learning rate trust score (k_alpha)")
    CONSENSUS_PARAM_UPDATE_SIG_L: float = Field(1.0, alias="CONSENSUS_PARAM_UPDATE_SIG_L", description="Tham số L cho sigmoid f_update_sig (trust update)")
    CONSENSUS_PARAM_UPDATE_SIG_K: float = Field(5.0, alias="CONSENSUS_PARAM_UPDATE_SIG_K", description="Tham số k cho sigmoid f_update_sig (trust update)")
    CONSENSUS_PARAM_UPDATE_SIG_X0: float = Field(0.5, alias="CONSENSUS_PARAM_UPDATE_SIG_X0", description="Tham số x0 cho sigmoid f_update_sig (trust update)")
    CONSENSUS_PARAM_INCENTIVE_SIG_L: float = Field(1.0, alias="CONSENSUS_PARAM_INCENTIVE_SIG_L", description="Tham số L cho sigmoid f_sig (incentive)")
    CONSENSUS_PARAM_INCENTIVE_SIG_K: float = Field(10.0, alias="CONSENSUS_PARAM_INCENTIVE_SIG_K", description="Tham số k cho sigmoid f_sig (incentive)")
    CONSENSUS_PARAM_INCENTIVE_SIG_X0: float = Field(0.5, alias="CONSENSUS_PARAM_INCENTIVE_SIG_X0", description="Tham số x0 cho sigmoid f_sig (incentive)")
    CONSENSUS_PARAM_FRAUD_THRESHOLD_DEV: float = Field(0.3, alias="CONSENSUS_PARAM_FRAUD_THRESHOLD_DEV", description="Ngưỡng độ lệch trung bình để nghi ngờ validator gian lận")
    CONSENSUS_PARAM_FRAUD_N_CYCLES: int = Field(3, alias="CONSENSUS_PARAM_FRAUD_N_CYCLES", description="Số chu kỳ duy trì độ lệch để xác nhận gian lận (cần logic theo dõi)")
    CONSENSUS_PARAM_PENALTY_ETA: float = Field(0.5, alias="CONSENSUS_PARAM_PENALTY_ETA", description="Hệ số phạt trust score validator khi gian lận (eta)")
    CONSENSUS_PARAM_MAX_SLASH_RATE: float = Field(0.2, alias="CONSENSUS_PARAM_MAX_SLASH_RATE", description="Tỷ lệ cắt stake tối đa khi gian lận")
    CONSENSUS_PARAM_DELTA_W: float = Field(0.5, alias="CONSENSUS_PARAM_DELTA_W", description="Hằng số suy giảm cho trọng số miner (delta_W)")
    CONSENSUS_PARAM_THETA1: float = Field(0.3, alias="CONSENSUS_PARAM_THETA1", description="Trọng số theta1 cho E_validator (Q_task)")
    CONSENSUS_PARAM_THETA2: float = Field(0.4, alias="CONSENSUS_PARAM_THETA2", description="Trọng số theta2 cho E_validator (Metric Quality)")
    CONSENSUS_PARAM_THETA3: float = Field(0.3, alias="CONSENSUS_PARAM_THETA3", description="Trọng số theta3 cho E_validator (Penalty Term)")
    CONSENSUS_PARAM_PENALTY_THRESHOLD_DEV: float = Field(0.1, alias="CONSENSUS_PARAM_PENALTY_THRESHOLD_DEV", description="Ngưỡng độ lệch bắt đầu phạt trong E_validator (Threshold_dev)")
    CONSENSUS_PARAM_PENALTY_K_PENALTY: float = Field(5.0, alias="CONSENSUS_PARAM_PENALTY_K_PENALTY", description="Hệ số phạt độ lệch trong E_validator (k')")
    CONSENSUS_PARAM_PENALTY_P_PENALTY: float = Field(1.0, alias="CONSENSUS_PARAM_PENALTY_P_PENALTY", description="Bậc phạt độ lệch trong E_validator (p)")
    CONSENSUS_PARAM_LAMBDA_BALANCE: float = Field(0.5, alias="CONSENSUS_PARAM_LAMBDA_BALANCE", description="Hệ số cân bằng stake/performance cho trọng số validator (lambda)")
    CONSENSUS_PARAM_STAKE_LOG_BASE: float = Field(math.e, alias="CONSENSUS_PARAM_STAKE_LOG_BASE", description=f"Cơ số log cho stake trong trọng số validator ({math.e} cho ln, 10 cho log10)")
    CONSENSUS_PARAM_TIME_LOG_BASE: float = Field(10, alias="CONSENSUS_PARAM_TIME_LOG_BASE", description="Cơ số log cho thời gian trong trọng số validator")
    CONSENSUS_PARAM_DAO_KG: float = Field(1.0, alias="CONSENSUS_PARAM_DAO_KG", description="Hệ số bonus thời gian cho voting power DAO (k_g)")
    CONSENSUS_PARAM_DAO_TOTAL_TIME: float = Field(365.0, alias="CONSENSUS_PARAM_DAO_TOTAL_TIME", description="Khoảng thời gian tham chiếu cho bonus thời gian DAO (ví dụ: 365 ngày)")
    CONSENSUS_DATUM_COMPARISON_TOLERANCE: float = Field(1e-5, alias="CONSENSUS_DATUM_COMPARISON_TOLERANCE", description="Sai số cho phép khi so sánh datum validator on-chain và dự kiến")

    # Giữ nguyên validator của bạn
    @field_validator("CARDANO_NETWORK", mode="before")
    def validate_network(cls, value: Optional[str]): # Cho phép Optional để xử lý default tốt hơn
        if value is None: value = "TESTNET" # Gán default nếu là None
        normalized = str(value).upper().strip()
        if normalized == "MAINNET": return Network.MAINNET
        # Mặc định là TESTNET cho các giá trị khác hoặc không hợp lệ
        return Network.TESTNET

# --- Tạo một instance để sử dụng trong toàn bộ ứng dụng ---
try:
    settings = Settings()
except Exception as e:
    print(f"CRITICAL: Error loading settings: {e}. Using default values where possible.")
    # Trong trường hợp lỗi nghiêm trọng, có thể nên thoát thay vì dùng default
    # raise SystemExit(f"Failed to load critical settings: {e}")
    settings = Settings() # Cố gắng tạo với default

# --- LOGGING CONFIGURATION ---
# Giữ nguyên cấu hình logging của bạn, đảm bảo nó dùng settings.LOG_LEVEL
try:
    log_level_str = settings.log_level.upper()
    if log_level_str not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        log_level_str = "INFO"
    LOG_LEVEL = getattr(logging, log_level_str)
except Exception:
    LOG_LEVEL = logging.INFO

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[ logging.StreamHandler() ] # Giữ nguyên handlers của bạn
)
logger = logging.getLogger(__name__)
logger.info(f"Settings loaded. Log level set to {logging.getLevelName(LOG_LEVEL)}.")

