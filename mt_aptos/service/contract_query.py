"""
Contract Query Service cho ModernTensor Full Contract
Cung cấp các hàm query thông tin validator và miner
"""

from typing import Optional, Dict, Any, List
from mt_aptos.async_client import RestClient
from mt_aptos.config.settings import settings, logger


class ModernTensorQueryService:
    """Service để query thông tin từ full ModernTensor contract"""
    
    def __init__(self, client: RestClient, contract_address: str):
        self.client = client
        # Ensure contract address has proper format (remove and re-add 0x to normalize)
        clean_address = contract_address.replace("0x", "") if contract_address.startswith("0x") else contract_address
        self.contract_address = f"0x{clean_address}"
    
    async def get_validator_info(self, validator_address: str) -> Optional[Dict[str, Any]]:
        """
        Lấy thông tin validator từ contract
        
        Args:
            validator_address: Địa chỉ validator
            
        Returns:
            Dict với thông tin validator hoặc None nếu không tìm thấy
        """
        try:
            # Format address
            if not validator_address.startswith("0x"):
                validator_address = f"0x{validator_address}"
            
            # Call view function
            result = await self.client.view_function(
                f"{self.contract_address}::moderntensor",
                "get_validator_info",
                [],
                [validator_address]
            )
            
            if result and len(result) > 0:
                # Parse result into dict
                validator_data = result[0]
                return {
                    "uid": validator_data.get("uid", ""),
                    "subnet_uid": int(validator_data.get("subnet_uid", 0)),
                    "stake": int(validator_data.get("stake", 0)),
                    "trust_score": int(validator_data.get("trust_score", 0)),
                    "last_performance": int(validator_data.get("last_performance", 0)),
                    "accumulated_rewards": int(validator_data.get("accumulated_rewards", 0)),
                    "last_update_time": int(validator_data.get("last_update_time", 0)),
                    "performance_history_hash": validator_data.get("performance_history_hash", ""),
                    "wallet_addr_hash": validator_data.get("wallet_addr_hash", ""),
                    "status": int(validator_data.get("status", 0)),
                    "registration_time": int(validator_data.get("registration_time", 0)),
                    "api_endpoint": validator_data.get("api_endpoint", ""),
                    "weight": int(validator_data.get("weight", 0)),
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Could not get validator info for {validator_address}: {e}")
            return None
    
    async def get_miner_info(self, miner_address: str) -> Optional[Dict[str, Any]]:
        """
        Lấy thông tin miner từ contract
        
        Args:
            miner_address: Địa chỉ miner
            
        Returns:
            Dict với thông tin miner hoặc None nếu không tìm thấy
        """
        try:
            # Format address
            if not miner_address.startswith("0x"):
                miner_address = f"0x{miner_address}"
            
            # Call view function
            result = await self.client.view_function(
                f"{self.contract_address}::moderntensor",
                "get_miner_info",
                [],
                [miner_address]
            )
            
            if result and len(result) > 0:
                # Parse result into dict
                miner_data = result[0]
                return {
                    "uid": miner_data.get("uid", ""),
                    "subnet_uid": int(miner_data.get("subnet_uid", 0)),
                    "stake": int(miner_data.get("stake", 0)),
                    "trust_score": int(miner_data.get("trust_score", 0)),
                    "last_performance": int(miner_data.get("last_performance", 0)),
                    "accumulated_rewards": int(miner_data.get("accumulated_rewards", 0)),
                    "last_update_time": int(miner_data.get("last_update_time", 0)),
                    "performance_history_hash": miner_data.get("performance_history_hash", ""),
                    "wallet_addr_hash": miner_data.get("wallet_addr_hash", ""),
                    "status": int(miner_data.get("status", 0)),
                    "registration_time": int(miner_data.get("registration_time", 0)),
                    "api_endpoint": miner_data.get("api_endpoint", ""),
                    "weight": int(miner_data.get("weight", 0)),
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Could not get miner info for {miner_address}: {e}")
            return None
    
    async def is_validator(self, address: str) -> bool:
        """Kiểm tra xem address có phải validator không"""
        try:
            if not address.startswith("0x"):
                address = f"0x{address}"
            
            result = await self.client.view_function(
                f"{self.contract_address}::moderntensor",
                "is_validator",
                [],
                [address]
            )
            
            return bool(result[0]) if result else False
            
        except Exception as e:
            logger.warning(f"Could not check validator status for {address}: {e}")
            return False
    
    async def is_miner(self, address: str) -> bool:
        """Kiểm tra xem address có phải miner không"""
        try:
            if not address.startswith("0x"):
                address = f"0x{address}"
            
            result = await self.client.view_function(
                f"{self.contract_address}::moderntensor",
                "is_miner",
                [],
                [address]
            )
            
            return bool(result[0]) if result else False
            
        except Exception as e:
            logger.warning(f"Could not check miner status for {address}: {e}")
            return False
    
    async def get_validator_weight(self, address: str) -> int:
        """Lấy weight của validator"""
        try:
            if not address.startswith("0x"):
                address = f"0x{address}"
            
            result = await self.client.view_function(
                f"{self.contract_address}::moderntensor",
                "get_validator_weight",
                [],
                [address]
            )
            
            return int(result[0]) if result else 0
            
        except Exception as e:
            logger.warning(f"Could not get validator weight for {address}: {e}")
            return 0
    
    async def get_miner_weight(self, address: str) -> int:
        """Lấy weight của miner"""
        try:
            if not address.startswith("0x"):
                address = f"0x{address}"
            
            result = await self.client.view_function(
                f"{self.contract_address}::moderntensor",
                "get_miner_weight",
                [],
                [address]
            )
            
            return int(result[0]) if result else 0
            
        except Exception as e:
            logger.warning(f"Could not get miner weight for {address}: {e}")
            return 0


# Convenience functions
async def create_query_service(contract_address: Optional[str] = None) -> ModernTensorQueryService:
    """Tạo query service với default config"""
    client = RestClient(settings.APTOS_NODE_URL)
    contract_addr = contract_address or settings.APTOS_CONTRACT_ADDRESS
    return ModernTensorQueryService(client, contract_addr) 