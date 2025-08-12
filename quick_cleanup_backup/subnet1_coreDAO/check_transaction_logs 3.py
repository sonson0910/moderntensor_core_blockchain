#!/usr/bin/env python3
"""
Check transaction logs for revert reasons
"""

from web3 import Web3


def check_transaction_logs():
    print("🔍 CHECKING TRANSACTION LOGS")
    print("=" * 40)

    rpc_url = "https://rpc.test.btcs.network"
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    # Recent failed transaction hashes from the logs
    failed_txs = [
        "0x29a642399a125ecdaca6999981f8943ffbbad8ae32797ab2d03fb78252e797b9",  # Miner 1
        "0x933d3305568701fdf23ee4e2c70c559ccbfa8b895c78ed6e080fe16a49dc5115",  # Miner 2
        "0x6832a3570cbb05a8f3f0a0ade20fdc27c957c760b819e8b21d261c4298a4420b",  # Validator 1
    ]

    for i, tx_hash in enumerate(failed_txs):
        print(f"\n📋 Checking Transaction {i+1}:")
        print(f"  🔗 Hash: {tx_hash}")

        try:
            # Get transaction receipt
            receipt = w3.eth.get_transaction_receipt(tx_hash)
            print(f"  📊 Status: {'Success' if receipt.status == 1 else 'Failed'}")
            print(f"  ⛽ Gas Used: {receipt.gasUsed}")

            # Get transaction details
            tx = w3.eth.get_transaction(tx_hash)
            print(f"  💰 Value: {Web3.from_wei(tx.value, 'ether')} CORE")
            print(f"  🎯 To: {tx.to}")

            # Check if there are any logs
            if receipt.logs:
                print(f"  📜 Logs: {len(receipt.logs)} events")
                for j, log in enumerate(receipt.logs):
                    print(f"    Event {j+1}: {log.address}")
            else:
                print(f"  📜 No logs (likely reverted)")

        except Exception as e:
            print(f"  ❌ Error checking transaction: {e}")

    print("\n🎯 POSSIBLE ISSUES:")
    print("1. Registration not open for subnet")
    print("2. Already registered (duplicate registration)")
    print("3. Insufficient permissions")
    print("4. Contract function signature mismatch")
    print("5. Minimum stake requirements not met")


if __name__ == "__main__":
    check_transaction_logs()
