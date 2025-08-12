#!/usr/bin/env python3
"""
Mint CORE tokens for entities
"""

import json
from pathlib import Path
from web3 import Web3
from eth_account import Account


def mint_core_tokens():
    print("🪙 MINTING CORE TOKENS FOR ENTITIES")
    print("=" * 50)

    # Configuration
    core_token_address = "0x7B74e4868c8C500D6143CEa53a5d2F94e94c7637"
    deployer_private_key = (
        "a07b6e0db803f9a21ffd1001c76b0aa0b313aaba8faab8c771af47301c4452b4"
    )
    rpc_url = "https://rpc.test.btcs.network"

    # Initialize Web3
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    deployer_account = Account.from_key(deployer_private_key)

    print(f"💰 Deployer: {deployer_account.address}")

    # ERC20 ABI with mint function
    erc20_abi = [
        {
            "constant": False,
            "inputs": [
                {"name": "to", "type": "address"},
                {"name": "amount", "type": "uint256"},
            ],
            "name": "mint",
            "outputs": [],
            "type": "function",
        },
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function",
        },
    ]

    # Create CORE token contract
    core_token = w3.eth.contract(address=core_token_address, abi=erc20_abi)
    print("✅ CORE token contract loaded")

    # Load entities
    entities_dir = Path("entities")
    all_entities = []

    # Load miners
    for i in range(1, 3):
        miner_file = entities_dir / f"miner_{i}.json"
        if miner_file.exists():
            with open(miner_file, "r") as f:
                entity = json.load(f)
                entity["type"] = "miner"
                entity["required_tokens"] = 0.1  # 0.1 CORE (more than 0.05 needed)
                all_entities.append(entity)

    # Load validators
    for i in range(1, 4):
        validator_file = entities_dir / f"validator_{i}.json"
        if validator_file.exists():
            with open(validator_file, "r") as f:
                entity = json.load(f)
                entity["type"] = "validator"
                entity["required_tokens"] = 0.15  # 0.15 CORE (more than 0.08 needed)
                all_entities.append(entity)

    print(f"📋 Found {len(all_entities)} entities to mint tokens for")

    # Mint tokens for each entity
    for i, entity in enumerate(all_entities):
        address = entity["address"]
        entity_type = entity["type"]
        amount = entity["required_tokens"]
        amount_wei = int(amount * 10**18)

        print(f"\n🪙 MINTING for {entity_type.upper()} {i+1}: {address}")
        print(f"  💰 Amount: {amount} CORE")

        try:
            # Check current balance
            current_balance = core_token.functions.balanceOf(address).call()
            current_balance_ether = Web3.from_wei(current_balance, "ether")
            print(f"  📊 Current balance: {current_balance_ether} CORE")

            if current_balance_ether >= amount:
                print(f"  ✅ Already has sufficient tokens")
                continue

            # Build mint transaction
            mint_txn = core_token.functions.mint(address, amount_wei).build_transaction(
                {
                    "from": deployer_account.address,
                    "nonce": w3.eth.get_transaction_count(deployer_account.address),
                    "gas": 100000,
                    "gasPrice": w3.to_wei("30", "gwei"),
                }
            )

            # Sign and send transaction
            signed_txn = w3.eth.account.sign_transaction(mint_txn, deployer_private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)

            print(f"  📡 Mint transaction sent: {tx_hash.hex()}")

            # Wait for confirmation
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

            if receipt.status == 1:
                # Check new balance
                new_balance = core_token.functions.balanceOf(address).call()
                new_balance_ether = Web3.from_wei(new_balance, "ether")
                print(
                    f"  ✅ Minted successfully! New balance: {new_balance_ether} CORE"
                )
            else:
                print(f"  ❌ Mint transaction failed")

        except Exception as e:
            print(f"  ❌ Error minting tokens: {e}")

    print("\n🎉 TOKEN MINTING COMPLETE!")
    print("\n📝 Next steps:")
    print("1. Run: python register_all_entities.py")
    print("2. Verify: python final_network_check.py")


if __name__ == "__main__":
    mint_core_tokens()
