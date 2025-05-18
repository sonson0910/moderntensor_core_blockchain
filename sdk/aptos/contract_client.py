"""
Client để tương tác với các contract ModernTensor trên Aptos
"""

from typing import Dict, Any, List, Optional, Union, cast
import time
import logging
from aptos_sdk.account import Account
from aptos_sdk.client import RestClient
from aptos_sdk.transactions import EntryFunction, TransactionArgument, TransactionPayload
from aptos_sdk.type_tag import TypeTag, StructTag
from aptos_sdk.bcs import Serializer

from .datatypes import MinerInfo, ValidatorInfo, SubnetInfo, STATUS_ACTIVE

# Logger cấu hình
logger = logging.getLogger(__name__)


class ModernTensorClient:
    """
    Client tương tác với các smart contract ModernTensor trên Aptos.
    
    Cung cấp các phương thức để:
    - Đăng ký Miner/Validator mới
    - Cập nhật thông tin Miner/Validator
    - Truy vấn thông tin Miner/Validator/Subnet
    """
    
    def __init__(
        self,
        account: Account,
        client: RestClient,
        moderntensor_address: str = "0xcafe",  # Địa chỉ contract ModernTensor
    ):
        """
        Khởi tạo client ModernTensor.
        
        Args:
            account: Tài khoản Aptos để ký giao dịch.
            client: RestClient của Aptos để tương tác với blockchain.
            moderntensor_address: Địa chỉ của contract ModernTensor trên Aptos.
        """
        self.account = account
        self.client = client
        self.moderntensor_address = moderntensor_address
    
    async def register_miner(
        self,
        uid: bytes,
        subnet_uid: int,
        stake_amount: int,
        api_endpoint: str,
        gas_unit_price: Optional[int] = None,
        max_gas_amount: Optional[int] = None,
    ) -> str:
        """
        Đăng ký một miner mới trên ModernTensor.
        
        Args:
            uid: UID dạng bytes của miner.
            subnet_uid: UID của subnet mà miner đăng ký.
            stake_amount: Số lượng APT stake (đã scale 10^8).
            api_endpoint: URL API endpoint của miner.
            gas_unit_price: Giá gas đơn vị (tùy chọn).
            max_gas_amount: Lượng gas tối đa (tùy chọn).
            
        Returns:
            str: Hash của giao dịch.
        """
        logger.info(f"Registering miner with UID {uid.hex()} on subnet {subnet_uid}")
        
        payload = EntryFunction.natural(
            f"{self.moderntensor_address}::miner",
            "register_miner",
            [],  # Type args
            [
                TransactionArgument(uid, Serializer.SEQUENCE),
                TransactionArgument(subnet_uid, Serializer.U64),
                TransactionArgument(stake_amount, Serializer.U64),
                TransactionArgument(api_endpoint, Serializer.STR),
            ],
        )
        
        txn_hash = await self.client.submit_transaction(
            self.account,
            TransactionPayload(payload),
            gas_unit_price=gas_unit_price,
            max_gas_amount=max_gas_amount,
        )
        
        # Đợi confirmation
        await self.client.wait_for_transaction(txn_hash)
        return txn_hash
    
    async def register_validator(
        self,
        uid: bytes,
        subnet_uid: int,
        stake_amount: int,
        api_endpoint: str,
        gas_unit_price: Optional[int] = None,
        max_gas_amount: Optional[int] = None,
    ) -> str:
        """
        Đăng ký một validator mới trên ModernTensor.
        
        Args:
            uid: UID dạng bytes của validator.
            subnet_uid: UID của subnet mà validator đăng ký.
            stake_amount: Số lượng APT stake (đã scale 10^8).
            api_endpoint: URL API endpoint của validator.
            gas_unit_price: Giá gas đơn vị (tùy chọn).
            max_gas_amount: Lượng gas tối đa (tùy chọn).
            
        Returns:
            str: Hash của giao dịch.
        """
        logger.info(f"Registering validator with UID {uid.hex()} on subnet {subnet_uid}")
        
        payload = EntryFunction.natural(
            f"{self.moderntensor_address}::validator",
            "register_validator",
            [],  # Type args
            [
                TransactionArgument(uid, Serializer.SEQUENCE),
                TransactionArgument(subnet_uid, Serializer.U64),
                TransactionArgument(stake_amount, Serializer.U64),
                TransactionArgument(api_endpoint, Serializer.STR),
            ],
        )
        
        txn_hash = await self.client.submit_transaction(
            self.account,
            TransactionPayload(payload),
            gas_unit_price=gas_unit_price,
            max_gas_amount=max_gas_amount,
        )
        
        # Đợi confirmation
        await self.client.wait_for_transaction(txn_hash)
        return txn_hash
    
    async def update_miner_scores(
        self,
        miner_address: str,
        new_performance: int,  # Đã scale (x 1,000,000)
        new_trust_score: int,  # Đã scale (x 1,000,000)
        gas_unit_price: Optional[int] = None,
        max_gas_amount: Optional[int] = None,
    ) -> str:
        """
        Cập nhật điểm số của một miner.
        
        Args:
            miner_address: Địa chỉ Aptos của miner.
            new_performance: Điểm hiệu suất mới (đã scale).
            new_trust_score: Điểm tin cậy mới (đã scale).
            gas_unit_price: Giá gas đơn vị (tùy chọn).
            max_gas_amount: Lượng gas tối đa (tùy chọn).
            
        Returns:
            str: Hash của giao dịch.
        """
        logger.info(f"Updating scores for miner {miner_address}")
        
        payload = EntryFunction.natural(
            f"{self.moderntensor_address}::miner",
            "update_miner_scores",
            [],  # Type args
            [
                TransactionArgument(miner_address, Serializer.ADDRESS),
                TransactionArgument(new_performance, Serializer.U64),
                TransactionArgument(new_trust_score, Serializer.U64),
            ],
        )
        
        txn_hash = await self.client.submit_transaction(
            self.account,
            TransactionPayload(payload),
            gas_unit_price=gas_unit_price,
            max_gas_amount=max_gas_amount,
        )
        
        # Đợi confirmation
        await self.client.wait_for_transaction(txn_hash)
        return txn_hash
    
    async def create_subnet(
        self,
        net_uid: int,
        name: str,
        description: str,
        max_miners: int,
        max_validators: int,
        immunity_period: int,
        min_stake_miner: int,
        min_stake_validator: int,
        reg_cost: int,
        gas_unit_price: Optional[int] = None,
        max_gas_amount: Optional[int] = None,
    ) -> str:
        """
        Tạo một subnet mới.
        
        Args:
            net_uid: UID của subnet mới.
            name: Tên của subnet.
            description: Mô tả của subnet.
            max_miners: Số lượng miner tối đa.
            max_validators: Số lượng validator tối đa.
            immunity_period: Thời gian miễn trừ (tính bằng giây).
            min_stake_miner: Lượng stake tối thiểu cho miner.
            min_stake_validator: Lượng stake tối thiểu cho validator.
            reg_cost: Chi phí đăng ký.
            gas_unit_price: Giá gas đơn vị (tùy chọn).
            max_gas_amount: Lượng gas tối đa (tùy chọn).
            
        Returns:
            str: Hash của giao dịch.
        """
        logger.info(f"Creating subnet with UID {net_uid} named '{name}'")
        
        payload = EntryFunction.natural(
            f"{self.moderntensor_address}::subnet",
            "create_subnet",
            [],  # Type args
            [
                TransactionArgument(net_uid, Serializer.U64),
                TransactionArgument(name, Serializer.STR),
                TransactionArgument(description, Serializer.STR),
                TransactionArgument(max_miners, Serializer.U64),
                TransactionArgument(max_validators, Serializer.U64),
                TransactionArgument(immunity_period, Serializer.U64),
                TransactionArgument(min_stake_miner, Serializer.U64),
                TransactionArgument(min_stake_validator, Serializer.U64),
                TransactionArgument(reg_cost, Serializer.U64),
            ],
        )
        
        txn_hash = await self.client.submit_transaction(
            self.account,
            TransactionPayload(payload),
            gas_unit_price=gas_unit_price,
            max_gas_amount=max_gas_amount,
        )
        
        # Đợi confirmation
        await self.client.wait_for_transaction(txn_hash)
        return txn_hash
        
    async def get_miner_info(self, miner_address: str) -> MinerInfo:
        """
        Truy vấn thông tin của một miner.
        
        Args:
            miner_address: Địa chỉ Aptos của miner.
            
        Returns:
            MinerInfo: Đối tượng chứa thông tin miner.
            
        Raises:
            ValueError: Nếu miner không tồn tại.
        """
        try:
            result = await self.client.view_function(
                self.moderntensor_address,
                "miner",
                "get_miner_performance",
                [miner_address],
            )
            
            # Kết quả là performance scaled
            performance = result / 1_000_000
            
            # Lấy trust score
            trust_result = await self.client.view_function(
                self.moderntensor_address,
                "miner",
                "get_miner_trust_score",
                [miner_address],
            )
            
            trust_score = trust_result / 1_000_000
            
            # Lấy thông tin resource miner
            resource = await self.client.account_resource(
                miner_address,
                f"{self.moderntensor_address}::miner::MinerInfo",
            )
            
            data = resource["data"]
            
            return MinerInfo(
                uid=data["uid"].hex(),
                address=miner_address,
                api_endpoint=data["api_endpoint"],
                trust_score=trust_score,
                weight=0.0,  # Được tính toán ở tầng ứng dụng
                stake=data["stake"] / 100_000_000,  # Convert from smallest unit to APT
                last_selected_time=-1,  # Không lưu ở blockchain
                performance_history=[],  # Không lưu lịch sử ở blockchain
                status=data["status"],
                subnet_uid=data["subnet_uid"],
                registration_timestamp=data["registration_timestamp"],
                performance_history_hash=bytes.fromhex(data["performance_history_hash"]) if data["performance_history_hash"] else None,
            )
            
        except Exception as e:
            logger.error(f"Error retrieving miner info for {miner_address}: {e}")
            raise ValueError(f"Failed to get miner info: {e}")
    
    # Thêm các phương thức khác để truy vấn validator, subnet, v.v. 