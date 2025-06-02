"""
Helper cho validator Move trên Aptos.
Thay thế chức năng của validator.py trong smartcontract cho Cardano Plutus.
"""

import logging
import json
import os
from typing import Dict, Any, Optional, List

from mt_aptos.async_client import RestClient
from mt_aptos.account import Account
from .contract_client import AptosContractClient

logger = logging.getLogger(__name__)


async def get_validator_info(
    client: RestClient, 
    contract_address: str, 
    validator_address: str
) -> Optional[Dict[str, Any]]:
    """
    Lấy thông tin validator từ hợp đồng trên Aptos.
    
    Args:
        client (RestClient): Client REST Aptos.
        contract_address (str): Địa chỉ hợp đồng ModernTensor.
        validator_address (str): Địa chỉ validator cần truy vấn.
        
    Returns:
        Optional[Dict[str, Any]]: Thông tin validator nếu có, None nếu không tìm thấy.
    """
    try:
        # Đảm bảo địa chỉ có định dạng đúng
        if not validator_address.startswith("0x"):
            validator_address = f"0x{validator_address}"
            
        # Tạo contract client
        contract_client = AptosContractClient(
            client=client,
            contract_address=contract_address
        )
        
        # Gọi view function để lấy thông tin validator
        validator_info = await contract_client.call_view_function(
            function="get_validator_info",
            type_arguments=[],
            arguments=[validator_address]
        )
        
        return validator_info
    except Exception as e:
        logger.error(f"Lỗi khi lấy thông tin validator {validator_address}: {e}")
        return None


async def get_all_validators(
    client: RestClient,
    contract_address: str
) -> List[Dict[str, Any]]:
    """
    Lấy danh sách tất cả các validator từ hợp đồng trên Aptos.
    
    Args:
        client (RestClient): Client REST Aptos.
        contract_address (str): Địa chỉ hợp đồng ModernTensor.
        
    Returns:
        List[Dict[str, Any]]: Danh sách thông tin validator.
    """
    try:
        # Tạo contract client
        contract_client = AptosContractClient(
            client=client,
            contract_address=contract_address
        )
        
        # Gọi view function để lấy tất cả validator
        validators = await contract_client.call_view_function(
            function="get_all_validators",
            type_arguments=[],
            arguments=[]
        )
        
        return validators if validators else []
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách validator: {e}")
        return []


async def get_all_miners(
    client: RestClient,
    contract_address: str
) -> List[Dict[str, Any]]:
    """
    Lấy danh sách tất cả các miner từ hợp đồng trên Aptos.
    
    Args:
        client (RestClient): Client REST Aptos.
        contract_address (str): Địa chỉ hợp đồng ModernTensor.
        
    Returns:
        List[Dict[str, Any]]: Danh sách thông tin miner.
    """
    try:
        # Tạo contract client
        contract_client = AptosContractClient(
            client=client,
            contract_address=contract_address
        )
        
        # Gọi view function để lấy tất cả miner
        miners = await contract_client.call_view_function(
            function="get_all_miners",
            type_arguments=[],
            arguments=[]
        )
        
        return miners if miners else []
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách miner: {e}")
        return []


async def is_validator_active(
    client: RestClient,
    contract_address: str,
    validator_address: str
) -> bool:
    """
    Kiểm tra xem một validator có đang hoạt động hay không.
    
    Args:
        client (RestClient): Client REST Aptos.
        contract_address (str): Địa chỉ hợp đồng ModernTensor.
        validator_address (str): Địa chỉ validator cần kiểm tra.
        
    Returns:
        bool: True nếu validator đang hoạt động, False nếu không.
    """
    try:
        validator_info = await get_validator_info(client, contract_address, validator_address)
        
        if not validator_info:
            return False
            
        # Kiểm tra trạng thái của validator
        return validator_info.get("status") == "active"
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra trạng thái validator {validator_address}: {e}")
        return False 