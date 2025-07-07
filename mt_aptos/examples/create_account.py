#!/usr/bin/env python3
"""
Ví dụ về cách tạo và quản lý tài khoản Aptos với ModernTensor HD Wallet
Updated to use HD wallet system instead of old keymanager
"""

import os
import sys
import logging
from getpass import getpass

# Add the parent directory to sys.path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import HD wallet utilities instead of old keymanager
from moderntensor.mt_aptos.keymanager.hd_wallet_manager import AptosHDWalletManager
from moderntensor.mt_aptos.keymanager.wallet_utils import WalletUtils

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    # Tạo thư mục wallets nếu chưa tồn tại
    wallets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wallets")
    os.makedirs(wallets_dir, exist_ok=True)
    
    # Khởi tạo HD Wallet Manager và Utilities
    hd_wallet = AptosHDWalletManager(base_dir=wallets_dir)
    utils = WalletUtils(base_dir=wallets_dir)
    
    print("\n=== ModernTensor Aptos HD Wallet Manager ===\n")
    print("1. Create a new HD wallet")
    print("2. Create coldkey in existing wallet")
    print("3. Create hotkey in existing wallet")
    print("4. List all wallets")
    print("5. Show wallet/account details")
    print("6. Import account by private key")
    print("7. Export private key")
    print("8. Load account for use")
    print("0. Exit")
    
    choice = input("\nEnter your choice (0-8): ")
    
    if choice == "1":
        # Tạo HD wallet mới
        wallet_name = input("Enter a name for the new HD wallet: ")
        password = getpass("Enter a password to encrypt the wallet: ")
        confirm_password = getpass("Confirm password: ")
        
        if password != confirm_password:
            logger.error("Passwords do not match!")
            return
        
        # Chọn số từ trong mnemonic
        word_count = input("Enter number of words for mnemonic (12 or 24, default 24): ").strip()
        word_count = int(word_count) if word_count in ['12', '24'] else 24
        
        try:
            mnemonic = hd_wallet.create_wallet(wallet_name, password, word_count)
            print(f"\nHD Wallet created successfully!")
            print(f"Wallet name: {wallet_name}")
            print(f"Mnemonic phrase: {mnemonic}")
            print("⚠️  IMPORTANT: Store this mnemonic securely! It's the only way to recover your wallet.")
        except Exception as e:
            logger.error(f"Error creating HD wallet: {e}")
    
    elif choice == "2":
        # Tạo coldkey trong wallet hiện tại
        wallet_name = input("Enter wallet name: ")
        coldkey_name = input("Enter coldkey name: ")
        password = getpass("Enter wallet password: ")
        
        try:
            hd_wallet.load_wallet(wallet_name, password)
            coldkey_info = hd_wallet.create_coldkey(wallet_name, coldkey_name)
            print(f"\nColdkey created successfully!")
            print(f"Coldkey name: {coldkey_name}")
            print(f"Address: {coldkey_info['address']}")
            print(f"Derivation path: {coldkey_info['derivation_path']}")
        except Exception as e:
            logger.error(f"Error creating coldkey: {e}")
    
    elif choice == "3":
        # Tạo hotkey trong wallet hiện tại
        wallet_name = input("Enter wallet name: ")
        coldkey_name = input("Enter coldkey name: ")
        hotkey_name = input("Enter hotkey name: ")
        password = getpass("Enter wallet password: ")
        
        try:
            hd_wallet.load_wallet(wallet_name, password)
            hotkey_info = hd_wallet.create_hotkey(wallet_name, coldkey_name, hotkey_name)
            print(f"\nHotkey created successfully!")
            print(f"Hotkey name: {hotkey_name}")
            print(f"Address: {hotkey_info['address']}")
            print(f"Derivation path: {hotkey_info['derivation_path']}")
        except Exception as e:
            logger.error(f"Error creating hotkey: {e}")
    
    elif choice == "4":
        # Liệt kê tất cả wallets
        try:
            utils.show_all_wallets()
        except Exception as e:
            logger.error(f"Error listing wallets: {e}")
    
    elif choice == "5":
        # Hiển thị chi tiết wallet/account
        wallet_name = input("Enter wallet name: ")
        password = getpass("Enter wallet password: ")
        
        try:
            hd_wallet.load_wallet(wallet_name, password)
            hd_wallet.display_wallet_info(wallet_name)
        except Exception as e:
            logger.error(f"Error loading wallet: {e}")
    
    elif choice == "6":
        # Nhập private key
        wallet_name = input("Enter wallet name to import into: ")
        account_name = input("Enter a name for the imported account: ")
        private_key_hex = getpass("Enter private key (hex): ")
        password = getpass("Enter wallet password: ")
        
        try:
            # Clean private key format
            if private_key_hex.startswith("0x"):
                private_key_hex = private_key_hex[2:]
            
            hd_wallet.load_wallet(wallet_name, password)
            account_info = hd_wallet.import_account_by_private_key(wallet_name, private_key_hex, account_name)
            print(f"\nAccount imported successfully!")
            print(f"Account name: {account_name}")
            print(f"Address: {account_info['address']}")
        except Exception as e:
            logger.error(f"Error importing private key: {e}")
    
    elif choice == "7":
        # Export private key
        wallet_name = input("Enter wallet name: ")
        coldkey_name = input("Enter coldkey name: ")
        hotkey_name = input("Enter hotkey name (leave empty for coldkey): ").strip()
        password = getpass("Enter wallet password: ")
        
        if not hotkey_name:
            hotkey_name = None
        
        try:
            hd_wallet.load_wallet(wallet_name, password)
            private_key = hd_wallet.export_private_key(wallet_name, coldkey_name, hotkey_name)
            
            if hotkey_name:
                print(f"\nPrivate key for {wallet_name}.{coldkey_name}.{hotkey_name}:")
            else:
                print(f"\nPrivate key for {wallet_name}.{coldkey_name}:")
            
            print(f"0x{private_key}")
            print("⚠️  IMPORTANT: Keep this private key secure! Anyone with this key can control your account.")
        except Exception as e:
            logger.error(f"Error exporting private key: {e}")
    
    elif choice == "8":
        # Load account for use
        wallet_name = input("Enter wallet name: ")
        coldkey_name = input("Enter coldkey name: ")
        hotkey_name = input("Enter hotkey name: ")
        password = getpass("Enter wallet password: ")
        
        try:
            account = utils.quick_load_account(wallet_name, coldkey_name, hotkey_name, password)
            
            if account:
                print(f"\nAccount loaded successfully!")
                print(f"Wallet path: {wallet_name}.{coldkey_name}.{hotkey_name}")
                print(f"Address: {str(account.address())}")
                print(f"Public Key: {str(account.public_key())}")
            else:
                print("Failed to load account. Please check your credentials.")
        except Exception as e:
            logger.error(f"Error loading account: {e}")
    
    elif choice == "0":
        print("Exiting...")
    
    else:
        print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main() 