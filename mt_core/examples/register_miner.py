#!/usr/bin/env python3
"""
Ví dụ về cách đăng ký một miner mới trên ModernTensor sử dụng Core blockchain
Updated to use Core blockchain instead of Aptos
"""

import os
import sys
import asyncio
import logging
import json
import secrets
import argparse
from getpass import getpass
from decimal import Decimal

# Add the parent directory to sys.path for imports
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# Import Core blockchain utilities
from ..account import CoreAccount, Account
from ..core_client.contract_client import ModernTensorCoreClient
from ..config.settings import Settings

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Default values
DEFAULT_SUBNET_UID = 1
DEFAULT_STAKE_AMOUNT = 1000  # 1000 CORE tokens
DEFAULT_BITCOIN_STAKE_AMOUNT = 0.1  # 0.1 BTC


class CoreAccountManager:
    """Helper class for managing Core accounts"""

    def __init__(self, wallets_dir: str = "./wallets"):
        self.wallets_dir = wallets_dir
        os.makedirs(wallets_dir, exist_ok=True)

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


async def register_miner(
    account_name: str,
    account_password: str,
    api_endpoint: str,
    wallets_dir: str = "./wallets",
    subnet_uid: int = DEFAULT_SUBNET_UID,
    stake_amount: int = DEFAULT_STAKE_AMOUNT,
    bitcoin_stake_amount: float = DEFAULT_BITCOIN_STAKE_AMOUNT,
    staking_tier: str = "base",
    enable_bitcoin_staking: bool = False,
):
    """
    Đăng ký một miner mới trên ModernTensor Core blockchain.

    Args:
        account_name: Tên tài khoản.
        account_password: Mật khẩu tài khoản.
        api_endpoint: API endpoint của miner.
        wallets_dir: Thư mục chứa wallets.
        subnet_uid: UID của subnet đăng ký.
        stake_amount: Số lượng CORE tokens stake.
        bitcoin_stake_amount: Số lượng Bitcoin stake (nếu enabled).
        staking_tier: Tier staking (base, boost, super, satoshi).
        enable_bitcoin_staking: Có enable Bitcoin staking không.
    """
    # Khởi tạo AccountManager
    account_manager = CoreAccountManager(wallets_dir)

    # Tải tài khoản
    try:
        account = account_manager.load_account(account_name, account_password)
        logger.info(f"Loaded account: {account_name}")
        logger.info(f"Account address: {account.address}")
    except Exception as e:
        logger.error(f"Error loading account: {e}")
        logger.error("Please make sure the account exists and password is correct")
        logger.error("Create it using:")
        logger.error(f"  python examples/create_account.py")
        return

    # Khởi tạo ModernTensorCoreClient
    settings = Settings()
    client = ModernTensorCoreClient(
        account=account,
        rpc_url=settings.CORE_NODE_URL,
        contract_address=settings.CORE_CONTRACT_ADDRESS,
        chain_id=settings.CORE_CHAIN_ID,
    )

    # Tạo UID ngẫu nhiên cho miner
    miner_uid = secrets.token_bytes(16)  # Tạo 16 bytes ngẫu nhiên cho UID
    logger.info(f"Generated miner UID: {miner_uid.hex()}")

    # Hiển thị thông tin trước khi gửi giao dịch
    print(f"\n=== Registration Information ===")
    print(f"Account: {account_name}")
    print(f"Account Address: {account.address}")
    print(f"Miner UID: {miner_uid.hex()}")
    print(f"Subnet UID: {subnet_uid}")
    print(f"CORE Stake Amount: {stake_amount} CORE")
    print(f"API Endpoint: {api_endpoint}")
    print(f"Staking Tier: {staking_tier}")

    if enable_bitcoin_staking:
        print(f"Bitcoin Staking: ENABLED")
        print(f"Bitcoin Stake Amount: {bitcoin_stake_amount} BTC")
    else:
        print(f"Bitcoin Staking: DISABLED")

    # Hiển thị reward multiplier theo tier
    tier_multipliers = {
        "base": "1.0x",
        "boost": "1.25x",
        "super": "1.5x",
        "satoshi": "2.0x",
    }
    print(f"Reward Multiplier: {tier_multipliers.get(staking_tier, '1.0x')}")

    # Xác nhận từ người dùng
    confirm = input("\nConfirm registration? (y/n): ")
    if confirm.lower() != "y":
        logger.info("Registration cancelled.")
        return

    # Gửi giao dịch đăng ký
    try:
        logger.info("Registering miner...")

        # Prepare miner data
        miner_data = {
            "uid": miner_uid,
            "subnet_uid": subnet_uid,
            "stake_amount": stake_amount,
            "api_endpoint": api_endpoint,
            "staking_tier": staking_tier,
            "bitcoin_stake_amount": (
                bitcoin_stake_amount if enable_bitcoin_staking else 0
            ),
            "enable_bitcoin_staking": enable_bitcoin_staking,
        }

        # Register miner on Core blockchain
        if enable_bitcoin_staking:
            # Register with Bitcoin staking
            txn_hash = await client.register_miner_with_bitcoin_staking(
                uid=miner_uid,
                subnet_uid=subnet_uid,
                core_stake_amount=stake_amount,
                bitcoin_stake_amount=bitcoin_stake_amount,
                api_endpoint=api_endpoint,
                staking_tier=staking_tier,
            )
        else:
            # Register with CORE tokens only
            txn_hash = await client.register_miner(
                uid=miner_uid,
                subnet_uid=subnet_uid,
                stake_amount=stake_amount,
                api_endpoint=api_endpoint,
                staking_tier=staking_tier,
            )

        logger.info(f"Registration successful! Transaction hash: {txn_hash}")
        print(f"\n✅ Miner registered successfully!")
        print(f"Transaction hash: {txn_hash}")
        print(f"Miner UID: {miner_uid.hex()}")

        # Save miner info to file
        miner_info_file = os.path.join(wallets_dir, f"{account_name}_miner_info.json")
        with open(miner_info_file, "w") as f:
            json.dump(
                {
                    "account_name": account_name,
                    "account_address": account.address,
                    "miner_uid": miner_uid.hex(),
                    "subnet_uid": subnet_uid,
                    "stake_amount": stake_amount,
                    "api_endpoint": api_endpoint,
                    "staking_tier": staking_tier,
                    "bitcoin_staking_enabled": enable_bitcoin_staking,
                    "bitcoin_stake_amount": (
                        bitcoin_stake_amount if enable_bitcoin_staking else 0
                    ),
                    "transaction_hash": txn_hash,
                    "registration_timestamp": asyncio.get_event_loop().time(),
                },
                f,
                indent=2,
            )

        print(f"Miner info saved to: {miner_info_file}")

    except Exception as e:
        logger.error(f"Error registering miner: {e}")
        print(f"❌ Registration failed: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Register a new miner on ModernTensor Core blockchain"
    )
    parser.add_argument("--account", required=True, help="Account name")
    parser.add_argument("--api", required=True, help="API endpoint of the miner")
    parser.add_argument(
        "--subnet",
        type=int,
        default=DEFAULT_SUBNET_UID,
        help="Subnet UID to register to",
    )
    parser.add_argument(
        "--stake",
        type=int,
        default=DEFAULT_STAKE_AMOUNT,
        help="CORE tokens stake amount",
    )
    parser.add_argument("--wallets", default="./wallets", help="Wallets directory")
    parser.add_argument(
        "--tier",
        choices=["base", "boost", "super", "satoshi"],
        default="base",
        help="Staking tier (base=1x, boost=1.25x, super=1.5x, satoshi=2x)",
    )
    parser.add_argument(
        "--bitcoin-staking", action="store_true", help="Enable Bitcoin staking"
    )
    parser.add_argument(
        "--bitcoin-stake",
        type=float,
        default=DEFAULT_BITCOIN_STAKE_AMOUNT,
        help="Bitcoin stake amount (if enabled)",
    )

    args = parser.parse_args()

    # Lấy mật khẩu từ người dùng
    password = getpass(f"Enter password for account '{args.account}': ")

    # Hiển thị thông tin network
    settings = Settings()
    print(f"\n=== Core Blockchain Network Information ===")
    print(f"Network: {settings.CORE_NETWORK}")
    print(f"RPC URL: {settings.CORE_NODE_URL}")
    print(f"Chain ID: {settings.CORE_CHAIN_ID}")
    print(f"Contract Address: {settings.CORE_CONTRACT_ADDRESS}")
    print(f"CORE Token Address: {settings.CORE_TOKEN_ADDRESS}")

    # Chạy hàm đăng ký miner
    asyncio.run(
        register_miner(
            account_name=args.account,
            account_password=password,
            api_endpoint=args.api,
            wallets_dir=args.wallets,
            subnet_uid=args.subnet,
            stake_amount=args.stake,
            bitcoin_stake_amount=args.bitcoin_stake,
            staking_tier=args.tier,
            enable_bitcoin_staking=args.bitcoin_staking,
        )
    )


if __name__ == "__main__":
    main()
