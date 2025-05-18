#!/usr/bin/env python3
"""
Script để đăng ký miner sử dụng tài khoản đã nhập
"""

import os
import sys
import asyncio
import logging
from keymanager import AccountKeyManager
from aptos_sdk.client import RestClient

# Thử import ModernTensorClient
try:
    from aptos_core import ModernTensorClient
except ImportError:
    print("Không thể import ModernTensorClient. Có thể cần thêm đường dẫn.")
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "aptos_migration"))
    try:
        from aptos_core import ModernTensorClient
    except ImportError:
        print("Vẫn không thể import ModernTensorClient. Kiểm tra lại cấu trúc dự án.")
        sys.exit(1)

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Cấu hình
ACCOUNT_NAME = "myaptos"
PASSWORD = "password123"  # Nên để trống và hỏi người dùng trong thực tế
NODE_URL = "https://fullnode.testnet.aptoslabs.com/v1"  # Thêm /v1 để fix lỗi kết nối
SUBNET_UID = 1
STAKE_AMOUNT = 10_000_000  # 0.1 APT, assuming 8 decimals
CONTRACT_ADDRESS = "0x49efdb1b13ba49c9624ab17ac21cfa9d2b891871727e39a309457b63f42518b2"  # Địa chỉ contract ModernTensor
API_ENDPOINT = "http://example.com/api/miner"  # Endpoint API của miner

async def register_miner():
    # Khởi tạo AccountKeyManager
    key_manager = AccountKeyManager(base_dir="./examples/wallets")
    
    # Tải tài khoản
    logger.info(f"Đang tải tài khoản {ACCOUNT_NAME}...")
    try:
        account = key_manager.load_account(ACCOUNT_NAME, PASSWORD)
        logger.info(f"Đã tải tài khoản với địa chỉ: {account.address().hex()}")
    except Exception as e:
        logger.error(f"Lỗi khi tải tài khoản: {e}")
        return
    
    # Khởi tạo Aptos REST client
    logger.info(f"Kết nối tới node Aptos tại {NODE_URL}...")
    rest_client = RestClient(NODE_URL)
    
    # Khởi tạo ModernTensorClient
    logger.info(f"Khởi tạo ModernTensorClient với địa chỉ contract {CONTRACT_ADDRESS}...")
    client = ModernTensorClient(
        account=account,
        client=rest_client,
        moderntensor_address=CONTRACT_ADDRESS,
    )
    
    # Tạo UID ngẫu nhiên cho miner
    miner_uid = os.urandom(16)  # Tạo 16 bytes ngẫu nhiên cho UID
    logger.info(f"Tạo UID miner: {miner_uid.hex()}")
    
    # Hiển thị thông tin trước khi gửi giao dịch
    print(f"\n=== Thông tin đăng ký ===")
    print(f"Địa chỉ tài khoản: {account.address().hex()}")
    print(f"UID miner: {miner_uid.hex()}")
    print(f"Subnet UID: {SUBNET_UID}")
    print(f"Số lượng stake: {STAKE_AMOUNT / 100_000_000} APT")
    print(f"API Endpoint: {API_ENDPOINT}")
    
    # Xác nhận từ người dùng
    confirm = input("\nXác nhận đăng ký? (y/n): ")
    if confirm.lower() != 'y':
        logger.info("Đăng ký đã bị hủy.")
        return
    
    # Gửi giao dịch đăng ký
    try:
        logger.info("Đang đăng ký miner...")
        txn_hash = await client.register_miner(
            uid=miner_uid,
            subnet_uid=SUBNET_UID,
            stake_amount=STAKE_AMOUNT,
            api_endpoint=API_ENDPOINT,
        )
        logger.info(f"Đăng ký thành công! Hash giao dịch: {txn_hash}")
    except Exception as e:
        logger.error(f"Lỗi khi đăng ký miner: {e}")

if __name__ == "__main__":
    asyncio.run(register_miner()) 