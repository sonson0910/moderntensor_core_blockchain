#!/usr/bin/env python3
"""
ModernTensor Core Blockchain - Advanced Usage Example
Advanced features and configurations for experienced users
"""

import os
import sys
import asyncio
import logging
import json
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from getpass import getpass

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
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AdvancedUsageExample:
    """Advanced usage examples for ModernTensor Core blockchain"""

    def __init__(self, wallets_dir: str = "./wallets"):
        self.wallets_dir = wallets_dir
        self.settings = Settings()
        self.accounts: Dict[str, CoreAccount] = {}
        self.clients: Dict[str, ModernTensorCoreClient] = {}
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
            account = CoreAccount(private_key.hex())

            # Cache account
            self.accounts[account_name] = account
            return account

        except Exception as e:
            logger.error(f"Error loading account: {e}")
            raise

    def get_client(self, account_name: str) -> ModernTensorCoreClient:
        """Get or create client for account"""
        if account_name not in self.clients:
            if account_name not in self.accounts:
                raise ValueError(f"Account {account_name} not loaded")

            client = ModernTensorCoreClient(
                account=self.accounts[account_name],
                rpc_url=self.settings.CORE_NODE_URL,
                contract_address=self.settings.CORE_CONTRACT_ADDRESS,
                chain_id=self.settings.CORE_CHAIN_ID,
            )
            self.clients[account_name] = client

        return self.clients[account_name]

    async def multi_account_setup(self, account_names: List[str], passwords: List[str]):
        """Setup multiple accounts for batch operations"""
        print("=== Multi-Account Setup ===")

        if len(account_names) != len(passwords):
            raise ValueError("Account names and passwords must have same length")

        for account_name, password in zip(account_names, passwords):
            try:
                account = self.load_account(account_name, password)
                client = self.get_client(account_name)

                print(f"✅ Loaded account: {account_name} ({account.address})")

                # Check balance
                balance = await client.get_core_balance(account.address)
                print(f"   CORE Balance: {balance} CORE")

            except Exception as e:
                print(f"❌ Failed to load account {account_name}: {e}")

    async def create_subnet(self, account_name: str, subnet_config: Dict):
        """Create a new subnet"""
        print(f"=== Creating Subnet with {account_name} ===")

        client = self.get_client(account_name)

        try:
            # Create subnet
            txn_hash = await client.create_subnet(
                subnet_name=subnet_config["name"],
                subnet_description=subnet_config["description"],
                min_stake=subnet_config["min_stake"],
                max_validators=subnet_config["max_validators"],
                max_miners=subnet_config["max_miners"],
                incentive_model=subnet_config["incentive_model"],
                creator_address=self.accounts[account_name].address,
            )

            print(f"✅ Subnet created successfully!")
            print(f"Transaction hash: {txn_hash}")
            print(f"Subnet name: {subnet_config['name']}")

            return txn_hash

        except Exception as e:
            logger.error(f"Error creating subnet: {e}")
            raise

    async def batch_register_miners(self, miners_config: List[Dict]):
        """Register multiple miners in batch"""
        print("=== Batch Miner Registration ===")

        registration_results = []

        for config in miners_config:
            try:
                account_name = config["account_name"]
                client = self.get_client(account_name)

                print(f"Registering miner: {account_name}")

                # Register miner
                txn_hash = await client.register_miner(
                    uid=os.urandom(16),
                    subnet_uid=config["subnet_uid"],
                    stake_amount=config["stake_amount"],
                    api_endpoint=config["api_endpoint"],
                    staking_tier=config.get("staking_tier", "base"),
                )

                result = {
                    "account_name": account_name,
                    "transaction_hash": txn_hash,
                    "subnet_uid": config["subnet_uid"],
                    "status": "success",
                }

                registration_results.append(result)
                print(f"✅ Registered: {account_name} - {txn_hash}")

            except Exception as e:
                result = {
                    "account_name": config["account_name"],
                    "error": str(e),
                    "status": "failed",
                }
                registration_results.append(result)
                print(f"❌ Failed: {config['account_name']} - {e}")

        return registration_results

    async def setup_dual_staking_network(self, network_config: Dict):
        """Setup a complete dual staking network"""
        print("=== Setting up Dual Staking Network ===")

        # Create validators with different tiers
        validators = network_config["validators"]
        miners = network_config["miners"]

        print(f"Setting up {len(validators)} validators and {len(miners)} miners")

        # Setup validators
        for validator_config in validators:
            account_name = validator_config["account_name"]
            client = self.get_client(account_name)

            try:
                # Register validator
                txn_hash = await client.register_validator(
                    uid=os.urandom(16),
                    subnet_uid=validator_config["subnet_uid"],
                    stake_amount=validator_config["stake_amount"],
                    staking_tier=validator_config.get("staking_tier", "base"),
                )

                print(f"✅ Validator registered: {account_name} - {txn_hash}")

                # Enable dual staking if configured
                if validator_config.get("enable_dual_staking", False):
                    dual_txn = await client.enable_dual_staking(
                        core_amount=validator_config["stake_amount"],
                        btc_amount=validator_config.get("btc_amount", 0.1),
                        staking_tier=validator_config.get("staking_tier", "boost"),
                        lock_time=datetime.now() + timedelta(days=30),
                        staker_address=self.accounts[account_name].address,
                    )
                    print(f"✅ Dual staking enabled: {account_name} - {dual_txn}")

            except Exception as e:
                print(f"❌ Validator setup failed: {account_name} - {e}")

        # Setup miners
        await self.batch_register_miners(miners)

        print("✅ Dual staking network setup completed!")

    async def monitor_network_performance(
        self, subnet_uid: int, duration_minutes: int = 60
    ):
        """Monitor network performance and metrics"""
        print(f"=== Monitoring Network Performance (Subnet {subnet_uid}) ===")

        # Use first available client for monitoring
        client = list(self.clients.values())[0]

        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)

        metrics = {
            "subnet_uid": subnet_uid,
            "start_time": start_time.isoformat(),
            "validators": [],
            "miners": [],
            "performance_data": [],
        }

        print(f"Monitoring for {duration_minutes} minutes...")

        while datetime.now() < end_time:
            try:
                # Get subnet info
                subnet_info = await client.get_subnet_info(subnet_uid)

                # Get metagraph data
                metagraph = await client.get_metagraph(subnet_uid)

                # Collect performance metrics
                timestamp = datetime.now().isoformat()
                performance_point = {
                    "timestamp": timestamp,
                    "active_validators": len(metagraph.get("validators", [])),
                    "active_miners": len(metagraph.get("miners", [])),
                    "total_stake": subnet_info.get("total_stake", 0),
                    "network_difficulty": subnet_info.get("difficulty", 0),
                    "avg_response_time": subnet_info.get("avg_response_time", 0),
                }

                metrics["performance_data"].append(performance_point)

                print(
                    f"📊 [{timestamp}] Validators: {performance_point['active_validators']}, "
                    f"Miners: {performance_point['active_miners']}, "
                    f"Total Stake: {performance_point['total_stake']} CORE"
                )

                # Wait before next measurement
                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Error monitoring network: {e}")
                await asyncio.sleep(60)

        # Save metrics to file
        metrics_file = os.path.join(
            self.wallets_dir, f"subnet_{subnet_uid}_metrics.json"
        )
        with open(metrics_file, "w") as f:
            json.dump(metrics, f, indent=2)

        print(f"✅ Monitoring completed. Metrics saved to: {metrics_file}")
        return metrics

    async def optimize_staking_strategy(self, account_name: str):
        """Optimize staking strategy based on network conditions"""
        print(f"=== Optimizing Staking Strategy for {account_name} ===")

        client = self.get_client(account_name)
        account = self.accounts[account_name]

        try:
            # Get current staking info
            staking_info = await client.get_staking_info(account.address)

            # Calculate potential rewards for different tiers
            tiers = ["base", "boost", "super", "satoshi"]
            tier_analysis = {}

            for tier in tiers:
                # Simulate rewards for this tier
                rewards = await client.simulate_rewards(
                    account.address, staking_tier=tier, time_horizon_days=30
                )

                tier_analysis[tier] = {
                    "multiplier": {
                        "base": 1.0,
                        "boost": 1.25,
                        "super": 1.5,
                        "satoshi": 2.0,
                    }[tier],
                    "estimated_rewards": rewards.get("estimated_rewards", 0),
                    "required_bitcoin": {
                        "base": 0,
                        "boost": 0.01,
                        "super": 0.1,
                        "satoshi": 1.0,
                    }[tier],
                    "roi_percentage": rewards.get("roi_percentage", 0),
                }

            # Find optimal tier
            optimal_tier = max(
                tier_analysis.keys(), key=lambda x: tier_analysis[x]["roi_percentage"]
            )

            print(f"📈 Staking Strategy Analysis:")
            print(f"Current Tier: {staking_info.get('staking_tier', 'none')}")
            print(f"Recommended Tier: {optimal_tier}")
            print(
                f"Estimated ROI: {tier_analysis[optimal_tier]['roi_percentage']:.2f}%"
            )

            # Display tier comparison
            print("\n🎯 Tier Comparison:")
            for tier, analysis in tier_analysis.items():
                print(
                    f"  {tier.capitalize()}: {analysis['multiplier']}x multiplier, "
                    f"ROI: {analysis['roi_percentage']:.2f}%, "
                    f"BTC Required: {analysis['required_bitcoin']} BTC"
                )

            # Suggest upgrade if beneficial
            current_tier = staking_info.get("staking_tier", "base")
            if optimal_tier != current_tier:
                print(f"\n💡 Suggestion: Upgrade from {current_tier} to {optimal_tier}")
                print(
                    f"   Estimated additional rewards: {tier_analysis[optimal_tier]['estimated_rewards'] - tier_analysis[current_tier]['estimated_rewards']:.2f} CORE/month"
                )

            return {
                "current_tier": current_tier,
                "optimal_tier": optimal_tier,
                "tier_analysis": tier_analysis,
            }

        except Exception as e:
            logger.error(f"Error optimizing staking strategy: {e}")
            raise

    async def advanced_reward_claiming(self, account_names: List[str]):
        """Advanced reward claiming with optimization"""
        print("=== Advanced Reward Claiming ===")

        total_rewards = {"core": 0, "bitcoin": 0, "gas_used": 0}

        for account_name in account_names:
            try:
                client = self.get_client(account_name)
                account = self.accounts[account_name]

                # Calculate pending rewards
                rewards = await client.calculate_rewards(account.address)

                print(f"📊 {account_name} - Pending rewards:")
                print(f"   CORE: {rewards.get('core_rewards', 0)} CORE")
                print(f"   Bitcoin: {rewards.get('bitcoin_rewards', 0)} BTC")

                # Check if claiming is profitable (rewards > gas cost)
                gas_cost = await client.estimate_gas_cost("claim_rewards")

                if (
                    rewards.get("core_rewards", 0) > gas_cost * 2
                ):  # 2x gas cost threshold
                    # Claim rewards
                    txn_hash = await client.claim_rewards(account.address)

                    print(f"✅ Rewards claimed: {account_name} - {txn_hash}")

                    total_rewards["core"] += rewards.get("core_rewards", 0)
                    total_rewards["bitcoin"] += rewards.get("bitcoin_rewards", 0)
                    total_rewards["gas_used"] += gas_cost

                else:
                    print(
                        f"⏳ Skipping {account_name} - rewards below gas cost threshold"
                    )

            except Exception as e:
                print(f"❌ Error claiming rewards for {account_name}: {e}")

        print(f"\n📈 Total Rewards Claimed:")
        print(f"   CORE: {total_rewards['core']} CORE")
        print(f"   Bitcoin: {total_rewards['bitcoin']} BTC")
        print(f"   Gas Used: {total_rewards['gas_used']} CORE")
        print(
            f"   Net Profit: {total_rewards['core'] - total_rewards['gas_used']} CORE"
        )

        return total_rewards

    async def setup_automated_operations(self, config: Dict):
        """Setup automated operations like auto-staking, auto-claiming"""
        print("=== Setting up Automated Operations ===")

        # This would integrate with external scheduling systems
        automation_config = {
            "auto_claim_rewards": config.get("auto_claim_rewards", False),
            "auto_restake": config.get("auto_restake", False),
            "auto_optimize_tier": config.get("auto_optimize_tier", False),
            "monitoring_interval": config.get("monitoring_interval", 3600),  # 1 hour
            "accounts": config.get("accounts", []),
        }

        # Save automation config
        config_file = os.path.join(self.wallets_dir, "automation_config.json")
        with open(config_file, "w") as f:
            json.dump(automation_config, f, indent=2)

        print(f"✅ Automation config saved to: {config_file}")
        print("💡 Use external cron job or task scheduler to run automated operations")

        # Example automation script
        automation_script = f"""#!/bin/bash
# ModernTensor Automation Script
# Run this script periodically via cron

cd {os.path.dirname(os.path.abspath(__file__))}

# Auto-claim rewards
python3 -c "
import asyncio
import json
from {__name__} import AdvancedUsageExample

async def auto_claim():
    with open('{config_file}', 'r') as f:
        config = json.load(f)
    
    example = AdvancedUsageExample()
    
    # Load accounts
    for account_config in config['accounts']:
        example.load_account(account_config['name'], account_config['password'])
    
    # Claim rewards
    await example.advanced_reward_claiming([acc['name'] for acc in config['accounts']])

if __name__ == '__main__':
    asyncio.run(auto_claim())
"
        """

        script_file = os.path.join(self.wallets_dir, "automation_script.sh")
        with open(script_file, "w") as f:
            f.write(automation_script)

        print(f"✅ Automation script created: {script_file}")
        print("💡 Make executable with: chmod +x automation_script.sh")

        return automation_config


async def main():
    """Main advanced usage demo"""
    print("🚀 ModernTensor Core Blockchain - Advanced Usage Examples")
    print("=" * 70)

    example = AdvancedUsageExample()

    print("\nAdvanced Features:")
    print("1. Multi-account batch operations")
    print("2. Subnet creation and management")
    print("3. Dual staking network setup")
    print("4. Network performance monitoring")
    print("5. Staking strategy optimization")
    print("6. Advanced reward claiming")
    print("7. Automated operations setup")
    print("8. Complete network deployment")
    print("0. Exit")

    choice = input("\nEnter your choice (0-8): ").strip()

    if choice == "0":
        print("Exiting...")
        return

    if choice == "1":
        # Multi-account setup
        accounts = input("Enter account names (comma-separated): ").strip().split(",")
        accounts = [acc.strip() for acc in accounts]

        passwords = []
        for account in accounts:
            password = getpass(f"Enter password for {account}: ")
            passwords.append(password)

        await example.multi_account_setup(accounts, passwords)

    elif choice == "2":
        # Subnet creation
        account_name = input("Enter account name: ").strip()
        password = getpass("Enter password: ")

        example.load_account(account_name, password)

        subnet_config = {
            "name": input("Enter subnet name: ").strip(),
            "description": input("Enter subnet description: ").strip(),
            "min_stake": int(input("Enter minimum stake: ") or "1000"),
            "max_validators": int(input("Enter max validators: ") or "64"),
            "max_miners": int(input("Enter max miners: ") or "256"),
            "incentive_model": input("Enter incentive model: ").strip() or "standard",
        }

        await example.create_subnet(account_name, subnet_config)

    elif choice == "3":
        # Dual staking network setup
        print("Setting up dual staking network requires pre-configured accounts...")
        print("Please ensure you have validator and miner accounts ready.")

        # Example configuration
        network_config = {
            "validators": [
                {
                    "account_name": "validator1",
                    "subnet_uid": 1,
                    "stake_amount": 10000,
                    "staking_tier": "super",
                    "enable_dual_staking": True,
                    "btc_amount": 0.1,
                }
            ],
            "miners": [
                {
                    "account_name": "miner1",
                    "subnet_uid": 1,
                    "stake_amount": 1000,
                    "api_endpoint": "http://localhost:8080",
                    "staking_tier": "boost",
                }
            ],
        }

        await example.setup_dual_staking_network(network_config)

    elif choice == "4":
        # Network monitoring
        subnet_uid = int(input("Enter subnet UID to monitor: "))
        duration = int(input("Enter monitoring duration in minutes: ") or "60")

        await example.monitor_network_performance(subnet_uid, duration)

    elif choice == "5":
        # Staking optimization
        account_name = input("Enter account name: ").strip()
        password = getpass("Enter password: ")

        example.load_account(account_name, password)

        await example.optimize_staking_strategy(account_name)

    elif choice == "6":
        # Advanced reward claiming
        accounts = input("Enter account names (comma-separated): ").strip().split(",")
        accounts = [acc.strip() for acc in accounts]

        for account in accounts:
            password = getpass(f"Enter password for {account}: ")
            example.load_account(account, password)

        await example.advanced_reward_claiming(accounts)

    elif choice == "7":
        # Automated operations
        automation_config = {
            "auto_claim_rewards": True,
            "auto_restake": False,
            "auto_optimize_tier": True,
            "monitoring_interval": 3600,
            "accounts": [],
        }

        await example.setup_automated_operations(automation_config)

    elif choice == "8":
        # Complete network deployment
        print("Complete network deployment requires extensive configuration...")
        print("Please refer to the documentation for detailed setup instructions.")

    else:
        print("Invalid choice. Please try again.")


if __name__ == "__main__":
    asyncio.run(main())
