#!/usr/bin/env python3
"""
ModernTensor Core Blockchain - Quickstart Example
Hướng dẫn nhanh để bắt đầu với ModernTensor trên Core blockchain
"""

import os
import sys
import asyncio
import logging
from getpass import getpass

# Add the parent directory to sys.path for imports
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# Import Core blockchain utilities
from ..account import CoreAccount
from ..core_client.contract_client import ModernTensorCoreClient
from ..config.settings import Settings

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class QuickstartExample:
    """Quickstart example for ModernTensor Core blockchain"""

    def __init__(self):
        self.settings = Settings()
        self.account = None
        self.client = None

    def create_account(self):
        """Step 1: Create a new Core account"""
        print("=== Step 1: Creating Core Account ===")

        # Generate new account
        self.account = CoreAccount()

        print(f"✅ Account created successfully!")
        print(f"Address: {self.account.address}")
        print(f"Private Key: {self.account.private_key}")
        print("⚠️  IMPORTANT: Store your private key securely!")

        return self.account

    def setup_client(self):
        """Step 2: Setup ModernTensor client"""
        print("\n=== Step 2: Setting up ModernTensor Client ===")

        if not self.account:
            raise ValueError("Account must be created first")

        # Initialize client
        self.client = ModernTensorCoreClient(
            account=self.account,
            rpc_url=self.settings.CORE_NODE_URL,
            contract_address=self.settings.CORE_CONTRACT_ADDRESS,
            chain_id=self.settings.CORE_CHAIN_ID,
        )

        print(f"✅ Client setup successful!")
        print(f"Connected to: {self.settings.CORE_NETWORK}")
        print(f"RPC URL: {self.settings.CORE_NODE_URL}")
        print(f"Chain ID: {self.settings.CORE_CHAIN_ID}")

        return self.client

    async def check_balance(self):
        """Step 3: Check account balance"""
        print("\n=== Step 3: Checking Account Balance ===")

        if not self.client:
            raise ValueError("Client must be setup first")

        try:
            # Get CORE token balance
            balance = await self.client.get_core_balance(self.account.address)
            print(f"CORE Balance: {balance} CORE")

            # Get ETH balance (for gas fees)
            eth_balance = await self.client.get_eth_balance(self.account.address)
            print(f"ETH Balance: {eth_balance} ETH")

            if balance == 0:
                print("⚠️  Warning: You need CORE tokens to stake and participate")
                print("💡 Get testnet tokens from Core faucet:")
                print("   https://scan.test.btcs.network/faucet")

            if eth_balance == 0:
                print("⚠️  Warning: You need ETH for gas fees")
                print("💡 Get testnet ETH from Core faucet")

        except Exception as e:
            logger.error(f"Error checking balance: {e}")

    async def register_as_miner(self, api_endpoint: str = "http://localhost:8080"):
        """Step 4: Register as a miner"""
        print("\n=== Step 4: Registering as Miner ===")

        if not self.client:
            raise ValueError("Client must be setup first")

        try:
            # Default values
            subnet_uid = 1
            stake_amount = 1000  # 1000 CORE tokens

            print(f"Registering miner with:")
            print(f"  Subnet UID: {subnet_uid}")
            print(f"  Stake Amount: {stake_amount} CORE")
            print(f"  API Endpoint: {api_endpoint}")

            # Register miner
            txn_hash = await self.client.register_miner(
                uid=os.urandom(16),  # Random 16-byte UID
                subnet_uid=subnet_uid,
                stake_amount=stake_amount,
                api_endpoint=api_endpoint,
                staking_tier="base",
            )

            print(f"✅ Miner registration successful!")
            print(f"Transaction hash: {txn_hash}")

        except Exception as e:
            logger.error(f"Error registering miner: {e}")
            print(f"❌ Registration failed: {e}")

    async def register_as_validator(self):
        """Step 5: Register as a validator"""
        print("\n=== Step 5: Registering as Validator ===")

        if not self.client:
            raise ValueError("Client must be setup first")

        try:
            # Default values
            subnet_uid = 1
            stake_amount = 10000  # 10,000 CORE tokens (higher stake for validator)

            print(f"Registering validator with:")
            print(f"  Subnet UID: {subnet_uid}")
            print(f"  Stake Amount: {stake_amount} CORE")

            # Register validator
            txn_hash = await self.client.register_validator(
                uid=os.urandom(16),  # Random 16-byte UID
                subnet_uid=subnet_uid,
                stake_amount=stake_amount,
                staking_tier="base",
            )

            print(f"✅ Validator registration successful!")
            print(f"Transaction hash: {txn_hash}")

        except Exception as e:
            logger.error(f"Error registering validator: {e}")
            print(f"❌ Registration failed: {e}")

    async def enable_bitcoin_staking(self):
        """Step 6: Enable Bitcoin staking (optional)"""
        print("\n=== Step 6: Enabling Bitcoin Staking ===")

        if not self.client:
            raise ValueError("Client must be setup first")

        try:
            # Bitcoin staking parameters
            btc_amount = 0.1  # 0.1 BTC
            lock_time_days = 30
            staking_tier = "boost"  # Boost tier with Bitcoin

            print(f"Enabling Bitcoin staking with:")
            print(f"  BTC Amount: {btc_amount} BTC")
            print(f"  Lock Time: {lock_time_days} days")
            print(f"  Staking Tier: {staking_tier} (1.25x multiplier)")

            # Enable dual staking
            txn_hash = await self.client.enable_dual_staking(
                core_amount=1000,  # 1000 CORE tokens
                btc_amount=btc_amount,
                staking_tier=staking_tier,
                lock_time=None,  # Will be calculated
                staker_address=self.account.address,
            )

            print(f"✅ Bitcoin staking enabled!")
            print(f"Transaction hash: {txn_hash}")
            print(f"🎉 You now earn 1.25x rewards with dual staking!")

        except Exception as e:
            logger.error(f"Error enabling Bitcoin staking: {e}")
            print(f"❌ Bitcoin staking failed: {e}")

    async def check_staking_status(self):
        """Step 7: Check staking status"""
        print("\n=== Step 7: Checking Staking Status ===")

        if not self.client:
            raise ValueError("Client must be setup first")

        try:
            # Get staking info
            staking_info = await self.client.get_staking_info(self.account.address)

            print(f"Staking Status:")
            print(f"  Account: {self.account.address}")
            print(f"  CORE Staked: {staking_info.get('core_staked', 0)} CORE")
            print(f"  Bitcoin Staked: {staking_info.get('bitcoin_staked', 0)} BTC")
            print(f"  Staking Tier: {staking_info.get('staking_tier', 'none')}")
            print(
                f"  Dual Staking: {'ENABLED' if staking_info.get('dual_staking', False) else 'DISABLED'}"
            )

            # Calculate rewards
            rewards = await self.client.calculate_rewards(self.account.address)

            print(f"\nPending Rewards:")
            print(f"  CORE Rewards: {rewards.get('core_rewards', 0)} CORE")
            print(f"  Bitcoin Rewards: {rewards.get('bitcoin_rewards', 0)} BTC")

        except Exception as e:
            logger.error(f"Error checking staking status: {e}")

    def display_next_steps(self):
        """Display next steps for users"""
        print("\n=== Next Steps ===")
        print("🎯 You have successfully setup ModernTensor on Core blockchain!")
        print()
        print("What you can do next:")
        print("1. 🚀 Start mining/validating:")
        print("   - Run your miner/validator node")
        print("   - Connect to the network")
        print("   - Start earning rewards")
        print()
        print("2. 📈 Optimize your staking:")
        print("   - Upgrade to higher staking tiers")
        print("   - Enable Bitcoin staking for higher rewards")
        print("   - Monitor your performance")
        print()
        print("3. 🔧 Explore advanced features:")
        print("   - Set up multiple subnets")
        print("   - Configure custom models")
        print("   - Use the CLI tools")
        print()
        print("4. 📚 Learn more:")
        print("   - Read the documentation")
        print("   - Join the community")
        print("   - Check the examples")
        print()
        print("Resources:")
        print("- Documentation: README_CORE.md")
        print("- Examples: examples/")
        print("- Core Network: https://coredao.org")
        print("- Testnet Faucet: https://scan.test.btcs.network/faucet")


async def main():
    """Main quickstart workflow"""
    print("🚀 ModernTensor Core Blockchain - Quickstart Guide")
    print("=" * 60)

    example = QuickstartExample()

    # Interactive mode
    print("\nChoose your path:")
    print("1. Full quickstart (recommended)")
    print("2. Miner setup only")
    print("3. Validator setup only")
    print("4. Bitcoin staking demo")
    print("5. Manual step-by-step")

    choice = input("\nEnter your choice (1-5): ").strip()

    if choice == "1":
        # Full quickstart
        print("\n🎯 Starting full quickstart...")

        # Create account
        account = example.create_account()

        # Setup client
        client = example.setup_client()

        # Check balance
        await example.check_balance()

        # Register as miner
        api_endpoint = input(
            "\nEnter your miner API endpoint (default: http://localhost:8080): "
        ).strip()
        if not api_endpoint:
            api_endpoint = "http://localhost:8080"

        await example.register_as_miner(api_endpoint)

        # Ask about Bitcoin staking
        enable_btc = (
            input("\nEnable Bitcoin staking for higher rewards? (y/n): ")
            .strip()
            .lower()
        )
        if enable_btc == "y":
            await example.enable_bitcoin_staking()

        # Check final status
        await example.check_staking_status()

        # Display next steps
        example.display_next_steps()

    elif choice == "2":
        # Miner setup only
        print("\n⛏️  Setting up miner...")

        example.create_account()
        example.setup_client()
        await example.check_balance()

        api_endpoint = input("\nEnter your miner API endpoint: ").strip()
        if not api_endpoint:
            api_endpoint = "http://localhost:8080"

        await example.register_as_miner(api_endpoint)
        await example.check_staking_status()

    elif choice == "3":
        # Validator setup only
        print("\n🛡️  Setting up validator...")

        example.create_account()
        example.setup_client()
        await example.check_balance()
        await example.register_as_validator()
        await example.check_staking_status()

    elif choice == "4":
        # Bitcoin staking demo
        print("\n₿ Bitcoin staking demo...")

        example.create_account()
        example.setup_client()
        await example.check_balance()
        await example.enable_bitcoin_staking()
        await example.check_staking_status()

    elif choice == "5":
        # Manual step-by-step
        print("\n📋 Manual step-by-step mode...")
        print("Follow the prompts to complete each step.")

        input("\nPress Enter to create account...")
        example.create_account()

        input("\nPress Enter to setup client...")
        example.setup_client()

        input("\nPress Enter to check balance...")
        await example.check_balance()

        action = (
            input("\nWhat would you like to do? (miner/validator/bitcoin): ")
            .strip()
            .lower()
        )

        if action == "miner":
            api_endpoint = input("Enter miner API endpoint: ").strip()
            await example.register_as_miner(api_endpoint)
        elif action == "validator":
            await example.register_as_validator()
        elif action == "bitcoin":
            await example.enable_bitcoin_staking()

        await example.check_staking_status()

    else:
        print("Invalid choice. Please try again.")
        return

    print("\n🎉 Quickstart completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
