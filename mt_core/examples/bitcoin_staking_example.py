#!/usr/bin/env python3
"""
Ví dụ về cách sử dụng Bitcoin staking trên ModernTensor Core blockchain
Example of Bitcoin staking integration with dual staking rewards
"""

import os
import sys
import asyncio
import logging
import json
from decimal import Decimal
from getpass import getpass
from datetime import datetime, timedelta

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


class BitcoinStakingExample:
    """Bitcoin staking example with dual staking rewards"""

    def __init__(self, wallets_dir: str = "./wallets"):
        self.wallets_dir = wallets_dir
        self.settings = Settings()
        os.makedirs(wallets_dir, exist_ok=True)

    def load_account(self, account_name: str, password: str) -> CoreAccount:
        """Load account from encrypted file"""
        try:
            account_file = os.path.join(self.wallets_dir, f"{account_name}.json")

            if not os.path.exists(account_file):
                raise FileNotFoundError(f"Account file not found: {account_file}")

            with open(account_file, "r") as f:
                encrypted_account = json.load(f)

            private_key = Account.decrypt(encrypted_account, password)
            return CoreAccount(private_key.hex())

        except Exception as e:
            logger.error(f"Error loading account: {e}")
            raise

    async def stake_bitcoin(
        self, account: CoreAccount, btc_amount: float, lock_time_days: int = 30
    ):
        """Stake Bitcoin with CLTV timelock"""
        try:
            client = ModernTensorCoreClient(
                account=account,
                rpc_url=self.settings.CORE_NODE_URL,
                contract_address=self.settings.CORE_CONTRACT_ADDRESS,
                chain_id=self.settings.CORE_CHAIN_ID,
            )

            # Calculate lock time
            lock_time = datetime.now() + timedelta(days=lock_time_days)

            logger.info(f"Staking {btc_amount} BTC for {lock_time_days} days")

            # Create Bitcoin staking transaction
            txn_hash = await client.stake_bitcoin(
                amount=btc_amount, lock_time=lock_time, staker_address=account.address
            )

            logger.info(f"Bitcoin staking successful! Transaction hash: {txn_hash}")
            return txn_hash

        except Exception as e:
            logger.error(f"Error staking Bitcoin: {e}")
            raise

    async def stake_core_tokens(
        self, account: CoreAccount, core_amount: int, staking_tier: str = "base"
    ):
        """Stake CORE tokens with tier multiplier"""
        try:
            client = ModernTensorCoreClient(
                account=account,
                rpc_url=self.settings.CORE_NODE_URL,
                contract_address=self.settings.CORE_CONTRACT_ADDRESS,
                chain_id=self.settings.CORE_CHAIN_ID,
            )

            logger.info(f"Staking {core_amount} CORE tokens at {staking_tier} tier")

            # Stake CORE tokens
            txn_hash = await client.stake_core_tokens(
                amount=core_amount,
                staking_tier=staking_tier,
                staker_address=account.address,
            )

            logger.info(f"CORE staking successful! Transaction hash: {txn_hash}")
            return txn_hash

        except Exception as e:
            logger.error(f"Error staking CORE tokens: {e}")
            raise

    async def enable_dual_staking(
        self,
        account: CoreAccount,
        core_amount: int,
        btc_amount: float,
        staking_tier: str = "satoshi",
        lock_time_days: int = 30,
    ):
        """Enable dual staking for maximum rewards"""
        try:
            client = ModernTensorCoreClient(
                account=account,
                rpc_url=self.settings.CORE_NODE_URL,
                contract_address=self.settings.CORE_CONTRACT_ADDRESS,
                chain_id=self.settings.CORE_CHAIN_ID,
            )

            # Calculate lock time
            lock_time = datetime.now() + timedelta(days=lock_time_days)

            logger.info(f"Enabling dual staking: {core_amount} CORE + {btc_amount} BTC")
            logger.info(
                f"Staking tier: {staking_tier}, Lock time: {lock_time_days} days"
            )

            # Enable dual staking
            txn_hash = await client.enable_dual_staking(
                core_amount=core_amount,
                btc_amount=btc_amount,
                staking_tier=staking_tier,
                lock_time=lock_time,
                staker_address=account.address,
            )

            logger.info(f"Dual staking enabled! Transaction hash: {txn_hash}")
            return txn_hash

        except Exception as e:
            logger.error(f"Error enabling dual staking: {e}")
            raise

    async def get_staking_info(self, account: CoreAccount):
        """Get staking information for account"""
        try:
            client = ModernTensorCoreClient(
                account=account,
                rpc_url=self.settings.CORE_NODE_URL,
                contract_address=self.settings.CORE_CONTRACT_ADDRESS,
                chain_id=self.settings.CORE_CHAIN_ID,
            )

            # Get staking info
            staking_info = await client.get_staking_info(account.address)

            return staking_info

        except Exception as e:
            logger.error(f"Error getting staking info: {e}")
            raise

    async def calculate_rewards(self, account: CoreAccount):
        """Calculate pending rewards"""
        try:
            client = ModernTensorCoreClient(
                account=account,
                rpc_url=self.settings.CORE_NODE_URL,
                contract_address=self.settings.CORE_CONTRACT_ADDRESS,
                chain_id=self.settings.CORE_CHAIN_ID,
            )

            # Calculate rewards
            rewards = await client.calculate_rewards(account.address)

            return rewards

        except Exception as e:
            logger.error(f"Error calculating rewards: {e}")
            raise

    async def claim_rewards(self, account: CoreAccount):
        """Claim pending rewards"""
        try:
            client = ModernTensorCoreClient(
                account=account,
                rpc_url=self.settings.CORE_NODE_URL,
                contract_address=self.settings.CORE_CONTRACT_ADDRESS,
                chain_id=self.settings.CORE_CHAIN_ID,
            )

            # Claim rewards
            txn_hash = await client.claim_rewards(account.address)

            logger.info(f"Rewards claimed! Transaction hash: {txn_hash}")
            return txn_hash

        except Exception as e:
            logger.error(f"Error claiming rewards: {e}")
            raise

    def display_staking_tiers(self):
        """Display available staking tiers and multipliers"""
        print("\n=== Bitcoin Staking Tiers ===")
        print("1. Base (1.0x multiplier)")
        print("   - CORE tokens only")
        print("   - No Bitcoin staking required")
        print("   - Standard rewards")

        print("\n2. Boost (1.25x multiplier)")
        print("   - CORE tokens + 0.01 BTC minimum")
        print("   - 25% reward boost")
        print("   - 30-day minimum lock")

        print("\n3. Super (1.5x multiplier)")
        print("   - CORE tokens + 0.1 BTC minimum")
        print("   - 50% reward boost")
        print("   - 60-day minimum lock")

        print("\n4. Satoshi (2.0x multiplier)")
        print("   - CORE tokens + 1.0 BTC minimum")
        print("   - 100% reward boost")
        print("   - 90-day minimum lock")
        print("   - Maximum dual staking rewards")

    def display_dual_staking_economics(self):
        """Display dual staking economics"""
        print("\n=== Dual Staking Economics ===")
        print("Revenue Streams:")
        print("1. AI Training Rewards (CORE tokens)")
        print("2. Bitcoin Staking Rewards (BTC)")
        print("3. Network Fees (CORE tokens)")
        print("4. Validator Rewards (CORE tokens)")

        print("\nDual Staking Benefits:")
        print("• Self-custodial Bitcoin staking")
        print("• No slashing risk")
        print("• Timelock-based security")
        print("• Multiplicative rewards")
        print("• Bitcoin network security")

        print("\nTechnical Features:")
        print("• CLTV timelock contracts")
        print("• Bitcoin transaction verification")
        print("• Core blockchain integration")
        print("• EVM compatibility")
        print("• ~5000 TPS performance")


async def main():
    example = BitcoinStakingExample()

    print("\n=== ModernTensor Bitcoin Staking Example ===")
    print("Core blockchain with Bitcoin staking integration")

    # Display staking information
    example.display_staking_tiers()
    example.display_dual_staking_economics()

    print("\n=== Available Actions ===")
    print("1. Stake Bitcoin only")
    print("2. Stake CORE tokens only")
    print("3. Enable dual staking")
    print("4. Check staking info")
    print("5. Calculate rewards")
    print("6. Claim rewards")
    print("7. Show network info")
    print("0. Exit")

    choice = input("\nEnter your choice (0-7): ")

    if choice == "0":
        print("Exiting...")
        return

    if choice == "7":
        # Show network info
        settings = Settings()
        print(f"\n=== Network Information ===")
        print(f"Network: {settings.CORE_NETWORK}")
        print(f"RPC URL: {settings.CORE_NODE_URL}")
        print(f"Chain ID: {settings.CORE_CHAIN_ID}")
        print(f"Contract Address: {settings.CORE_CONTRACT_ADDRESS}")
        print(f"CORE Token Address: {settings.CORE_TOKEN_ADDRESS}")
        print(
            f"Bitcoin Staking: {'ENABLED' if settings.BITCOIN_STAKING_ENABLED else 'DISABLED'}"
        )
        print(
            f"Dual Staking: {'ENABLED' if settings.DUAL_STAKING_ENABLED else 'DISABLED'}"
        )
        return

    # Get account info
    account_name = input("Enter account name: ")
    password = getpass("Enter account password: ")

    try:
        account = example.load_account(account_name, password)
        logger.info(f"Loaded account: {account.address}")
    except Exception as e:
        logger.error(f"Error loading account: {e}")
        return

    if choice == "1":
        # Stake Bitcoin only
        btc_amount = float(input("Enter Bitcoin amount to stake: "))
        lock_days = int(input("Enter lock time in days (default 30): ") or "30")

        try:
            txn_hash = await example.stake_bitcoin(account, btc_amount, lock_days)
            print(f"✅ Bitcoin staking successful! Transaction: {txn_hash}")
        except Exception as e:
            print(f"❌ Bitcoin staking failed: {e}")

    elif choice == "2":
        # Stake CORE tokens only
        core_amount = int(input("Enter CORE token amount to stake: "))
        tier = input("Enter staking tier (base/boost/super/satoshi): ") or "base"

        try:
            txn_hash = await example.stake_core_tokens(account, core_amount, tier)
            print(f"✅ CORE staking successful! Transaction: {txn_hash}")
        except Exception as e:
            print(f"❌ CORE staking failed: {e}")

    elif choice == "3":
        # Enable dual staking
        core_amount = int(input("Enter CORE token amount: "))
        btc_amount = float(input("Enter Bitcoin amount: "))
        tier = input("Enter staking tier (boost/super/satoshi): ") or "satoshi"
        lock_days = int(input("Enter lock time in days (default 30): ") or "30")

        try:
            txn_hash = await example.enable_dual_staking(
                account, core_amount, btc_amount, tier, lock_days
            )
            print(f"✅ Dual staking enabled! Transaction: {txn_hash}")
        except Exception as e:
            print(f"❌ Dual staking failed: {e}")

    elif choice == "4":
        # Check staking info
        try:
            staking_info = await example.get_staking_info(account)
            print(f"\n=== Staking Information ===")
            print(f"Account: {account.address}")
            print(f"CORE Staked: {staking_info.get('core_staked', 0)} CORE")
            print(f"Bitcoin Staked: {staking_info.get('bitcoin_staked', 0)} BTC")
            print(f"Staking Tier: {staking_info.get('staking_tier', 'none')}")
            print(f"Lock Time: {staking_info.get('lock_time', 'none')}")
            print(
                f"Dual Staking: {'ENABLED' if staking_info.get('dual_staking', False) else 'DISABLED'}"
            )
        except Exception as e:
            print(f"❌ Error getting staking info: {e}")

    elif choice == "5":
        # Calculate rewards
        try:
            rewards = await example.calculate_rewards(account)
            print(f"\n=== Pending Rewards ===")
            print(f"Account: {account.address}")
            print(f"CORE Rewards: {rewards.get('core_rewards', 0)} CORE")
            print(f"Bitcoin Rewards: {rewards.get('bitcoin_rewards', 0)} BTC")
            print(f"Total Value (USD): ${rewards.get('total_value_usd', 0):.2f}")
        except Exception as e:
            print(f"❌ Error calculating rewards: {e}")

    elif choice == "6":
        # Claim rewards
        try:
            txn_hash = await example.claim_rewards(account)
            print(f"✅ Rewards claimed! Transaction: {txn_hash}")
        except Exception as e:
            print(f"❌ Error claiming rewards: {e}")

    else:
        print("Invalid choice. Please try again.")


if __name__ == "__main__":
    asyncio.run(main())
