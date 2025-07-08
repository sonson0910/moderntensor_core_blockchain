"""
Dịch vụ tài khoản Aptos để quản lý tài khoản, kiểm tra số dư và thực hiện giao dịch cơ bản.
Thay thế chức năng của UTxO trong Cardano.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Tuple

from mt_core.account import Account
from mt_core.async_client import RestClient
from mt_core.transactions import EntryFunction, TransactionArgument, TransactionPayload
from mt_core.type_tag import TypeTag, StructTag

from mt_core.config.settings import settings
from .address import get_aptos_address

logger = logging.getLogger(__name__)


async def get_account_resources(client: RestClient, account_address: str) -> List[Dict[str, Any]]:
    """
    Lấy tất cả tài nguyên của một tài khoản Aptos.

    Args:
        client (RestClient): Client REST Aptos.
        account_address (str): Địa chỉ tài khoản cần kiểm tra.

    Returns:
        List[Dict[str, Any]]: Danh sách các tài nguyên tài khoản.
    """
    try:
        # Đảm bảo địa chỉ có định dạng đúng (với tiền tố 0x)
        if not account_address.startswith("0x"):
            account_address = f"0x{account_address}"
            
        resources = await client.account_resources(account_address)
        return resources
    except Exception as e:
        logger.error(f"Lỗi khi lấy tài nguyên tài khoản {account_address}: {e}")
        return []


async def get_account_balance(
    client: RestClient, 
    account_address: str, 
    coin_type: str = "0x1::aptos_coin::AptosCoin"
) -> int:
    """
    Lấy số dư của một tài khoản Aptos cho một loại coin cụ thể.
    Support both old CoinStore và new FungibleAsset framework.

    Args:
        client (RestClient): Client REST Aptos.
        account_address (str): Địa chỉ tài khoản cần kiểm tra.
        coin_type (str): Loại coin cần kiểm tra. Mặc định là AptosCoin.

    Returns:
        int: Số dư hiện tại. Trả về 0 nếu tài khoản không tồn tại hoặc không có tài nguyên coin.
    """
    import aiohttp
    
    try:
        # Method 1: Try old CoinStore first (for backwards compatibility)
        resources = await get_account_resources(client, account_address)
        coin_store_type = f"0x1::coin::CoinStore<{coin_type}>"
        
        for resource in resources:
            if resource["type"] == coin_store_type:
                balance = int(resource["data"]["coin"]["value"])
                logger.debug(f"Found APT balance via CoinStore: {balance} octas")
                return balance
        
        # Method 2: Try FungibleAsset (new method) for APT only
        if coin_type == "0x1::aptos_coin::AptosCoin":
            async with aiohttp.ClientSession() as session:
                # Get owned objects
                view_payload = {
                    "function": "0x1::object::object_addresses_owned_by",
                    "type_arguments": [],
                    "arguments": [account_address]
                }
                
                # Determine node URL from client
                node_url = str(client.base_url).rstrip('/')
                view_url = f"{node_url}/view"
                
                async with session.post(view_url, json=view_payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result and result[0]:
                            owned_objects = result[0]
                            
                            # Check each object for APT FungibleStore
                            for obj_addr in owned_objects:
                                store_url = f"{node_url}/accounts/{obj_addr}/resource/0x1::fungible_asset::FungibleStore"
                                async with session.get(store_url) as store_response:
                                    if store_response.status == 200:
                                        store_data = await store_response.json()
                                        balance = store_data.get("data", {}).get("balance", "0")
                                        metadata = store_data.get("data", {}).get("metadata", {}).get("inner", "")
                                        
                                        # Check if this is APT (metadata = 0xa)
                                        if metadata == "0x000000000000000000000000000000000000000000000000000000000000000a" or metadata == "0xa":
                                            balance_value = int(balance)
                                            logger.debug(f"Found APT balance via FungibleStore: {balance_value} octas")
                                            return balance_value
                
        # Không tìm thấy tài nguyên coin
        logger.warning(f"Không tìm thấy {coin_type} trong tài khoản {account_address}")
        return 0
    except Exception as e:
        logger.error(f"Lỗi khi lấy số dư tài khoản {account_address}: {e}")
        return 0


async def transfer_coins(
    client: RestClient,
    sender: Account,
    recipient_address: str,
    amount: int,
    coin_type: str = "0x1::aptos_coin::AptosCoin",
    gas_unit_price: Optional[int] = None,
    max_gas_amount: Optional[int] = None,
) -> Optional[str]:
    """
    Chuyển coin từ tài khoản người gửi đến người nhận.

    Args:
        client (RestClient): Client REST Aptos.
        sender (Account): Tài khoản người gửi với private key để ký giao dịch.
        recipient_address (str): Địa chỉ người nhận.
        amount (int): Số lượng coin cần chuyển.
        coin_type (str): Loại coin cần chuyển. Mặc định là AptosCoin.
        gas_unit_price (Optional[int]): Giá gas tùy chọn.
        max_gas_amount (Optional[int]): Số lượng gas tối đa tùy chọn.

    Returns:
        Optional[str]: Hash giao dịch nếu thành công, None nếu thất bại.
    """
    try:
        # Đảm bảo địa chỉ người nhận có định dạng đúng
        if not recipient_address.startswith("0x"):
            recipient_address = f"0x{recipient_address}"
            
        # Tạo và ký giao dịch
        payload = EntryFunction.natural(
            "0x1::coin",
            "transfer",
            [TypeTag(StructTag.from_str(coin_type))],
            [
                TransactionArgument(recipient_address, "address"), 
                TransactionArgument(amount, "u64")
            ]
        )
        
        # Gửi giao dịch
        signed_transaction = await client.create_bcs_signed_transaction(
            sender, 
            payload,  # Đơn giản hóa, không cần TransactionPayload wrapper
            gas_unit_price=gas_unit_price,
            max_gas_amount=max_gas_amount
        )
        
        tx_hash = await client.submit_bcs_transaction(signed_transaction)
        await client.wait_for_transaction(tx_hash)
        
        logger.info(f"Chuyển {amount} {coin_type} thành công từ {sender.address()} đến {recipient_address}")
        return tx_hash
    except Exception as e:
        logger.error(f"Lỗi khi chuyển coin: {e}")
        return None
        
        
async def check_account_exists(client: RestClient, account_address: str) -> bool:
    """
    Kiểm tra xem một tài khoản có tồn tại trên blockchain hay không.

    Args:
        client (RestClient): Client REST Aptos.
        account_address (str): Địa chỉ tài khoản cần kiểm tra.

    Returns:
        bool: True nếu tài khoản tồn tại, False nếu không.
    """
    try:
        # Đảm bảo địa chỉ có định dạng đúng
        if not account_address.startswith("0x"):
            account_address = f"0x{account_address}"
            
        await client.account_resources(account_address)
        return True
    except Exception:
        return False 