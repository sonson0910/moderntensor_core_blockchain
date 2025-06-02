"""
Định nghĩa các cấu trúc dữ liệu cốt lõi dùng chung trong ModernTensor Aptos SDK.
"""
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field
import time

from pydantic import BaseModel, Field

# Các hằng số trạng thái
STATUS_INACTIVE = 0
STATUS_ACTIVE = 1
STATUS_JAILED = 2


@dataclass
class MinerInfo:
    """Lưu trữ thông tin trạng thái của một Miner trong bộ nhớ."""

    uid: str  # UID dạng hex string
    address: str  # Địa chỉ Aptos
    api_endpoint: Optional[str] = None
    trust_score: float = 0.0
    weight: float = 0.0
    stake: float = 0.0
    last_selected_time: int = -1  # Chu kỳ cuối cùng được chọn
    performance_history: List[float] = field(default_factory=list)
    status: int = STATUS_ACTIVE
    subnet_uid: int = 0  # UID của Subnet miner thuộc về
    registration_timestamp: int = 0
    performance_history_hash: Optional[bytes] = None


@dataclass
class ValidatorInfo:
    """Lưu trữ thông tin trạng thái của một Validator."""

    uid: str
    address: str  # Địa chỉ Aptos
    api_endpoint: Optional[str] = None
    trust_score: float = 0.0
    weight: float = 0.0
    stake: float = 0.0
    last_performance: float = 0.0
    status: int = STATUS_ACTIVE
    subnet_uid: int = 0
    registration_timestamp: int = 0
    performance_history: List[float] = field(default_factory=list)
    performance_history_hash: Optional[bytes] = None


@dataclass
class SubnetInfo:
    """Lưu trữ thông tin về một Subnet."""

    uid: int
    name: str
    description: str
    owner_address: str
    weight: float = 0.0
    performance: float = 0.0
    total_stake: float = 0.0
    validator_count: int = 0
    miner_count: int = 0
    max_miners: int = 1000
    max_validators: int = 100
    current_epoch: int = 0
    registration_open: bool = True
    registration_cost: float = 0.0
    creation_timestamp: int = 0
    last_update_timestamp: int = 0


@dataclass
class TaskAssignment:
    """Lưu trữ thông tin về một task đã được giao cho Miner."""

    task_id: str
    task_data: Any
    miner_uid: str
    validator_uid: str
    timestamp_sent: float
    expected_result_format: Any


@dataclass
class MinerResult:
    """Lưu trữ kết quả một Miner trả về cho một task."""

    task_id: str
    miner_uid: str
    result_data: Any
    timestamp_received: float


@dataclass
class ValidatorScore:
    """Lưu trữ điểm số một Validator chấm cho một Miner về một task."""

    task_id: str
    miner_uid: str
    validator_uid: str  # Validator đã chấm điểm này
    score: float  # Điểm P_miner,v
    deviation: Optional[float] = None  # Độ lệch so với điểm đồng thuận (tính sau)
    timestamp: float = field(default_factory=time.time)  # Thời điểm chấm điểm


class ScoreSubmissionPayload(BaseModel):
    """Dữ liệu điểm số gửi qua API, bao gồm chữ ký."""

    scores: List[ValidatorScore] = Field(
        ..., description="Danh sách điểm số chi tiết ValidatorScore"
    )
    submitter_validator_uid: str = Field(
        ..., description="UID (dạng hex) của validator gửi điểm"
    )
    cycle: int = Field(..., description="Chu kỳ đồng thuận mà điểm số này thuộc về")
    submitter_address: Optional[str] = Field(
        None, description="Địa chỉ Aptos của người gửi"
    )
    signature: Optional[str] = Field(
        None,
        description="Chữ ký (dạng hex) của hash(canonical_json(scores)) để xác thực người gửi",
    )


class MinerConsensusResult(BaseModel):
    """
    Dữ liệu kết quả đồng thuận cho một Miner cụ thể trong một chu kỳ,
    do Validator tính toán và công bố.
    """

    miner_uid: str = Field(..., description="UID (hex) của Miner")
    p_adj: float = Field(..., description="Điểm hiệu suất đồng thuận cuối cùng (P_adj)")
    calculated_incentive: float = Field(
        ...,
        description="Phần thưởng (incentive) đã được tính toán (dạng float, chưa scale)",
    )


class CycleConsensusResults(BaseModel):
    """
    Toàn bộ kết quả đồng thuận của một chu kỳ, được Validator công bố.
    """

    cycle: int = Field(..., description="Số thứ tự chu kỳ")
    results: Dict[str, MinerConsensusResult] = Field(
        ..., description="Dictionary chứa kết quả cho từng Miner (key là miner_uid hex)"
    )
    publisher_uid: Optional[str] = Field(
        None, description="UID (hex) của validator công bố"
    )
    publish_timestamp: Optional[float] = Field(
        default_factory=time.time,
        description="Timestamp khi kết quả được công bố/cache",
    ) 