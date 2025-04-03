# sdk/consensus/__init__.py

# Export các lớp và kiểu dữ liệu chính ra ngoài module
from .datatypes import (
    MinerInfo,
    ValidatorInfo,
    TaskAssignment,
    MinerResult,
    ValidatorScore
)
from .node import ValidatorNode
# Có thể export thêm các hàm tiện ích hoặc lớp khác nếu cần

__all__ = [
    # Datatypes
    "MinerInfo",
    "ValidatorInfo",
    "TaskAssignment",
    "MinerResult",
    "ValidatorScore",
    # Node Classes
    "ValidatorNode",
]
