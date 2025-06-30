# sdk/metagraph/metagraph_datum.py
"""
Định nghĩa cấu trúc dữ liệu cho các thành phần trong Metagraph (Miner, Validator, Subnet)
cho Aptos blockchain.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

# --- Import settings để lấy divisor ---
try:
    from mt_aptos.config.settings import settings

    DATUM_INT_DIVISOR = settings.METAGRAPH_DATUM_INT_DIVISOR
except ImportError:
    print(
        "Warning: Could not import settings for DATUM_INT_DIVISOR. Using default 1_000_000.0"
    )
    DATUM_INT_DIVISOR = 1_000_000.0

# --- Định nghĩa các hằng số trạng thái ---
STATUS_INACTIVE = 0  # Chưa đăng ký hoặc đã hủy đăng ký
STATUS_ACTIVE = 1  # Đang hoạt động
STATUS_JAILED = 2  # Bị phạt, tạm khóa hoạt động


@dataclass
class MinerData:
    """Lưu trữ trạng thái của một Miner trên blockchain."""

    uid: str  # hexadecimal string
    subnet_uid: int
    stake: int
    scaled_last_performance: int  # Đã scale (x DIVISOR)
    scaled_trust_score: int  # Đã scale (x DIVISOR)
    accumulated_rewards: int
    last_update_time: int  # Timestamp cuối cùng dữ liệu này được cập nhật
    performance_history_hash: str  # hexadecimal string
    wallet_addr_hash: str  # hexadecimal string
    status: int  # 0: Inactive, 1: Active, 2: Jailed
    registration_time: int
    api_endpoint: str

    @property
    def trust_score(self) -> float:
        """Trả về trust score dạng float."""
        return (
            self.scaled_trust_score / DATUM_INT_DIVISOR
        )  # Sử dụng divisor từ settings

    @property
    def last_performance(self) -> float:
        """Trả về performance dạng float."""
        return (
            self.scaled_last_performance / DATUM_INT_DIVISOR
        )  # Sử dụng divisor từ settings


@dataclass
class ValidatorData:
    """Lưu trữ trạng thái của một Validator trên blockchain."""

    uid: str  # hexadecimal string
    subnet_uid: int
    stake: int
    scaled_last_performance: int  # Đã scale (x DIVISOR)
    scaled_trust_score: int  # Đã scale (x DIVISOR)
    accumulated_rewards: int
    last_update_time: int
    performance_history_hash: str  # hexadecimal string
    wallet_addr_hash: str  # hexadecimal string
    status: int  # 0: Inactive, 1: Active, 2: Jailed
    registration_time: int
    api_endpoint: str

    @property
    def trust_score(self) -> float:
        """Trả về trust score dạng float."""
        return (
            self.scaled_trust_score / DATUM_INT_DIVISOR
        )  # Sử dụng divisor từ settings

    @property
    def last_performance(self) -> float:
        """Trả về performance dạng float."""
        return (
            self.scaled_last_performance / DATUM_INT_DIVISOR
        )  # Sử dụng divisor từ settings


@dataclass
class SubnetStaticData:
    """Lưu trữ thông tin tĩnh, ít thay đổi của một Subnet."""

    net_uid: int
    name: str
    owner_addr: str
    max_miners: int
    max_validators: int
    immunity_period: int
    creation_time: int
    description: str
    version: int
    min_stake_miner: int
    min_stake_validator: int


@dataclass
class SubnetDynamicData:
    """Lưu trữ thông tin động, thường xuyên thay đổi của một Subnet."""

    net_uid: int
    scaled_weight: int  # Đã scale (x DIVISOR)
    scaled_performance: int  # Đã scale (x DIVISOR)
    current_epoch: int
    registration_open: int
    reg_cost: int
    scaled_incentive_ratio: int  # Đã scale (x DIVISOR)
    last_update_time: int
    total_stake: int
    validator_count: int
    miner_count: int

    @property
    def weight(self) -> float:
        """Trả về weight dạng float."""
        return (
            self.scaled_weight / DATUM_INT_DIVISOR
        )  # Sử dụng divisor từ settings

    @property
    def performance(self) -> float:
        """Trả về performance dạng float."""
        return (
            self.scaled_performance / DATUM_INT_DIVISOR
        )  # Sử dụng divisor từ settings

# Helper functions to convert between data objects and Move resources
def from_move_resource(resource_data: Dict[str, Any], data_class: type) -> Any:
    """
    Convert a Move resource dictionary to a Python data class instance.
    
    Args:
        resource_data: Dictionary containing the Move resource fields
        data_class: The target Python data class type
        
    Returns:
        An instance of the specified data class
    """
    # Create a dictionary of parameters for the data class constructor
    params = {}
    
    # For each field in the data class, find the corresponding value in the resource data
    for field_name in data_class.__annotations__:
        # Handle type conversions as needed
        if field_name in resource_data:
            params[field_name] = resource_data[field_name]
    
    # Create and return the data class instance
    return data_class(**params)

def to_move_resource(data_obj: Any) -> Dict[str, Any]:
    """
    Convert a Python data class instance to a Move resource dictionary.
    
    Args:
        data_obj: The data class instance to convert
        
    Returns:
        Dictionary suitable for creating or updating a Move resource
    """
    # Create a dictionary from the data object's fields
    resource_data = {}
    
    # Convert each field, handling any needed type conversions
    for field_name, field_value in data_obj.__dict__.items():
        resource_data[field_name] = field_value
    
    return resource_data


# --- Legacy aliases for backward compatibility ---
MinerDatum = MinerData
ValidatorDatum = ValidatorData
