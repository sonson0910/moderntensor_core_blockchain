#!/usr/bin/env python3
"""
Create subnet and register entities
"""

import json
from pathlib import Path
from web3 import Web3
from eth_account import Account


def create_subnet_and_register():
    print("🛠️ CREATING SUBNET AND REGISTERING ENTITIES")
    print("=" * 55)

    # Configuration
    contract_address = "0x594fc12B3e3AB824537b947765dd9409DAAAa143"
    core_token_address = "0x7B74e4868c8C500D6143CEa53a5d2F94e94c7637"
    deployer_private_key = (
        "a07b6e0db803f9a21ffd1001c76b0aa0b313aaba8faab8c771af47301c4452b4"
    )
    rpc_url = "https://rpc.test.btcs.network"

    # Initialize Web3
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    deployer_account = Account.from_key(deployer_private_key)

    print(f"💰 Deployer: {deployer_account.address}")

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

    # First, try to create a new subnet (subnet 1)
    print("\n🛠️ CREATING NEW SUBNET:")
    try:
        create_txn = contract.functions.createSubnet(
            "Subnet1",  # name
            "Test subnet for entities",  # description
            10,  # maxMiners
            10,  # maxValidators
            int(0.01 * 10**18),  # minMinerStake (0.01 CORE)
            int(0.01 * 10**18),  # minValidatorStake (0.01 CORE)
        ).build_transaction(
            {
                "from": deployer_account.address,
                "nonce": w3.eth.get_transaction_count(deployer_account.address),
                "gas": 500000,
                "gasPrice": w3.to_wei("30", "gwei"),
            }
        )

        signed_txn = w3.eth.account.sign_transaction(create_txn, deployer_private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)

        print(f"  📡 Create subnet transaction: {tx_hash.hex()}")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

        if receipt.status == 1:
            print("  ✅ Subnet created successfully!")
            subnet_id = 1  # Use the new subnet
        else:
            print("  ❌ Failed to create subnet, using subnet 0")
            subnet_id = 0

    except Exception as e:
        print(f"  ⚠️ Error creating subnet (using subnet 0): {e}")
        subnet_id = 0

    # Load entities
    entities_dir = Path("entities")
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

    print(f"\n📋 Found {len(miners)} miners and {len(validators)} validators")
    print(f"🎯 Using subnet ID: {subnet_id}")

    # ERC20 ABI for approval
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
    core_token = w3.eth.contract(address=core_token_address, abi=erc20_abi)

    # Register miners with lower stake
    print("\n🔨 REGISTERING MINERS:")
    for i, miner in enumerate(miners):
        address = miner["address"]
        private_key = miner["private_key"]
        stake_amount = int(0.01 * 10**18)  # Lower stake: 0.01 CORE
        api_endpoint = miner["api_endpoint"]

        print(f"\nMiner {i+1}: {address}")
        print(f"  💰 Stake: 0.01 CORE (reduced)")

        try:
            # Approve tokens
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

            signed_approve = w3.eth.account.sign_transaction(approve_txn, private_key)
            approve_hash = w3.eth.send_raw_transaction(signed_approve.raw_transaction)
            w3.eth.wait_for_transaction_receipt(approve_hash, timeout=60)
            print(f"  ✅ Tokens approved")

            # Register
            register_txn = contract.functions.registerMiner(
                subnet_id, stake_amount, 0, api_endpoint
            ).build_transaction(
                {
                    "from": address,
                    "nonce": w3.eth.get_transaction_count(address),
                    "gas": 300000,
                    "gasPrice": w3.to_wei("30", "gwei"),
                }
            )

            signed_register = w3.eth.account.sign_transaction(register_txn, private_key)
            register_hash = w3.eth.send_raw_transaction(signed_register.raw_transaction)

            print(f"  📡 Registration sent: {register_hash.hex()}")
            receipt = w3.eth.wait_for_transaction_receipt(register_hash, timeout=60)

            if receipt.status == 1:
                print(f"  ✅ Miner registered successfully!")
            else:
                print(f"  ❌ Registration failed")

        except Exception as e:
            print(f"  ❌ Error: {e}")

    # Register validators
    print("\n✅ REGISTERING VALIDATORS:")
    for i, validator in enumerate(validators):
        address = validator["address"]
        private_key = validator["private_key"]
        stake_amount = int(0.01 * 10**18)  # Lower stake: 0.01 CORE
        api_endpoint = validator["api_endpoint"]

        print(f"\nValidator {i+1}: {address}")
        print(f"  💰 Stake: 0.01 CORE (reduced)")

        try:
            # Approve tokens
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

            signed_approve = w3.eth.account.sign_transaction(approve_txn, private_key)
            approve_hash = w3.eth.send_raw_transaction(signed_approve.raw_transaction)
            w3.eth.wait_for_transaction_receipt(approve_hash, timeout=60)
            print(f"  ✅ Tokens approved")

            # Register
            register_txn = contract.functions.registerValidator(
                subnet_id, stake_amount, 0, api_endpoint
            ).build_transaction(
                {
                    "from": address,
                    "nonce": w3.eth.get_transaction_count(address),
                    "gas": 300000,
                    "gasPrice": w3.to_wei("30", "gwei"),
                }
            )

            signed_register = w3.eth.account.sign_transaction(register_txn, private_key)
            register_hash = w3.eth.send_raw_transaction(signed_register.raw_transaction)

            print(f"  📡 Registration sent: {register_hash.hex()}")
            receipt = w3.eth.wait_for_transaction_receipt(register_hash, timeout=60)

            if receipt.status == 1:
                print(f"  ✅ Validator registered successfully!")
            else:
                print(f"  ❌ Registration failed")

        except Exception as e:
            print(f"  ❌ Error: {e}")

    print("\n🎉 PROCESS COMPLETE!")
    print(
        "🔍 Run: export CORE_CONTRACT_ADDRESS='0x594fc12B3e3AB824537b947765dd9409DAAAa143' && python final_network_check.py"
    )


if __name__ == "__main__":
    create_subnet_and_register()
