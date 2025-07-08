# sdk/config/settings.py

import logging
import math
from typing import Optional
import coloredlogs
import re

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ANSI color codes
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

# Regex to find potential TxIDs (64 hex chars) or Addresses/Hashes (e.g., 56 hex chars)
# Word boundaries \b ensure we match whole hex strings
HEX_ID_REGEX = re.compile(r"(\b[a-fA-F0-9]{56,64}\b)")
SCORE_REGEX = re.compile(r"(\bScored\b)", re.IGNORECASE)


class HighlightFormatter(coloredlogs.ColoredFormatter):
    """Custom formatter to highlight 'score' and hex IDs/addresses."""

    def format(self, record):
        # Format the message using the base class first to get level colors
        formatted_message = super().format(record)
        try:
            # Use the already formatted message content for highlighting
            # This avoids issues if the original message is complex

            # Highlight 'score' first
            if SCORE_REGEX.search(formatted_message):
                formatted_message = SCORE_REGEX.sub(
                    f"{RED}\1{RESET}", formatted_message
                )

            # Then highlight hex IDs/addresses
            # Use a function for replacement to handle potential overlaps with score highlighting
            def replace_hex(match):
                hex_str = match.group(1)
                # Avoid re-coloring if already colored red (part of 'score')
                # This check is basic, might need refinement for complex cases
                if RED in hex_str:
                    return hex_str  # Don't change color if it was part of score
                return f"{YELLOW}{hex_str}{RESET}"

            formatted_message = HEX_ID_REGEX.sub(replace_hex, formatted_message)

        except Exception as format_err:
            # Log the formatting error itself using the root logger to avoid loops
            logging.getLogger().exception(f"Error in HighlightFormatter: {format_err}")
            # Return the message as formatted by the base class
            pass  # Keep the original formatted_message from super().format()

        return formatted_message


class Settings(BaseSettings):
    """
    Quản lý cấu hình tập trung cho dự án, load từ biến môi trường hoặc file .env.
    Đã cập nhật để bao gồm các tham số và hằng số cho module đồng thuận.
    """

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="MODERNTENSOR_",  # Giữ nguyên tiền tố (hoặc bỏ nếu không muốn)
    )

    # --- Các trường cấu hình cho Core blockchain ---
    CORE_NODE_URL: str = Field(
        default="https://rpc.test.btcs.network", 
        alias="CORE_NODE_URL",
        description="Core blockchain RPC URL"
    )
    CORE_MAINNET_URL: str = Field(
        default="https://rpc.coredao.org", 
        alias="CORE_MAINNET_URL",
        description="Core blockchain mainnet RPC URL"
    )
    CORE_CONTRACT_ADDRESS: str = Field(
        default="0x0000000000000000000000000000000000000000", 
        alias="CORE_CONTRACT_ADDRESS",
        description="ModernTensor contract address on Core blockchain"
    )
    CORE_NETWORK: str = Field(
        default="testnet", 
        alias="CORE_NETWORK",
        description="Core blockchain network (testnet/mainnet)"
    )
    CORE_CHAIN_ID: int = Field(
        default=1115,
        alias="CORE_CHAIN_ID", 
        description="Core blockchain chain ID (1115 for testnet, 1116 for mainnet)"
    )
    CORE_TOKEN_ADDRESS: str = Field(
        default="0x40375C92d9FAf44d2f9db9Bd9ba41a3317a2404f",
        alias="CORE_TOKEN_ADDRESS",
        description="CORE token contract address"
    )
    
    # --- Bitcoin staking configuration ---
    BITCOIN_STAKING_ENABLED: bool = Field(
        default=True,
        alias="BITCOIN_STAKING_ENABLED",
        description="Enable Bitcoin staking integration"
    )
    BITCOIN_MIN_LOCK_TIME: int = Field(
        default=86400,  # 24 hours
        alias="BITCOIN_MIN_LOCK_TIME",
        description="Minimum Bitcoin lock time in seconds"
    )
    BITCOIN_RPC_URL: str = Field(
        default="https://bitcoin-rpc.com",
        alias="BITCOIN_RPC_URL", 
        description="Bitcoin RPC URL for staking verification"
    )
    
    # --- Dual staking configuration ---
    DUAL_STAKING_ENABLED: bool = Field(
        default=True,
        alias="DUAL_STAKING_ENABLED",
        description="Enable dual staking (Bitcoin + CORE)"
    )
    DUAL_STAKING_MIN_CORE_RATIO: float = Field(
        default=0.1,
        alias="DUAL_STAKING_MIN_CORE_RATIO",
        description="Minimum CORE to Bitcoin ratio for dual staking"
    )

    # --- Các trường cấu hình gốc của bạn ---
    HOTKEY_BASE_DIR: str = Field(default="moderntensor", alias="HOTKEY_BASE_DIR")
    COLDKEY_NAME: str = Field(default="kickoff", alias="COLDKEY_NAME")
    HOTKEY_NAME: str = Field(default="hk1", alias="HOTKEY_NAME")
    HOTKEY_PASSWORD: str = Field(default="sonlearn2003", alias="HOTKEY_PASSWORD")
    ACCOUNT_BASE_DIR: str = Field(default="accounts", alias="ACCOUNT_BASE_DIR")
    
    # --- Encryption Settings ---
    ENCRYPTION_PBKDF2_ITERATIONS: int = Field(
        default=100_000,  # Standard default for PBKDF2HMAC
        alias="ENCRYPTION_PBKDF2_ITERATIONS",
        description="Number of iterations for PBKDF2 key derivation.",
    )

    # --- Thêm các trường cấu hình Node (Ví dụ) ---
    API_PORT: int = Field(8001, alias="API_PORT", description="Port cho FastAPI server")
    VALIDATOR_UID: Optional[str] = Field(
        None, alias="VALIDATOR_UID", description="UID của validator này (nếu chạy node)"
    )
    VALIDATOR_ADDRESS: Optional[str] = Field(
        None, alias="VALIDATOR_ADDRESS", description="Địa chỉ Core của validator này"
    )
    MINER_ADDRESS: Optional[str] = Field(
        None, alias="MINER_ADDRESS", description="Địa chỉ Core của miner này"
    )
    VALIDATOR_API_ENDPOINT: Optional[str] = Field(
        None,
        alias="VALIDATOR_API_ENDPOINT",
        description="Địa chỉ API đầy đủ mà các node khác có thể gọi đến validator này",
    )

    # ======== THÊM TRƯỜNG LOG_LEVEL ========
    LOG_LEVEL: str = Field(
        default="DEBUG",
        alias="LOG_LEVEL",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    # --- Cấu hình Đồng thuận (Consensus) - Tham số & Hằng số ---

    # === Slot-Based Cycle Timing (Cardano ModernTensor Pattern) ===
    CONSENSUS_CYCLE_LENGTH: int = Field(
        default=600,  # Ví dụ: 600 giây = 10 phút
        alias="CONSENSUS_CYCLE_LENGTH",
        description="Độ dài của một chu kỳ đồng thuận tính bằng giây.",
    )
    
    # --- Cardano-style Slot Configuration ---
    SLOT_DURATION_MINUTES: int = Field(
        default=20,  # 20 phút cho testing, 60 phút cho production
        alias="SLOT_DURATION_MINUTES",
        description="Tổng thời gian của một slot (phút) - Cardano pattern"
    )
    TASK_ASSIGNMENT_MINUTES: int = Field(
        default=5,  # 5 phút đầu để giao task
        alias="TASK_ASSIGNMENT_MINUTES", 
        description="Thời gian giao task trong slot (phút) - Cardano pattern"
    )
    TASK_EXECUTION_MINUTES: int = Field(
        default=10,  # 10 phút để miners thực hiện task
        alias="TASK_EXECUTION_MINUTES",
        description="Thời gian thực hiện task trong slot (phút) - Cardano pattern"
    )
    CONSENSUS_MINUTES: int = Field(
        default=5,  # 5 phút cuối để consensus
        alias="CONSENSUS_MINUTES",
        description="Thời gian consensus trong slot (phút) - Cardano pattern"
    )
    
    # --- Cardano-style Consensus Timing ---
    CONSENSUS_SCORE_WAIT_TIMEOUT: int = Field(
        default=180,  # 3 phút chờ scores từ validators khác
        alias="CONSENSUS_SCORE_WAIT_TIMEOUT",
        description="Timeout chờ consensus scores từ validators khác (giây) - Cardano pattern"
    )
    CONSENSUS_P2P_TIMEOUT: int = Field(
        default=5,  # 5 giây timeout cho P2P calls
        alias="CONSENSUS_P2P_TIMEOUT", 
        description="Timeout cho P2P score broadcast (giây) - Cardano pattern"
    )
    CONSENSUS_SLOT_CHECK_INTERVAL: int = Field(
        default=30,  # Kiểm tra phase mỗi 30 giây
        alias="CONSENSUS_SLOT_CHECK_INTERVAL",
        description="Khoảng thời gian kiểm tra slot phase (giây) - Cardano pattern"
    )
    CONSENSUS_QUERY_INTERVAL_SECONDS: float = Field(
        default=0.5,
        alias="CONSENSUS_QUERY_INTERVAL_SECONDS",
        description="Khoảng thời gian (giây) giữa các lần kiểm tra thời gian hiện tại khi chờ đợi.",
    )

    # Các offset tính bằng GIÂY tính từ **cuối** chu kỳ mục tiêu
    CONSENSUS_COMMIT_OFFSET_SECONDS: int = Field(
        default=30,
        alias="CONSENSUS_COMMIT_OFFSET_SECONDS",
        description="Số giây trước khi kết thúc chu kỳ để bắt đầu commit.",
    )
    CONSENSUS_TIMEOUT_OFFSET_SECONDS: int = Field(
        default=60,
        alias="CONSENSUS_TIMEOUT_OFFSET_SECONDS",
        description="Số giây trước khi kết thúc chu kỳ để dừng chờ điểm P2P.",
    )
    CONSENSUS_BROADCAST_OFFSET_SECONDS: int = Field(
        default=90,
        alias="CONSENSUS_BROADCAST_OFFSET_SECONDS",
        description="Số giây trước khi kết thúc chu kỳ để broadcast điểm cục bộ.",
    )

    # Tỉ lệ thời gian cho giai đoạn Tasking (vẫn giữ dựa trên thời gian thực tương đối)
    CONSENSUS_TASKING_PHASE_RATIO: float = Field(
        default=0.85,  # Giữ nguyên hoặc điều chỉnh
        alias="CONSENSUS_TASKING_PHASE_RATIO",
        description="Tỷ lệ *thời gian thực* của chu kỳ dành cho việc gửi task và nhận kết quả (mini-batches).",
    )
    CONSENSUS_MINI_BATCH_WAIT_SECONDS: int = Field(
        default=45,  # Giữ nguyên hoặc điều chỉnh
        alias="CONSENSUS_MINI_BATCH_WAIT_SECONDS",
        description="Timeout (giây) chờ kết quả trong một mini-batch.",
    )
    CONSENSUS_MINI_BATCH_INTERVAL_SECONDS: int = Field(
        default=5,  # Giữ nguyên hoặc điều chỉnh
        alias="CONSENSUS_MINI_BATCH_INTERVAL_SECONDS",
        description="Delay (giây) giữa các mini-batch.",
    )
    CONSENSUS_TASKING_END_SLOTS_OFFSET: int = Field(
        default=120,  # Ví dụ: Tasking kết thúc 500 slot trước khi hết chu kỳ
        alias="CONSENSUS_TASKING_END_SLOTS_OFFSET",
        description="Số slot trước khi kết thúc chu kỳ để dừng giai đoạn giao task.",
    )

    # --- Timing ---
    CONSENSUS_METAGRAPH_UPDATE_INTERVAL_MINUTES: int = Field(
        60,
        description="Khoảng thời gian (phút) giữa các lần cập nhật metagraph dự kiến.",
    )
    CONSENSUS_SEND_SCORE_OFFSET_MINUTES: int = Field(
        1,  # Giảm từ 2 phút xuống 1 phút
        description="Gửi điểm số P2P trước thời điểm cập nhật metagraph bao nhiêu phút.",
    )
    CONSENSUS_CONSENSUS_TIMEOUT_OFFSET_MINUTES: int = Field(
        1,
        description="Chờ điểm P2P đến trước thời điểm cập nhật metagraph bao nhiêu phút (phải nhỏ hơn SEND_SCORE_OFFSET).",
    )
    CONSENSUS_COMMIT_DELAY_SECONDS: float = Field(
        1.5,
        description="Delay (giây) giữa các lần submit giao dịch commit để tránh rate limit.",
    )
    CONSENSUS_CYCLE_MIN_WAIT_SECONDS: int = Field(
        10,
        description="Thời gian chờ tối thiểu (giây) giữa các chu kỳ, nếu chu kỳ hoàn thành quá nhanh.",
    )
    CONSENSUS_NETWORK_TIMEOUT_SECONDS: int = Field(
        10, description="Timeout (giây) cho các yêu cầu mạng P2P (gửi task, gửi điểm)."
    )

    # --- Limits & Constants ---
    CONSENSUS_MAX_PERFORMANCE_HISTORY_LEN: int = Field(
        100,
        description="Độ dài tối đa của lịch sử hiệu suất lưu trữ (ảnh hưởng tính weight).",
    )
    METAGRAPH_DATUM_INT_DIVISOR: float = Field(
        1_000_000.0,
        description="Hệ số scale khi lưu float (performance, trust) thành int trong Datum.",
    )
    CONSENSUS_MIN_VALIDATORS_FOR_CONSENSUS: int = Field(
        2,  # Giảm từ 3 xuống 2 để test với 2 validators
        description="Số validator tối thiểu cần gửi điểm để thực hiện tính toán đồng thuận.",
    )
    # CONSENSUS_REQUIRED_PERCENTAGE: float = Field(0.6, description="Tỷ lệ % validator tối thiểu cần gửi điểm (ngoài số lượng tối thiểu).") # Có thể thêm nếu muốn

    # --- Miner Selection ---
    CONSENSUS_NUM_MINERS_TO_SELECT: int = Field(
        5, description="Số lượng miner mỗi validator chọn trong một chu kỳ."
    )
    CONSENSUS_PARAM_BETA: float = Field(
        0.2,
        ge=0.0,
        description="Hệ số bonus công bằng khi chọn miner (beta >= 0). Càng lớn càng ưu tiên miner chờ lâu.",
    )
    CONSENSUS_PARAM_MAX_TIME_BONUS: int = Field(
        10,
        ge=0,
        description="Số chu kỳ tối đa mà bonus thời gian chờ (beta) có tác dụng.",
    )

    # --- Trust Score Update ---
    CONSENSUS_PARAM_DELTA_TRUST: float = Field(
        0.01,
        ge=0.0,
        lt=1.0,
        description="Hằng số suy giảm trust score mỗi chu kỳ (0 <= delta < 1). Càng lớn suy giảm càng nhanh.",
    )
    CONSENSUS_PARAM_ALPHA_BASE: float = Field(
        0.1,
        gt=0.0,
        le=1.0,
        description="Learning rate cơ bản khi cập nhật trust score (0 < alpha <= 1).",
    )
    CONSENSUS_PARAM_K_ALPHA: float = Field(
        1.0,
        ge=0.0,
        le=2.0,
        description="Hệ số điều chỉnh learning rate (0 <= k_alpha <= 2). k=0: alpha không đổi; k=2: alpha=0 tại trust=0 và 1.",
    )
    CONSENSUS_PARAM_UPDATE_SIG_L: float = Field(
        1.0,
        gt=0.0,
        description="Giá trị tối đa (L > 0) của hàm sigmoid f_update_sig (ánh xạ điểm perf/E_v mới khi cập nhật trust).",
    )
    CONSENSUS_PARAM_UPDATE_SIG_K: float = Field(
        10.0, gt=0.0, description="Độ dốc (k > 0) của hàm sigmoid f_update_sig."
    )
    CONSENSUS_PARAM_UPDATE_SIG_X0: float = Field(
        0.5, description="Điểm uốn (x0) của hàm sigmoid f_update_sig."
    )

    # --- Incentive Calculation ---
    CONSENSUS_PARAM_INCENTIVE_SIG_L: float = Field(
        1.0,
        gt=0.0,
        description="Giá trị tối đa (L > 0) của hàm sigmoid f_sig (ánh xạ trust score khi tính incentive).",
    )
    CONSENSUS_PARAM_INCENTIVE_SIG_K: float = Field(
        10.0, gt=0.0, description="Độ dốc (k > 0) của hàm sigmoid f_sig."
    )
    CONSENSUS_PARAM_INCENTIVE_SIG_X0: float = Field(
        0.5, description="Điểm uốn (x0) của hàm sigmoid f_sig."
    )

    # --- Thêm Cấu hình Mini-Batch ---
    CONSENSUS_ENABLE_MINI_BATCH: bool = Field(
        True,  # <<<--- Đặt là True để bật logic mới, False để dùng logic cũ
        alias="CONSENSUS_ENABLE_MINI_BATCH",
        description="Enable mini-batch tasking within a consensus cycle.",
    )
    CONSENSUS_MINI_BATCH_SIZE: int = Field(
        5,  # <<<--- Ví dụ: Gửi task cho 5 miner mỗi lô
        alias="CONSENSUS_MINI_BATCH_SIZE",
        description="Number of miners to select in each mini-batch (N).",
    )
    CONSENSUS_MINI_BATCH_WAIT_SECONDS: int = Field(
        30,  # <<<--- Ví dụ: Chờ kết quả mỗi lô trong 120 giây (2 phút)
        alias="CONSENSUS_MINI_BATCH_WAIT_SECONDS",
        description="Timeout (seconds) to wait for results within a single mini-batch.",
    )
    CONSENSUS_TASKING_PHASE_RATIO: float = Field(
        0.85,  # <<<--- Ví dụ: Giai đoạn gửi task/nhận kết quả chiếm 85% chu kỳ
        alias="CONSENSUS_TASKING_PHASE_RATIO",
        description="Ratio of the cycle interval dedicated to sending tasks and receiving results (mini-batches).",
    )
    CONSENSUS_MINI_BATCH_INTERVAL_SECONDS: int = Field(
        5,  # <<<--- Ví dụ: Chờ 5 giây giữa các lô nếu không có gì làm
        alias="CONSENSUS_MINI_BATCH_INTERVAL_SECONDS",
        description="Short delay (seconds) between mini-batch iterations to avoid busy-waiting.",
    )
    # ----

    # --- Fraud Detection & Penalty (Validator) ---
    CONSENSUS_DATUM_COMPARISON_TOLERANCE: float = Field(
        1e-5,
        gt=0.0,
        description="Sai số cho phép (float) khi so sánh datum on-chain và dự kiến.",
    )
    # CONSENSUS_PARAM_FRAUD_N_CYCLES: int = Field(3, ge=1, description="Số chu kỳ liên tiếp sai lệch để gắn cờ gian lận (cần logic theo dõi).") # Chưa dùng đến
    CONSENSUS_PARAM_PENALTY_ETA: float = Field(
        0.1,
        ge=0.0,
        le=1.0,
        description="Hệ số phạt trust score validator khi gian lận (0 <= eta <= 1). Giá trị = eta * severity.",
    )
    CONSENSUS_JAILED_SEVERITY_THRESHOLD: float = Field(
        0.2,
        ge=0.0,
        le=1.0,
        description="Ngưỡng severity tối thiểu để chuyển validator sang JAILED (0 <= threshold <= 1).",
    )
    CONSENSUS_PARAM_MAX_SLASH_RATE: float = Field(
        0.05,
        ge=0.0,
        le=1.0,
        description="Tỷ lệ cắt stake tối đa khi gian lận (0 <= rate <= 1). Ví dụ: 0.05 = 5% stake.",
    )

    # --- Weight Calculation ---
    CONSENSUS_PARAM_DELTA_W: float = Field(
        0.05,
        ge=0.0,
        lt=1.0,
        description="Hằng số suy giảm trọng số miner W_x theo thời gian (0 <= delta < 1).",
    )
    CONSENSUS_PARAM_LAMBDA_BALANCE: float = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="Hệ số cân bằng stake/performance cho trọng số validator W_v (0 <= lambda <= 1). lambda=1: chỉ stake; lambda=0: chỉ perf/time.",
    )
    CONSENSUS_PARAM_STAKE_LOG_BASE: float = Field(
        math.e,
        gt=1.0,
        description=f"Cơ số log cho stake trong W_v (> 1). Dùng {math.e:.2f} cho ln, 10 cho log10.",
    )
    CONSENSUS_PARAM_TIME_LOG_BASE: float = Field(
        10, gt=1.0, description="Cơ số log cho thời gian tham gia trong W_v (> 1)."
    )

    # --- Validator Performance (E_v) ---
    CONSENSUS_PARAM_THETA1: float = Field(
        0.1, ge=0.0, description="Trọng số theta1 cho E_v (Q_task - hiện không dùng)."
    )
    CONSENSUS_PARAM_THETA2: float = Field(
        0.6,
        ge=0.0,
        description="Trọng số theta2 cho E_v (Metric Quality - ví dụ: độ ổn định).",
    )
    CONSENSUS_PARAM_THETA3: float = Field(
        0.3,
        ge=0.0,
        description="Trọng số theta3 cho E_v (Penalty Term - phạt do sai lệch). Tổng theta nên = 1.",
    )
    CONSENSUS_PARAM_PENALTY_THRESHOLD_DEV: float = Field(
        0.05,
        ge=0.0,
        description="Ngưỡng độ lệch trung bình bắt đầu phạt trong E_v (Threshold_dev >= 0).",
    )
    CONSENSUS_PARAM_PENALTY_K_PENALTY: float = Field(
        10.0, ge=0.0, description="Hệ số phạt độ lệch trong E_v (k' >= 0)."
    )
    CONSENSUS_PARAM_PENALTY_P_PENALTY: float = Field(
        1.0,
        ge=1.0,
        description="Bậc phạt độ lệch trong E_v (p >= 1). p=1: tuyến tính; p=2: bậc hai.",
    )

    # --- DAO ---
    CONSENSUS_PARAM_DAO_KG: float = Field(
        1.0,
        ge=0.0,
        description="Hệ số bonus thời gian (sqrt) cho voting power DAO (k_g >= 0).",
    )
    CONSENSUS_PARAM_DAO_TOTAL_TIME: float = Field(
        365.0 * 24 * 60 * 60,
        gt=0.0,
        description="Khoảng thời gian tham chiếu (giây) cho bonus thời gian DAO (ví dụ: 1 năm).",
    )  # Đổi sang giây

    # Legacy Single Validator Configuration (for backward compatibility)
    VALIDATOR_PRIVATE_KEY: Optional[str] = Field(
        None, alias="VALIDATOR_PRIVATE_KEY", description="Private key for validator"
    )
    VALIDATOR_ADDRESS: Optional[str] = Field(
        None, alias="VALIDATOR_ADDRESS", description="Address for validator"
    )
    VALIDATOR_API_ENDPOINT: Optional[str] = Field(
        None,
        alias="VALIDATOR_API_ENDPOINT",
        description="API endpoint for the validator.",
    )

    # Multiple Validator Configurations (New)
    VALIDATOR_1_PRIVATE_KEY: Optional[str] = Field(
        None, alias="VALIDATOR_1_PRIVATE_KEY", description="Private key for validator 1"
    )
    VALIDATOR_1_ADDRESS: Optional[str] = Field(
        None, alias="VALIDATOR_1_ADDRESS", description="Address for validator 1"
    )
    VALIDATOR_1_API_ENDPOINT: Optional[str] = Field(
        None, alias="VALIDATOR_1_API_ENDPOINT", description="API endpoint for validator 1"
    )
    VALIDATOR_1_PORT: Optional[int] = Field(
        None, alias="VALIDATOR_1_PORT", description="Port for validator 1"
    )

    VALIDATOR_2_PRIVATE_KEY: Optional[str] = Field(
        None, alias="VALIDATOR_2_PRIVATE_KEY", description="Private key for validator 2"
    )
    VALIDATOR_2_ADDRESS: Optional[str] = Field(
        None, alias="VALIDATOR_2_ADDRESS", description="Address for validator 2"
    )
    VALIDATOR_2_API_ENDPOINT: Optional[str] = Field(
        None, alias="VALIDATOR_2_API_ENDPOINT", description="API endpoint for validator 2"
    )
    VALIDATOR_2_PORT: Optional[int] = Field(
        None, alias="VALIDATOR_2_PORT", description="Port for validator 2"
    )

    VALIDATOR_3_PRIVATE_KEY: Optional[str] = Field(
        None, alias="VALIDATOR_3_PRIVATE_KEY", description="Private key for validator 3"
    )
    VALIDATOR_3_ADDRESS: Optional[str] = Field(
        None, alias="VALIDATOR_3_ADDRESS", description="Address for validator 3"
    )
    VALIDATOR_3_API_ENDPOINT: Optional[str] = Field(
        None, alias="VALIDATOR_3_API_ENDPOINT", description="API endpoint for validator 3"
    )
    VALIDATOR_3_PORT: Optional[int] = Field(
        None, alias="VALIDATOR_3_PORT", description="Port for validator 3"
    )

    # Multiple Miner Configurations (New)
    MINER_1_PRIVATE_KEY: Optional[str] = Field(
        None, alias="MINER_1_PRIVATE_KEY", description="Private key for miner 1"
    )
    MINER_1_ADDRESS: Optional[str] = Field(
        None, alias="MINER_1_ADDRESS", description="Address for miner 1"
    )
    MINER_1_API_ENDPOINT: Optional[str] = Field(
        None, alias="MINER_1_API_ENDPOINT", description="API endpoint for miner 1"
    )
    MINER_1_PORT: Optional[int] = Field(
        None, alias="MINER_1_PORT", description="Port for miner 1"
    )

    MINER_2_PRIVATE_KEY: Optional[str] = Field(
        None, alias="MINER_2_PRIVATE_KEY", description="Private key for miner 2"
    )
    MINER_2_ADDRESS: Optional[str] = Field(
        None, alias="MINER_2_ADDRESS", description="Address for miner 2"
    )
    MINER_2_API_ENDPOINT: Optional[str] = Field(
        None, alias="MINER_2_API_ENDPOINT", description="API endpoint for miner 2"
    )
    MINER_2_PORT: Optional[int] = Field(
        None, alias="MINER_2_PORT", description="Port for miner 2"
    )

    # --- HTTP Client Settings ---
    HTTP_CLIENT_TIMEOUT: int = Field(
        default=30,
        alias="HTTP_CLIENT_TIMEOUT",
        description="HTTP client timeout in seconds"
    )
    HTTP_CLIENT_MAX_CONNECTIONS: int = Field(
        default=100,
        alias="HTTP_CLIENT_MAX_CONNECTIONS", 
        description="Maximum number of HTTP connections"
    )

    # --- Consensus Retry Settings ---
    CONSENSUS_MAX_RETRIES: int = Field(
        default=3,
        alias="CONSENSUS_MAX_RETRIES",
        description="Maximum number of retries for consensus operations"
    )
    CONSENSUS_RETRY_DELAY_SECONDS: float = Field(
        default=1.0,
        alias="CONSENSUS_RETRY_DELAY_SECONDS",
        description="Delay in seconds between consensus retries"
    )

    # --- Circuit Breaker Settings ---
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = Field(
        default=5,
        alias="CIRCUIT_BREAKER_FAILURE_THRESHOLD",
        description="Number of failures before circuit breaker opens"
    )
    CIRCUIT_BREAKER_RESET_TIMEOUT: int = Field(
        default=60,
        alias="CIRCUIT_BREAKER_RESET_TIMEOUT", 
        description="Time in seconds before circuit breaker attempts to reset"
    )

    # --- Rate Limiter Settings ---
    RATE_LIMITER_MAX_REQUESTS: int = Field(
        default=100,
        alias="RATE_LIMITER_MAX_REQUESTS",
        description="Maximum requests allowed in time window"
    )
    RATE_LIMITER_TIME_WINDOW: int = Field(
        default=60,
        alias="RATE_LIMITER_TIME_WINDOW",
        description="Time window in seconds for rate limiting"
    )

    def get_validator_config(self, validator_id: int = 1) -> dict:
        """Get configuration for a specific validator"""
        if validator_id == 1:
            return {
                "private_key": self.VALIDATOR_1_PRIVATE_KEY or self.VALIDATOR_PRIVATE_KEY,
                "address": self.VALIDATOR_1_ADDRESS or self.VALIDATOR_ADDRESS,
                "api_endpoint": self.VALIDATOR_1_API_ENDPOINT or self.VALIDATOR_API_ENDPOINT,
                "port": self.VALIDATOR_1_PORT or 8001
            }
        elif validator_id == 2:
            return {
                "private_key": self.VALIDATOR_2_PRIVATE_KEY,
                "address": self.VALIDATOR_2_ADDRESS,
                "api_endpoint": self.VALIDATOR_2_API_ENDPOINT,
                "port": self.VALIDATOR_2_PORT or 8002
            }
        elif validator_id == 3:
            return {
                "private_key": self.VALIDATOR_3_PRIVATE_KEY,
                "address": self.VALIDATOR_3_ADDRESS,
                "api_endpoint": self.VALIDATOR_3_API_ENDPOINT,
                "port": self.VALIDATOR_3_PORT or 8003
            }
        else:
            raise ValueError(f"Invalid validator_id: {validator_id}. Must be 1, 2, or 3")

    def get_miner_config(self, miner_id: int = 1) -> dict:
        """Get configuration for a specific miner"""
        if miner_id == 1:
            return {
                "private_key": self.MINER_1_PRIVATE_KEY or self.MINER_PRIVATE_KEY,
                "address": self.MINER_1_ADDRESS or self.MINER_ADDRESS,
                "api_endpoint": self.MINER_1_API_ENDPOINT,
                "port": self.MINER_1_PORT or 8100
            }
        elif miner_id == 2:
            return {
                "private_key": self.MINER_2_PRIVATE_KEY,
                "address": self.MINER_2_ADDRESS,
                "api_endpoint": self.MINER_2_API_ENDPOINT,
                "port": self.MINER_2_PORT or 8101
            }
        else:
            raise ValueError(f"Invalid miner_id: {miner_id}. Must be 1 or 2")

    def get_current_validator_endpoint(self) -> Optional[str]:
        """Get the current validator's API endpoint (for backward compatibility)"""
        # Try legacy setting first, then default to validator 1
        return self.VALIDATOR_API_ENDPOINT or self.VALIDATOR_1_API_ENDPOINT

    # Giữ nguyên validator của bạn
    @field_validator("CORE_NETWORK", mode="before")
    def validate_network(cls, value: Optional[str]):
        if value is None:
            return "https://testnet.aptoslabs.com/v1"
        
        value_str = str(value).strip()
        
        # If already full URL, keep it
        if value_str.startswith("http://") or value_str.startswith("https://"):
            return value_str
        
        # Otherwise convert network name to full URL
        normalized = value_str.lower()
        if normalized == "mainnet":
            return "https://mainnet.aptoslabs.com/v1"
        else:  # Default to testnet
            return "https://testnet.aptoslabs.com/v1"


# --- Tạo một instance để sử dụng trong toàn bộ ứng dụng ---
try:
    settings = Settings()  # type: ignore
    # --- Kiểm tra tổng Theta ---
    if not math.isclose(
        settings.CONSENSUS_PARAM_THETA1
        + settings.CONSENSUS_PARAM_THETA2
        + settings.CONSENSUS_PARAM_THETA3,
        1.0,
        abs_tol=1e-9,
    ):
        logging.warning(
            f"Sum of Theta parameters (theta1+theta2+theta3 = {settings.CONSENSUS_PARAM_THETA1 + settings.CONSENSUS_PARAM_THETA2 + settings.CONSENSUS_PARAM_THETA3}) is not equal to 1.0!"
        )
    # ------------------------
except Exception as e:
    print(
        f"CRITICAL: Error loading settings: {e}. Using default values where possible."
    )
    # Trong trường hợp lỗi nghiêm trọng, có thể nên thoát thay vì dùng default
    # raise SystemExit(f"Failed to load critical settings: {e}")
    settings = Settings()  # type: ignore # Cố gắng tạo với default

# --- LOGGING CONFIGURATION ---
# Giữ nguyên cấu hình logging của bạn, đảm bảo nó dùng settings.LOG_LEVEL
# --- CẤU HÌNH LOGGING (CHỈ MỘT LẦN TẠI ĐÂY) ---
# Sử dụng trường LOG_LEVEL vừa định nghĩa trong settings
try:
    log_level_str = settings.LOG_LEVEL.upper()
    if log_level_str not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        log_level_str = "INFO"
    # Lấy hằng số logging tương ứng
    LOG_LEVEL_CONFIG = getattr(logging, log_level_str)
except AttributeError:
    print("Warning: Could not read LOG_LEVEL from settings. Defaulting to INFO.")
    LOG_LEVEL_CONFIG = logging.INFO
except Exception as log_e:
    print(f"Warning: Error processing LOG_LEVEL setting: {log_e}. Defaulting to INFO.")
    LOG_LEVEL_CONFIG = logging.INFO

# <<< CLEAR EXISTING ROOT HANDLERS >>>
root_logger = logging.getLogger()
if root_logger.hasHandlers():
    # Use logging.debug directly as logger instance is not yet defined
    logging.debug(f"Root logger has handlers: {root_logger.handlers}. Removing them.")
    for handler in root_logger.handlers[:]:  # Iterate over a copy
        root_logger.removeHandler(handler)
# <<< END CLEAR >>>

# Define styles once
DEFAULT_LEVEL_STYLES = {
    "debug": {"color": "green"},
    "info": {"color": "cyan"},
    "warning": {"color": "yellow"},
    "error": {"color": "red"},
    "critical": {"bold": True, "color": "red"},
}
DEFAULT_FIELD_STYLES = {
    "asctime": {"color": "magenta"},
    "levelname": {"bold": True, "color": "blue"},
    "name": {"color": "white"},
}
DEFAULT_FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# Cấu hình basicConfig ngay tại đây
# logging.basicConfig(...)
# coloredlogs.install(...)

# Instantiate the custom formatter
highlight_formatter = HighlightFormatter(
    fmt=DEFAULT_FMT,
    level_styles=DEFAULT_LEVEL_STYLES,
    field_styles=DEFAULT_FIELD_STYLES,
)

# Install coloredlogs using the custom formatter
coloredlogs.install(
    level=LOG_LEVEL_CONFIG,
    formatter=highlight_formatter,
    reconfigure=True,
    # fmt, level_styles, field_styles are now handled by the formatter instance
)

# Lấy logger và ghi log ban đầu
logger = logging.getLogger(__name__)
# <<< FORCE DEBUG LEVEL FOR SDK CONSENSUS NODE >>>
logging.getLogger("sdk.consensus.node").setLevel(LOG_LEVEL_CONFIG)

logger.info(
    f"Settings loaded. Log level set to {logging.getLevelName(LOG_LEVEL_CONFIG)}."
)
