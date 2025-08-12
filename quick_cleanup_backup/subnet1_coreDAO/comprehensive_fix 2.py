#!/usr/bin/env python3
"""
Comprehensive fix for registration issues
"""

import json
from pathlib import Path
from web3 import Web3
from eth_account import Account


def comprehensive_fix():
    print("🔧 COMPREHENSIVE REGISTRATION FIX")
    print("=" * 50)

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

    # Step 1: Check contract ownership and roles
    print("\n🔐 CHECKING CONTRACT OWNERSHIP:")
    try:
        # Check if deployer has admin role
        admin_role = contract.functions.DEFAULT_ADMIN_ROLE().call()
        has_admin = contract.functions.hasRole(
            admin_role, deployer_account.address
        ).call()
        print(f"  👤 Deployer has admin role: {has_admin}")

        # Check governance role
        governance_role = contract.functions.GOVERNANCE_ROLE().call()
        has_governance = contract.functions.hasRole(
            governance_role, deployer_account.address
        ).call()
        print(f"  🏛️ Deployer has governance role: {has_governance}")

    except Exception as e:
        print(f"  ❌ Error checking roles: {e}")

    # Step 2: Check and fix subnet status
    print("\n📊 CHECKING SUBNET STATUS:")

    # Try different subnet IDs
    for subnet_id in [0, 1]:
        print(f"\n  🔍 Checking Subnet {subnet_id}:")
        try:
            # Try to get subnet info using different function names
            subnet_functions = ["subnetStatic", "subnetDynamic", "getSubnetInfo"]

            for func_name in subnet_functions:
                if hasattr(contract.functions, func_name):
                    try:
                        result = getattr(contract.functions, func_name)(
                            subnet_id
                        ).call()
                        print(f"    ✅ {func_name}: {result}")
                    except Exception as e:
                        print(f"    ⚠️ {func_name} failed: {e}")

        except Exception as e:
            print(f"    ❌ Error checking subnet {subnet_id}: {e}")

    # Step 3: Try to enable registration for subnet 1
    print("\n🔓 ENABLING REGISTRATION:")

    try:
        # Check if there's a function to enable registration
        enable_functions = [
            "enableSubnetRegistration",
            "openRegistration",
            "setRegistrationOpen",
            "updateSubnetRegistration",
        ]

        registration_enabled = False

        for func_name in enable_functions:
            if hasattr(contract.functions, func_name):
                try:
                    print(f"  🎯 Trying {func_name} for subnet 1...")

                    func = getattr(contract.functions, func_name)

                    # Try with different parameters
                    params_to_try = [
                        [1, True],  # subnet_id, enabled
                        [1],  # subnet_id only
                        [True],  # enabled only
                        [],  # no params
                    ]

                    for params in params_to_try:
                        try:
                            if params:
                                txn = func(*params).build_transaction(
                                    {
                                        "from": deployer_account.address,
                                        "nonce": w3.eth.get_transaction_count(
                                            deployer_account.address
                                        ),
                                        "gas": 200000,
                                        "gasPrice": w3.to_wei("30", "gwei"),
                                    }
                                )
                            else:
                                txn = func().build_transaction(
                                    {
                                        "from": deployer_account.address,
                                        "nonce": w3.eth.get_transaction_count(
                                            deployer_account.address
                                        ),
                                        "gas": 200000,
                                        "gasPrice": w3.to_wei("30", "gwei"),
                                    }
                                )

                            signed_txn = w3.eth.account.sign_transaction(
                                txn, deployer_private_key
                            )
                            tx_hash = w3.eth.send_raw_transaction(
                                signed_txn.raw_transaction
                            )

                            print(f"    📡 Transaction sent: {tx_hash.hex()}")
                            receipt = w3.eth.wait_for_transaction_receipt(
                                tx_hash, timeout=60
                            )

                            if receipt.status == 1:
                                print(
                                    f"    ✅ {func_name} successful with params {params}!"
                                )
                                registration_enabled = True
                                break
                            else:
                                print(f"    ❌ {func_name} failed with params {params}")

                        except Exception as e:
                            print(f"    ⚠️ {func_name} with params {params}: {e}")

                    if registration_enabled:
                        break

                except Exception as e:
                    print(f"  ❌ Error with {func_name}: {e}")

        if not registration_enabled:
            print("  ⚠️ Could not enable registration automatically")
            print(
                "  💡 Registration might already be enabled or require manual intervention"
            )

    except Exception as e:
        print(f"  ❌ Error enabling registration: {e}")

    # Step 4: Try registration with minimal stakes
    print("\n🔨 ATTEMPTING REGISTRATION WITH MINIMAL STAKES:")

    # Load one entity for testing
    entities_dir = Path("entities")
    miner_file = entities_dir / "miner_1.json"

    if miner_file.exists():
        with open(miner_file, "r") as f:
            miner = json.load(f)

        address = miner["address"]
        private_key = miner["private_key"]
        api_endpoint = miner["api_endpoint"]

        print(f"  🧪 Testing with Miner: {address}")

        # Try different stake amounts
        stake_amounts = [
            int(0.001 * 10**18),  # 0.001 CORE
            int(0.01 * 10**18),  # 0.01 CORE
            int(0.05 * 10**18),  # 0.05 CORE
        ]

        # Try different subnet IDs
        subnet_ids = [0, 1]

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

        registration_success = False

        for subnet_id in subnet_ids:
            if registration_success:
                break

            for stake_amount in stake_amounts:
                if registration_success:
                    break

                print(
                    f"\n    📋 Trying: Subnet {subnet_id}, Stake {Web3.from_wei(stake_amount, 'ether')} CORE"
                )

                try:
                    # Approve tokens
                    nonce = w3.eth.get_transaction_count(address)

                    approve_txn = core_token.functions.approve(
                        contract_address, stake_amount
                    ).build_transaction(
                        {
                            "from": address,
                            "nonce": nonce,
                            "gas": 100000,
                            "gasPrice": w3.to_wei("30", "gwei"),
                        }
                    )

                    signed_approve = w3.eth.account.sign_transaction(
                        approve_txn, private_key
                    )
                    approve_hash = w3.eth.send_raw_transaction(
                        signed_approve.raw_transaction
                    )
                    w3.eth.wait_for_transaction_receipt(approve_hash, timeout=60)
                    print(f"      ✅ Tokens approved")

                    # Try registration
                    nonce = w3.eth.get_transaction_count(address)

                    register_txn = contract.functions.registerMiner(
                        subnet_id, stake_amount, 0, api_endpoint  # bitcoin stake
                    ).build_transaction(
                        {
                            "from": address,
                            "nonce": nonce,
                            "gas": 500000,  # Increased gas
                            "gasPrice": w3.to_wei("50", "gwei"),  # Higher gas price
                        }
                    )

                    signed_register = w3.eth.account.sign_transaction(
                        register_txn, private_key
                    )
                    register_hash = w3.eth.send_raw_transaction(
                        signed_register.raw_transaction
                    )

                    print(f"      📡 Registration sent: {register_hash.hex()}")
                    receipt = w3.eth.wait_for_transaction_receipt(
                        register_hash, timeout=120
                    )

                    if receipt.status == 1:
                        print(f"      🎉 REGISTRATION SUCCESS!")
                        print(f"         Subnet: {subnet_id}")
                        print(
                            f"         Stake: {Web3.from_wei(stake_amount, 'ether')} CORE"
                        )
                        registration_success = True
                        break
                    else:
                        print(f"      ❌ Registration failed")

                        # Check if we can get revert reason
                        try:
                            w3.eth.call(register_txn, receipt.blockNumber)
                        except Exception as revert_error:
                            print(f"         Revert reason: {revert_error}")

                except Exception as e:
                    print(f"      ❌ Error: {e}")

        if not registration_success:
            print(f"\n  ❌ All registration attempts failed")

    # Step 5: Final status check
    print(f"\n📊 FINAL STATUS CHECK:")
    try:
        # Check network stats
        network_stats = contract.functions.getNetworkStats().call()
        print(f"  👥 Total Miners: {network_stats[0]}")
        print(f"  🛡️ Total Validators: {network_stats[1]}")
        print(f"  💰 Total Staked: {Web3.from_wei(network_stats[2], 'ether')} CORE")

    except Exception as e:
        print(f"  ❌ Error checking final status: {e}")

    print(f"\n🎯 RECOMMENDATIONS:")
    print(f"1. Check contract on explorer for recent transactions")
    print(f"2. Verify contract deployment is correct")
    print(f"3. Consider manual registration via contract explorer")
    print(f"4. Check if contract requires specific initialization")

    return True


if __name__ == "__main__":
    comprehensive_fix()
