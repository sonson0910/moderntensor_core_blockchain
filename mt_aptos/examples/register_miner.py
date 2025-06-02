#!/usr/bin/env python3
"""
Ví dụ về cách đăng ký một miner mới trên ModernTensor sử dụng Aptos SDK
"""

import os
import sys
import asyncio
import logging
import binascii
import argparse
from getpass import getpass

# Add the parent directory to sys.path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mt_aptos.keymanager import AccountKeyManager
from mt_aptos.aptos_core import ModernTensorClient

from mt_aptos.client import RestClient

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Node URL
DEFAULT_NODE_URL = "https://fullnode.devnet.aptoslabs.com"
DEFAULT_SUBNET_UID = 1
DEFAULT_STAKE_AMOUNT = 10_000_000  # 0.1 APT, assuming 8 decimals
CONTRACT_ADDRESS = "0xcafe"  # Default test address

async def register_miner(
    account_name: str,
    password: str,
    api_endpoint: str,
    wallets_dir: str = "./wallets",
    node_url: str = DEFAULT_NODE_URL,
    subnet_uid: int = DEFAULT_SUBNET_UID,
    stake_amount: int = DEFAULT_STAKE_AMOUNT,
):
    """
    Đăng ký một miner mới trên ModernTensor.

    Args:
        account_name: Tên tài khoản để sử dụng.
        password: Mật khẩu để giải mã tài khoản.
        api_endpoint: API endpoint của miner.
        wallets_dir: Thư mục chứa ví.
        node_url: URL của Aptos node.
        subnet_uid: UID của subnet đăng ký.
        stake_amount: Số lượng stake (đã scale).
    """
    # Khởi tạo AccountKeyManager
    key_manager = AccountKeyManager(base_dir=wallets_dir)
    
    # Tải tài khoản
    try:
        account = key_manager.load_account(account_name, password)
        logger.info(f"Loaded account with address: {account.address().hex()}")
    except Exception as e:
        logger.error(f"Error loading account: {e}")
        return
    
    # Khởi tạo Aptos REST client
    rest_client = RestClient(node_url)
    
    # Khởi tạo ModernTensorClient
    client = ModernTensorClient(
        account=account,
        client=rest_client,
        moderntensor_address=CONTRACT_ADDRESS,
    )
    
    # Tạo UID ngẫu nhiên cho miner
    miner_uid = os.urandom(16)  # Tạo 16 bytes ngẫu nhiên cho UID
    logger.info(f"Generated miner UID: {miner_uid.hex()}")
    
    # Hiển thị thông tin trước khi gửi giao dịch
    print(f"\n=== Registration Information ===")
    print(f"Account Address: {account.address().hex()}")
    print(f"Miner UID: {miner_uid.hex()}")
    print(f"Subnet UID: {subnet_uid}")
    print(f"Stake Amount: {stake_amount / 100_000_000} APT")
    print(f"API Endpoint: {api_endpoint}")
    
    # Xác nhận từ người dùng
    confirm = input("\nConfirm registration? (y/n): ")
    if confirm.lower() != 'y':
        logger.info("Registration cancelled.")
        return
    
    # Gửi giao dịch đăng ký
    try:
        logger.info("Registering miner...")
        txn_hash = await client.register_miner(
            uid=miner_uid,
            subnet_uid=subnet_uid,
            stake_amount=stake_amount,
            api_endpoint=api_endpoint,
        )
        logger.info(f"Registration successful! Transaction hash: {txn_hash}")
    except Exception as e:
        logger.error(f"Error registering miner: {e}")

def main():
    parser = argparse.ArgumentParser(description="Register a new miner on ModernTensor Aptos network")
    parser.add_argument("--account", required=True, help="Account name to use")
    parser.add_argument("--api", required=True, help="API endpoint of the miner")
    parser.add_argument("--subnet", type=int, default=DEFAULT_SUBNET_UID, help="Subnet UID to register to")
    parser.add_argument("--stake", type=int, default=DEFAULT_STAKE_AMOUNT, help="Stake amount (in lowest denomination)")
    parser.add_argument("--node", default=DEFAULT_NODE_URL, help="Aptos node URL")
    parser.add_argument("--wallets", default="./wallets", help="Wallets directory")
    
    args = parser.parse_args()
    
    # Lấy mật khẩu từ người dùng
    password = getpass(f"Enter password for account '{args.account}': ")
    
    # Chạy hàm đăng ký miner
    asyncio.run(register_miner(
        account_name=args.account,
        password=password,
        api_endpoint=args.api,
        wallets_dir=args.wallets,
        node_url=args.node,
        subnet_uid=args.subnet,
        stake_amount=args.stake,
    ))

if __name__ == "__main__":
    main() 