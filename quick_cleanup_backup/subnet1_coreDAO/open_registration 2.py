#!/usr/bin/env python3
"""
Open registration for subnet
"""

import json
from web3 import Web3
from eth_account import Account


def open_registration():
    print("🔓 OPENING REGISTRATION FOR SUBNET")
    print("=" * 40)

    # Configuration
    contract_address = "0x594fc12B3e3AB824537b947765dd9409DAAAa143"
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

    # Check subnet 1 status first
    subnet_id = 1
    print(f"\n📊 Checking subnet {subnet_id} status:")

    try:
        # Check if we can read subnet data
        result = contract.functions.subnets(subnet_id).call()
        print(f"  📍 Subnet {subnet_id} exists")
        print(f"  🏗️ Total miners: {result[0] if result else 'unknown'}")
        print(f"  🏗️ Total validators: {result[1] if result else 'unknown'}")
    except Exception as e:
        print(f"  ⚠️ Cannot read subnet {subnet_id}: {e}")
        print(f"  ℹ️ Trying subnet 0 instead...")
        subnet_id = 0

    # Check available functions
    print(f"\n🔍 Available contract functions:")
    function_names = [
        func for func in dir(contract.functions) if not func.startswith("_")
    ]
    for func in function_names[:10]:  # Show first 10
        print(f"  - {func}")

    # Try to find and call registration opening function
    print(f"\n🔓 Attempting to open registration for subnet {subnet_id}:")

    # Common function names that might open registration
    possible_functions = [
        "openRegistration",
        "enableRegistration",
        "setRegistrationOpen",
        "toggleRegistration",
    ]

    registration_opened = False

    for func_name in possible_functions:
        if hasattr(contract.functions, func_name):
            try:
                print(f"  🎯 Trying {func_name}...")

                # Try to call the function
                func = getattr(contract.functions, func_name)

                # Try different parameter combinations
                try:
                    txn = func(subnet_id).build_transaction(
                        {
                            "from": deployer_account.address,
                            "nonce": w3.eth.get_transaction_count(
                                deployer_account.address
                            ),
                            "gas": 200000,
                            "gasPrice": w3.to_wei("30", "gwei"),
                        }
                    )
                except:
                    # Try without subnet parameter
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

                signed_txn = w3.eth.account.sign_transaction(txn, deployer_private_key)
                tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)

                print(f"    📡 Transaction sent: {tx_hash.hex()}")
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

                if receipt.status == 1:
                    print(f"    ✅ {func_name} successful!")
                    registration_opened = True
                    break
                else:
                    print(f"    ❌ {func_name} failed")

            except Exception as e:
                print(f"    ⚠️ {func_name} error: {e}")

    if not registration_opened:
        print(f"\n⚠️ Could not find registration opening function")
        print(f"💡 Registration might already be open or use different method")

    print(f"\n📝 Next steps:")
    print(f"1. Try registering entities again")
    print(f"2. Check contract explorer for admin functions")
    print(f"3. Verify subnet {subnet_id} is ready for registration")


if __name__ == "__main__":
    open_registration()
