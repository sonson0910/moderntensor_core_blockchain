#!/usr/bin/env python3
"""
Ví dụ về cách tạo và quản lý tài khoản Core blockchain với ModernTensor
Updated to use Core blockchain with eth-account
"""

import os
import sys
import logging
import json
from getpass import getpass
from web3 import Web3

# Add the parent directory to sys.path for imports
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# Import Core blockchain utilities
from ..account import CoreAccount, Account
from ..config.settings import Settings

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CoreAccountManager:
    """Manager for Core blockchain accounts"""

    def __init__(self, wallets_dir: str = "./wallets"):
        self.wallets_dir = wallets_dir
        self.settings = Settings()
        os.makedirs(wallets_dir, exist_ok=True)

    def create_new_account(self, account_name: str, password: str) -> dict:
        """Create a new Core blockchain account"""
        try:
            # Create new account
            core_account = CoreAccount()

            # Save encrypted account
            account_file = os.path.join(self.wallets_dir, f"{account_name}.json")
            encrypted_account = Account.encrypt(core_account.account.key, password)

            with open(account_file, "w") as f:
                json.dump(encrypted_account, f, indent=2)

            logger.info(f"Account '{account_name}' created successfully")

            return {
                "name": account_name,
                "address": core_account.address,
                "file": account_file,
            }
        except Exception as e:
            logger.error(f"Error creating account: {e}")
            raise

    def load_account(self, account_name: str, password: str) -> CoreAccount:
        """Load an existing account"""
        try:
            account_file = os.path.join(self.wallets_dir, f"{account_name}.json")

            if not os.path.exists(account_file):
                raise FileNotFoundError(f"Account file not found: {account_file}")

            with open(account_file, "r") as f:
                encrypted_account = json.load(f)

            # Decrypt account
            private_key = Account.decrypt(encrypted_account, password)
            return CoreAccount(private_key.hex())

        except Exception as e:
            logger.error(f"Error loading account: {e}")
            raise

    def import_account(
        self, account_name: str, private_key: str, password: str
    ) -> dict:
        """Import account from private key"""
        try:
            # Clean private key format
            if private_key.startswith("0x"):
                private_key = private_key[2:]

            # Create account from private key
            account = Account.from_key(private_key)

            # Save encrypted account
            account_file = os.path.join(self.wallets_dir, f"{account_name}.json")
            encrypted_account = Account.encrypt(account.key, password)

            with open(account_file, "w") as f:
                json.dump(encrypted_account, f, indent=2)

            logger.info(f"Account '{account_name}' imported successfully")

            return {
                "name": account_name,
                "address": account.address,
                "file": account_file,
            }
        except Exception as e:
            logger.error(f"Error importing account: {e}")
            raise

    def list_accounts(self) -> list:
        """List all accounts in wallets directory"""
        accounts = []
        try:
            for file in os.listdir(self.wallets_dir):
                if file.endswith(".json"):
                    account_name = file[:-5]  # Remove .json extension
                    accounts.append(account_name)
        except Exception as e:
            logger.error(f"Error listing accounts: {e}")

        return accounts

    def get_account_balance(self, account: CoreAccount) -> dict:
        """Get account balance from Core blockchain"""
        try:
            w3 = Web3(Web3.HTTPProvider(self.settings.CORE_NODE_URL))

            # Get CORE token balance
            core_balance = w3.eth.get_balance(account.address)
            core_balance_ether = w3.from_wei(core_balance, "ether")

            return {
                "address": account.address,
                "core_balance": float(core_balance_ether),
                "core_balance_wei": core_balance,
            }
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return {"error": str(e)}


def main():
    # Tạo thư mục wallets nếu chưa tồn tại
    wallets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wallets")
    account_manager = CoreAccountManager(wallets_dir)

    print("\n=== ModernTensor Core Blockchain Account Manager ===\n")
    print("1. Create a new Core account")
    print("2. Load existing account")
    print("3. Import account from private key")
    print("4. List all accounts")
    print("5. Check account balance")
    print("6. Export private key")
    print("7. Get account info")
    print("8. Network information")
    print("0. Exit")

    choice = input("\nEnter your choice (0-8): ")

    if choice == "1":
        # Tạo tài khoản mới
        account_name = input("Enter a name for the new account: ")
        password = getpass("Enter a password to encrypt the account: ")
        confirm_password = getpass("Confirm password: ")

        if password != confirm_password:
            logger.error("Passwords do not match!")
            return

        try:
            account_info = account_manager.create_new_account(account_name, password)
            print(f"\nCore account created successfully!")
            print(f"Account name: {account_info['name']}")
            print(f"Address: {account_info['address']}")
            print(f"File: {account_info['file']}")
            print(
                "⚠️  IMPORTANT: Store your password securely! It's needed to access your account."
            )
        except Exception as e:
            logger.error(f"Error creating account: {e}")

    elif choice == "2":
        # Load tài khoản hiện có
        account_name = input("Enter account name: ")
        password = getpass("Enter account password: ")

        try:
            account = account_manager.load_account(account_name, password)
            print(f"\nAccount loaded successfully!")
            print(f"Account name: {account_name}")
            print(f"Address: {account.address}")
            print(f"Public Key: {account.public_key}")
        except Exception as e:
            logger.error(f"Error loading account: {e}")

    elif choice == "3":
        # Import private key
        account_name = input("Enter a name for the imported account: ")
        private_key = getpass("Enter private key (hex): ")
        password = getpass("Enter password to encrypt the account: ")

        try:
            account_info = account_manager.import_account(
                account_name, private_key, password
            )
            print(f"\nAccount imported successfully!")
            print(f"Account name: {account_info['name']}")
            print(f"Address: {account_info['address']}")
            print(f"File: {account_info['file']}")
        except Exception as e:
            logger.error(f"Error importing account: {e}")

    elif choice == "4":
        # Liệt kê tất cả accounts
        try:
            accounts = account_manager.list_accounts()
            if accounts:
                print(f"\nFound {len(accounts)} accounts:")
                for i, account_name in enumerate(accounts, 1):
                    print(f"{i}. {account_name}")
            else:
                print("\nNo accounts found.")
        except Exception as e:
            logger.error(f"Error listing accounts: {e}")

    elif choice == "5":
        # Kiểm tra balance
        account_name = input("Enter account name: ")
        password = getpass("Enter account password: ")

        try:
            account = account_manager.load_account(account_name, password)
            balance_info = account_manager.get_account_balance(account)

            if "error" in balance_info:
                print(f"Error getting balance: {balance_info['error']}")
            else:
                print(f"\nAccount Balance:")
                print(f"Address: {balance_info['address']}")
                print(f"CORE Balance: {balance_info['core_balance']} CORE")
                print(f"Balance (Wei): {balance_info['core_balance_wei']}")
        except Exception as e:
            logger.error(f"Error checking balance: {e}")

    elif choice == "6":
        # Export private key
        account_name = input("Enter account name: ")
        password = getpass("Enter account password: ")

        try:
            account = account_manager.load_account(account_name, password)
            print(f"\nPrivate key for {account_name}:")
            print(f"{account.private_key}")
            print(
                "⚠️  IMPORTANT: Keep this private key secure! Anyone with this key can control your account."
            )
        except Exception as e:
            logger.error(f"Error exporting private key: {e}")

    elif choice == "7":
        # Get account info
        account_name = input("Enter account name: ")
        password = getpass("Enter account password: ")

        try:
            account = account_manager.load_account(account_name, password)
            balance_info = account_manager.get_account_balance(account)

            print(f"\nAccount Information:")
            print(f"Name: {account_name}")
            print(f"Address: {account.address}")
            print(f"Public Key: {account.public_key}")

            if "error" not in balance_info:
                print(f"CORE Balance: {balance_info['core_balance']} CORE")

        except Exception as e:
            logger.error(f"Error getting account info: {e}")

    elif choice == "8":
        # Network information
        settings = Settings()
        print(f"\nCore Blockchain Network Information:")
        print(f"Network: {settings.CORE_NETWORK}")
        print(f"RPC URL: {settings.CORE_NODE_URL}")
        print(f"Chain ID: {settings.CORE_CHAIN_ID}")
        print(f"Contract Address: {settings.CORE_CONTRACT_ADDRESS}")
        print(f"CORE Token Address: {settings.CORE_TOKEN_ADDRESS}")
        print(f"Bitcoin Staking Enabled: {settings.BITCOIN_STAKING_ENABLED}")
        print(f"Dual Staking Enabled: {settings.DUAL_STAKING_ENABLED}")

    elif choice == "0":
        print("Exiting...")

    else:
        print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
