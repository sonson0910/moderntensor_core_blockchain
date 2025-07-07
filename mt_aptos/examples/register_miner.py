#!/usr/bin/env python3
"""
Ví dụ về cách đăng ký một miner mới trên ModernTensor sử dụng HD Wallet
Updated to use HD wallet system instead of old keymanager
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

# Import HD wallet utilities instead of old keymanager
from moderntensor.mt_aptos.keymanager.wallet_utils import WalletUtils
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
    wallet_name: str,
    coldkey_name: str,
    hotkey_name: str,
    wallet_password: str,
    api_endpoint: str,
    wallets_dir: str = "./wallets",
    node_url: str = DEFAULT_NODE_URL,
    subnet_uid: int = DEFAULT_SUBNET_UID,
    stake_amount: int = DEFAULT_STAKE_AMOUNT,
):
    """
    Đăng ký một miner mới trên ModernTensor sử dụng HD wallet.

    Args:
        wallet_name: Tên HD wallet.
        coldkey_name: Tên coldkey trong HD wallet.
        hotkey_name: Tên hotkey trong HD wallet.
        wallet_password: Mật khẩu HD wallet.
        api_endpoint: API endpoint của miner.
        wallets_dir: Thư mục chứa HD wallets.
        node_url: URL của Aptos node.
        subnet_uid: UID của subnet đăng ký.
        stake_amount: Số lượng stake (đã scale).
    """
    # Khởi tạo WalletUtils
    utils = WalletUtils(base_dir=wallets_dir)
    
    # Tải tài khoản từ HD wallet
    try:
        account = utils.quick_load_account(wallet_name, coldkey_name, hotkey_name, wallet_password)
        if not account:
            logger.error("Failed to load account from HD wallet")
            logger.error("Please make sure the wallet, coldkey, and hotkey exist and password is correct")
            logger.error("Create them using:")
            logger.error(f"  python -m moderntensor.mt_aptos.cli.main hdwallet create --name {wallet_name}")
            logger.error(f"  python -m moderntensor.mt_aptos.cli.main hdwallet create-coldkey --wallet {wallet_name} --name {coldkey_name}")
            logger.error(f"  python -m moderntensor.mt_aptos.cli.main hdwallet create-hotkey --wallet {wallet_name} --coldkey {coldkey_name} --name {hotkey_name}")
            return
        
        logger.info(f"Loaded account from HD wallet: {wallet_name}.{coldkey_name}.{hotkey_name}")
        logger.info(f"Account address: {str(account.address())}")
    except Exception as e:
        logger.error(f"Error loading account from HD wallet: {e}")
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
    print(f"HD Wallet: {wallet_name}.{coldkey_name}.{hotkey_name}")
    print(f"Account Address: {str(account.address())}")
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
        print(f"\n✅ Miner registered successfully!")
        print(f"Transaction hash: {txn_hash}")
        print(f"Miner UID: {miner_uid.hex()}")
    except Exception as e:
        logger.error(f"Error registering miner: {e}")

def main():
    parser = argparse.ArgumentParser(description="Register a new miner on ModernTensor Aptos network using HD wallet")
    parser.add_argument("--wallet", required=True, help="HD wallet name")
    parser.add_argument("--coldkey", required=True, help="Coldkey name in HD wallet")
    parser.add_argument("--hotkey", required=True, help="Hotkey name in HD wallet")
    parser.add_argument("--api", required=True, help="API endpoint of the miner")
    parser.add_argument("--subnet", type=int, default=DEFAULT_SUBNET_UID, help="Subnet UID to register to")
    parser.add_argument("--stake", type=int, default=DEFAULT_STAKE_AMOUNT, help="Stake amount (in lowest denomination)")
    parser.add_argument("--node", default=DEFAULT_NODE_URL, help="Aptos node URL")
    parser.add_argument("--wallets", default="./wallets", help="HD wallets directory")
    
    args = parser.parse_args()
    
    # Lấy mật khẩu từ người dùng
    password = getpass(f"Enter password for HD wallet '{args.wallet}': ")
    
    # Chạy hàm đăng ký miner
    asyncio.run(register_miner(
        wallet_name=args.wallet,
        coldkey_name=args.coldkey,
        hotkey_name=args.hotkey,
        wallet_password=password,
        api_endpoint=args.api,
        wallets_dir=args.wallets,
        node_url=args.node,
        subnet_uid=args.subnet,
        stake_amount=args.stake,
    ))

if __name__ == "__main__":
    main() 