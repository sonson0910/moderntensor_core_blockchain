#!/usr/bin/env python3
"""
Ví dụ về cách tạo và quản lý tài khoản Aptos với ModernTensor Aptos SDK
"""

import os
import sys
import logging
from getpass import getpass

# Add the parent directory to sys.path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from keymanager import AccountKeyManager

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    # Tạo thư mục wallets nếu chưa tồn tại
    wallets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wallets")
    os.makedirs(wallets_dir, exist_ok=True)
    
    # Khởi tạo AccountKeyManager
    key_manager = AccountKeyManager(base_dir=wallets_dir)
    
    print("\n=== ModernTensor Aptos Account Manager ===\n")
    print("1. Create a new account")
    print("2. List all accounts")
    print("3. Show account details")
    print("4. Import private key")
    print("5. Delete account")
    print("0. Exit")
    
    choice = input("\nEnter your choice (0-5): ")
    
    if choice == "1":
        # Tạo tài khoản mới
        account_name = input("Enter a name for the new account: ")
        password = getpass("Enter a password to encrypt the account: ")
        confirm_password = getpass("Confirm password: ")
        
        if password != confirm_password:
            logger.error("Passwords do not match!")
            return
        
        try:
            account = key_manager.create_account(account_name, password)
            print(f"\nAccount created successfully!")
            print(f"Address: {account.address().hex()}")
        except Exception as e:
            logger.error(f"Error creating account: {e}")
    
    elif choice == "2":
        # Liệt kê tất cả tài khoản
        accounts = key_manager.list_accounts()
        
        if not accounts:
            print("\nNo accounts found.")
        else:
            print("\n=== Available Accounts ===")
            for i, account in enumerate(accounts, 1):
                print(f"{i}. {account['name']} - {account['address']}")
    
    elif choice == "3":
        # Hiển thị chi tiết tài khoản
        account_name = input("Enter account name: ")
        password = getpass("Enter password: ")
        
        try:
            account = key_manager.load_account(account_name, password)
            print(f"\nAccount Address: {account.address().hex()}")
            print(f"Public Key: {account.public_key()}")
        except Exception as e:
            logger.error(f"Error loading account: {e}")
    
    elif choice == "4":
        # Nhập private key
        account_name = input("Enter a name for the imported account: ")
        private_key_hex = getpass("Enter private key (hex): ")
        password = getpass("Enter a password to encrypt the account: ")
        confirm_password = getpass("Confirm password: ")
        
        if password != confirm_password:
            logger.error("Passwords do not match!")
            return
        
        try:
            account = key_manager.import_private_key(account_name, private_key_hex, password)
            print(f"\nAccount imported successfully!")
            print(f"Address: {account.address().hex()}")
        except Exception as e:
            logger.error(f"Error importing private key: {e}")
    
    elif choice == "5":
        # Xóa tài khoản
        account_name = input("Enter account name to delete: ")
        password = getpass("Enter password to confirm deletion: ")
        
        try:
            success = key_manager.delete_account(account_name, password)
            if success:
                print(f"\nAccount '{account_name}' deleted successfully!")
            else:
                print(f"\nFailed to delete account '{account_name}'.")
        except Exception as e:
            logger.error(f"Error deleting account: {e}")
    
    elif choice == "0":
        print("Exiting...")
    
    else:
        print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main() 