"""
Contract Query Service cho ModernTensor Smart Contract trên Core blockchain
Cung cấp các hàm query thông tin validator và miner
"""

from typing import Optional, Dict, Any, List
from ..core_client.contract_client import ModernTensorCoreClient
from ..config.settings import settings, logger


class ModernTensorQueryService:
    """Service để query thông tin từ ModernTensor smart contract trên Core blockchain"""

    def __init__(self, client: ModernTensorCoreClient, contract_address: str):
        self.client = client
        self.contract_address = contract_address

    async def get_validator_info(
        self, validator_address: str
    ) -> Optional[Dict[str, Any]]:
        """
        Lấy thông tin validator từ contract

        Args:
            validator_address: Địa chỉ validator

        Returns:
            Dict với thông tin validator hoặc None nếu không tìm thấy
        """
        try:
            # ModernTensorCoreClient doesn't have getValidatorInfo method yet
            # Return placeholder for now
            logger.warning(
                f"getValidatorInfo not implemented yet for {validator_address}"
            )
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
            # Use the actual get_miner_info method from ModernTensorCoreClient
            result = self.client.get_miner_info(miner_address)

            if result:
                return {
                    "uid": result.get("uid", ""),
                    "subnet_uid": int(result.get("subnetUid", 0)),
                    "stake": int(result.get("stake", 0)),
                    "trust_score": int(result.get("trustScore", 0)),
                    "last_performance": int(result.get("lastPerformance", 0)),
                    "accumulated_rewards": int(result.get("accumulatedRewards", 0)),
                    "last_update_time": int(result.get("lastUpdateTime", 0)),
                    "performance_history_hash": result.get(
                        "performanceHistoryHash", ""
                    ),
                    "wallet_addr_hash": result.get("walletAddrHash", ""),
                    "status": int(result.get("status", 0)),
                    "registration_time": int(result.get("registrationTime", 0)),
                    "api_endpoint": result.get("apiEndpoint", ""),
                    "weight": int(result.get("weight", 0)),
                }

            return None

        except Exception as e:
            logger.warning(f"Could not get miner info for {miner_address}: {e}")
            return None

    async def is_validator(self, address: str) -> bool:
        """Kiểm tra xem address có phải validator không"""
        try:
            # This method is not implemented in ModernTensorCoreClient yet
            logger.warning(f"isValidator not implemented yet for {address}")
            return False

        except Exception as e:
            logger.warning(f"Could not check validator status for {address}: {e}")
            return False

    async def is_miner(self, address: str) -> bool:
        """Kiểm tra xem address có phải miner không"""
        try:
            # This method is not implemented in ModernTensorCoreClient yet
            logger.warning(f"isMiner not implemented yet for {address}")
            return False

        except Exception as e:
            logger.warning(f"Could not check miner status for {address}: {e}")
            return False

    async def get_validator_weight(self, address: str) -> int:
        """Lấy weight của validator"""
        try:
            # This method is not implemented in ModernTensorCoreClient yet
            logger.warning(f"getValidatorWeight not implemented yet for {address}")
            return 0

        except Exception as e:
            logger.warning(f"Could not get validator weight for {address}: {e}")
            return 0

    async def get_miner_weight(self, address: str) -> int:
        """Lấy weight của miner"""
        try:
            # This method is not implemented in ModernTensorCoreClient yet
            logger.warning(f"getMinerWeight not implemented yet for {address}")
            return 0

        except Exception as e:
            logger.warning(f"Could not get miner weight for {address}: {e}")
            return 0


# Convenience functions
async def create_query_service(
    contract_address: Optional[str] = None,
) -> ModernTensorQueryService:
    """Tạo query service với default config"""
    # Use Core blockchain testnet by default
    from web3 import Web3

    w3 = Web3(Web3.HTTPProvider("https://rpc.test.btcs.network"))
    contract_addr = contract_address or getattr(
        settings, "CONTRACT_ADDRESS", "0x0000000000000000000000000000000000000000"
    )

    client = ModernTensorCoreClient(w3=w3, contract_address=contract_addr, account=None)
    return ModernTensorQueryService(client, contract_addr)
