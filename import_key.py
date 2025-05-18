#!/usr/bin/env python3
"""
Script để nhập khóa từ Aptos vào ModernTensor
"""

import sys
from keymanager import AccountKeyManager

def main():
    # Tạo AccountKeyManager với thư mục wallets
    key_manager = AccountKeyManager(base_dir="./examples/wallets")
    
    # Nhập khóa private từ Aptos
    private_key = "CEBFFEE02B18741D2F6467E0A82684F32C68CEF26B68095D8BBC5C6881555587"
    account_name = "myaptos"
    password = "password123"  # Trong thực tế, nên dùng mật khẩu mạnh hơn
    
    try:
        account = key_manager.import_private_key(account_name, private_key, password)
        print(f"\nTài khoản đã được nhập thành công!")
        print(f"Địa chỉ: {account.address().hex()}")
    except Exception as e:
        print(f"Lỗi khi nhập khóa: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 