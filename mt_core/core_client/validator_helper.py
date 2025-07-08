"""
Helper cho validator Move trên Aptos.
Thay thế chức năng của validator.py trong smartcontract cho Cardano Plutus.
"""

import logging
import json
import os
from typing import Dict, Any, Optional, List

from mt_core.async_client import RestClient
from mt_core.account import Account
from .contract_client import AptosContractClient

logger = logging.getLogger(__name__)


async def get_validator_info(
    client: RestClient, 
    contract_address: str, 
    validator_uid: str
) -> Optional[Dict[str, Any]]:
    """
    Lấy thông tin validator từ hợp đồng trên Aptos.
    
    Args:
        client (RestClient): Client REST Aptos.
        contract_address (str): Địa chỉ hợp đồng ModernTensor.
        validator_uid (str): UID của validator cần truy vấn.
        
    Returns:
        Optional[Dict[str, Any]]: Thông tin validator nếu có, None nếu không tìm thấy.
    """
    try:
        # Tạo contract client - cần một account dummy cho view functions
        from mt_aptos.account import Account
        dummy_account = Account.generate()  # Temporary account for view functions
        contract_client = AptosContractClient(
            client=client,
            account=dummy_account,
            contract_address=contract_address
        )
        
        # Gọi method để lấy thông tin validator bằng UID
        validator_info = await contract_client.get_validator_info(validator_uid)
        
        # Convert ValidatorInfo object to dict if found
        if validator_info:
            return {
                "uid": validator_info.uid,
                "address": validator_info.address,
                "api_endpoint": validator_info.api_endpoint,
                "trust_score": validator_info.trust_score,
                "weight": validator_info.weight,
                "stake": validator_info.stake,
                "status": validator_info.status,
                "subnet_uid": validator_info.subnet_uid,
                "registration_slot": validator_info.registration_slot
            }
        
        return None
    except Exception as e:
        logger.error(f"Lỗi khi lấy thông tin validator {validator_uid}: {e}")
        return None


async def get_all_validators(
    client: RestClient,
    contract_address: str
) -> Dict[str, Any]:
    """
    Lấy danh sách tất cả các validator từ hợp đồng trên Aptos.
    
    Args:
        client (RestClient): Client REST Aptos.
        contract_address (str): Địa chỉ hợp đồng ModernTensor.
        
    Returns:
        Dict[str, Any]: Dictionary mapping validator UIDs to ValidatorInfo objects.
    """
    try:
        # Tạo contract client - cần một account dummy cho view functions
        from mt_aptos.account import Account
        dummy_account = Account.generate()  # Temporary account for view functions
        contract_client = AptosContractClient(
            client=client,
            account=dummy_account,
            contract_address=contract_address
        )
        
        # Gọi method để lấy tất cả validator
        validators_dict = await contract_client.get_all_validators()
        
        # Return the dict directly
        return validators_dict if validators_dict else {}
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách validator: {e}")
        return {}


async def get_all_miners(
    client: RestClient,
    contract_address: str
) -> Dict[str, Any]:
    """
    Lấy danh sách tất cả các miner từ hợp đồng trên Aptos.
    
    Args:
        client (RestClient): Client REST Aptos.
        contract_address (str): Địa chỉ hợp đồng ModernTensor.
        
    Returns:
        Dict[str, Any]: Dictionary mapping miner UIDs to MinerInfo objects.
    """
    try:
        # Tạo contract client - cần một account dummy cho view functions
        from mt_aptos.account import Account
        dummy_account = Account.generate()  # Temporary account for view functions
        contract_client = AptosContractClient(
            client=client,
            account=dummy_account,
            contract_address=contract_address
        )
        
        # Gọi method để lấy tất cả miner
        miners_dict = await contract_client.get_all_miners()
        
        # Return the dict directly
        return miners_dict if miners_dict else {}
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách miner: {e}")
        return {}


async def is_validator_active(
    client: RestClient,
    contract_address: str,
    validator_uid: str
) -> bool:
    """
    Kiểm tra xem một validator có đang hoạt động hay không.
    
    Args:
        client (RestClient): Client REST Aptos.
        contract_address (str): Địa chỉ hợp đồng ModernTensor.
        validator_uid (str): UID validator cần kiểm tra.
        
    Returns:
        bool: True nếu validator đang hoạt động, False nếu không.
    """
    try:
        validator_info = await get_validator_info(client, contract_address, validator_uid)
        
        if not validator_info:
            return False
            
        # Kiểm tra trạng thái của validator (1 is STATUS_ACTIVE)
        return validator_info.get("status") == 1
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra trạng thái validator {validator_uid}: {e}")
        return False 