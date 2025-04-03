# sdk/consensus/datatypes.py
"""
Định nghĩa các cấu trúc dữ liệu sử dụng trong module đồng thuận.
"""
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field

@dataclass
class MinerInfo:
    """Lưu trữ thông tin trạng thái của một Miner."""
    uid: str
    address: str # Địa chỉ ví hoặc định danh mạng
    trust_score: float
    weight: float # W_x (Cần được load hoặc tính toán)
    stake: float # Lượng stake (nếu có)
    last_selected_time: int # Chu kỳ cuối cùng được chọn
    performance_history: List[float] = field(default_factory=list)
    # Thêm các trường khác từ MinerDatum nếu cần (ví dụ: pending_rewards)

@dataclass
class ValidatorInfo:
    """Lưu trữ thông tin trạng thái của một Validator."""
    uid: str
    address: str
    trust_score: float
    weight: float # W_v (Cần được load hoặc tính toán)
    stake: float
    # Thêm các trường khác từ ValidatorDatum nếu cần

@dataclass
class TaskAssignment:
    """Lưu trữ thông tin về một task đã được giao cho Miner."""
    task_id: str
    task_data: Any # Nội dung công việc cụ thể
    miner_uid: str
    validator_uid: str
    timestamp_sent: float
    expected_result_format: Any # Mô tả định dạng kết quả mong đợi

@dataclass
class MinerResult:
    """Lưu trữ kết quả một Miner trả về cho một task."""
    task_id: str
    miner_uid: str
    result_data: Any # Kết quả thực tế từ miner
    timestamp_received: float

@dataclass
class ValidatorScore:
    """Lưu trữ điểm số một Validator chấm cho một Miner về một task."""
    task_id: str
    miner_uid: str
    validator_uid: str
    score: float # Điểm P_miner,v do validator này chấm
    deviation: Optional[float] = None # Độ lệch so với điểm đồng thuận (sẽ tính sau)

