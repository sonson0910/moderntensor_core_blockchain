#!/usr/bin/env python3
"""
Auto-register all entities from JSON files to ModernTensor contract
"""

import json
import asyncio
from pathlib import Path
from web3 import Web3
from eth_account import Account


async def register_all_entities():
    print("🚀 REGISTERING ALL ENTITIES TO MODERNTENSOR CONTRACT")
    print("=" * 60)

    # Contract configuration
    contract_address = "0x594fc12B3e3AB824537b947765dd9409DAAAa143"
    core_token_address = "0x7B74e4868c8C500D6143CEa53a5d2F94e94c7637"
    deployer_private_key = (
        "a07b6e0db803f9a21ffd1001c76b0aa0b313aaba8faab8c771af47301c4452b4"
    )
    rpc_url = "https://rpc.test.btcs.network"

    # Initialize Web3
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    deployer_account = Account.from_key(deployer_private_key)

    print(f"📍 Contract: {contract_address}")
    print(f"💰 Deployer: {deployer_account.address}")
    print(
        f"💳 Balance: {Web3.from_wei(w3.eth.get_balance(deployer_account.address), 'ether')} CORE"
    )

    # Load contract ABI
    try:
        abi_path = "../moderntensor_aptos/mt_core/smartcontract/artifacts/contracts/ModernTensor.sol/ModernTensor.json"
        with open(abi_path, "r") as f:
            contract_data = json.load(f)
            contract_abi = contract_data["abi"]
    except Exception as e:
        print(f"❌ Error loading contract ABI: {e}")
        return False

    # Create contract instance
    contract = w3.eth.contract(address=contract_address, abi=contract_abi)
    print("✅ Contract loaded")

    # ERC20 ABI for token approval
    erc20_abi = [
        {
            "constant": False,
            "inputs": [
                {"name": "_spender", "type": "address"},
                {"name": "_value", "type": "uint256"},
            ],
            "name": "approve",
            "outputs": [{"name": "", "type": "bool"}],
            "type": "function",
        }
    ]

    # Create CORE token contract
    core_token = w3.eth.contract(address=core_token_address, abi=erc20_abi)
    print("✅ CORE token contract loaded")

    # Load entities from JSON files
    entities_dir = Path("entities")
    if not entities_dir.exists():
        print("❌ Entities directory not found")
        return False

    miners = []
    validators = []

    for i in range(1, 3):
        miner_file = entities_dir / f"miner_{i}.json"
        if miner_file.exists():
            with open(miner_file, "r") as f:
                miners.append(json.load(f))

    for i in range(1, 4):
        validator_file = entities_dir / f"validator_{i}.json"
        if validator_file.exists():
            with open(validator_file, "r") as f:
                validators.append(json.load(f))

    print(f"📋 Found {len(miners)} miners and {len(validators)} validators")

    # Register miners
    print("\n🔨 REGISTERING MINERS:")
    for i, miner in enumerate(miners):
        address = miner["address"]
        private_key = miner["private_key"]
        stake_amount = int(float(miner["stake_amount"]) * 10**18)  # Convert to wei
        api_endpoint = miner["api_endpoint"]

        print(f"\nMiner {i+1}: {address}")
        print(f"  💰 Stake: {miner['stake_amount']} CORE")
        print(f"  🔗 Endpoint: {api_endpoint}")

        try:
            # Create account for this miner
            miner_account = Account.from_key(private_key)

            # Get current balance
            balance = w3.eth.get_balance(address)
            balance_eth = Web3.from_wei(balance, "ether")
            print(f"  💳 Balance: {balance_eth} CORE")

            if balance_eth < 0.1:
                print(f"  ⚠️ Low balance, may need more CORE for gas")

            # First, approve CORE token
            approve_txn = core_token.functions.approve(
                contract_address, stake_amount
            ).build_transaction(
                {
                    "from": address,
                    "nonce": w3.eth.get_transaction_count(address),
                    "gas": 100000,
                    "gasPrice": w3.to_wei("30", "gwei"),
                }
            )

            # Sign and send approval
            signed_approve = w3.eth.account.sign_transaction(approve_txn, private_key)
            approve_hash = w3.eth.send_raw_transaction(signed_approve.raw_transaction)
            print(f"  📝 Approval sent: {approve_hash.hex()}")

            # Wait for approval confirmation
            w3.eth.wait_for_transaction_receipt(approve_hash, timeout=60)
            print(f"  ✅ CORE tokens approved")

            # Build registration transaction
            txn = contract.functions.registerMiner(
                0,  # subnetId (use default subnet)
                stake_amount,  # coreStake
                0,  # bitcoinStake
                api_endpoint,  # endpoint
            ).build_transaction(
                {
                    "from": address,
                    "nonce": w3.eth.get_transaction_count(address),
                    "gas": 300000,
                    "gasPrice": w3.to_wei("30", "gwei"),
                }
            )

            # Sign and send transaction
            signed_txn = w3.eth.account.sign_transaction(txn, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)

            print(f"  📡 Transaction sent: {tx_hash.hex()}")

            # Wait for confirmation
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

            if receipt.status == 1:
                print(f"  ✅ Miner registered successfully!")
            else:
                print(f"  ❌ Transaction failed")

        except Exception as e:
            print(f"  ❌ Error registering miner: {e}")

    # Register validators
    print("\n✅ REGISTERING VALIDATORS:")
    for i, validator in enumerate(validators):
        address = validator["address"]
        private_key = validator["private_key"]
        stake_amount = int(float(validator["stake_amount"]) * 10**18)  # Convert to wei
        api_endpoint = validator["api_endpoint"]

        print(f"\nValidator {i+1}: {address}")
        print(f"  💰 Stake: {validator['stake_amount']} CORE")
        print(f"  🔗 Endpoint: {api_endpoint}")

        try:
            # Create account for this validator
            validator_account = Account.from_key(private_key)

            # Get current balance
            balance = w3.eth.get_balance(address)
            balance_eth = Web3.from_wei(balance, "ether")
            print(f"  💳 Balance: {balance_eth} CORE")

            if balance_eth < 0.1:
                print(f"  ⚠️ Low balance, may need more CORE for gas")

            # First, approve CORE token
            approve_txn = core_token.functions.approve(
                contract_address, stake_amount
            ).build_transaction(
                {
                    "from": address,
                    "nonce": w3.eth.get_transaction_count(address),
                    "gas": 100000,
                    "gasPrice": w3.to_wei("30", "gwei"),
                }
            )

            # Sign and send approval
            signed_approve = w3.eth.account.sign_transaction(approve_txn, private_key)
            approve_hash = w3.eth.send_raw_transaction(signed_approve.raw_transaction)
            print(f"  📝 Approval sent: {approve_hash.hex()}")

            # Wait for approval confirmation
            w3.eth.wait_for_transaction_receipt(approve_hash, timeout=60)
            print(f"  ✅ CORE tokens approved")

            # Build registration transaction
            txn = contract.functions.registerValidator(
                0,  # subnetId (use default subnet)
                stake_amount,  # coreStake
                0,  # bitcoinStake
                api_endpoint,  # endpoint
            ).build_transaction(
                {
                    "from": address,
                    "nonce": w3.eth.get_transaction_count(address),
                    "gas": 300000,
                    "gasPrice": w3.to_wei("30", "gwei"),
                }
            )

            # Sign and send transaction
            signed_txn = w3.eth.account.sign_transaction(txn, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)

            print(f"  📡 Transaction sent: {tx_hash.hex()}")

            # Wait for confirmation
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

            if receipt.status == 1:
                print(f"  ✅ Validator registered successfully!")
            else:
                print(f"  ❌ Transaction failed")

        except Exception as e:
            print(f"  ❌ Error registering validator: {e}")

    print("\n🎉 REGISTRATION COMPLETE!")
    print(
        f"🔗 Contract Explorer: https://scan.test.btcs.network/address/{contract_address}"
    )

    return True


if __name__ == "__main__":
    asyncio.run(register_all_entities())
