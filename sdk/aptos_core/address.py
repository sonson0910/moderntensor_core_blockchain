"""
Hàm tiện ích để xử lý địa chỉ Aptos
"""

from aptos_sdk.account import Account
from typing import Optional
from sdk.config.settings import settings, logger


def get_aptos_address(
    account: Account,
    format_hex: bool = True,
) -> str:
    """
    Lấy địa chỉ Aptos từ đối tượng Account.

    Args:
        account (Account): Đối tượng Account Aptos.
        format_hex (bool): Nếu True, trả về chuỗi dạng 0x prefixed hex. Mặc định là True.

    Returns:
        str: Địa chỉ Aptos ở dạng chuỗi.
    """
    if not account:
        raise ValueError("Account không được phép là None")

    address = account.address()
    
    if format_hex:
        # Đảm bảo địa chỉ luôn có tiền tố 0x
        if isinstance(address, str):
            if not address.startswith("0x"):
                return f"0x{address}"
            return address
        else:
            # Nếu là đối tượng AccountAddress, chuyển thành chuỗi hex
            hex_str = address.hex()
            if not hex_str.startswith("0x"):
                return f"0x{hex_str}"
            return hex_str
    else:
        # Trả về dưới dạng chuỗi mà không có tiền tố 0x
        if isinstance(address, str):
            if address.startswith("0x"):
                return address[2:]
            return address
        else:
            hex_str = address.hex()
            if hex_str.startswith("0x"):
                return hex_str[2:]
            return hex_str 