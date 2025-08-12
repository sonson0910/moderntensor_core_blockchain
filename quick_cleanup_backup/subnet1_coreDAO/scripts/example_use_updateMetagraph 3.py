#!/usr/bin/env python3
"""
Example: How to use the new updateMetagraph() function in ModernTensor.sol
Replaces individual updateMinerScores() calls with efficient batch processing
"""

import json
from typing import Dict, List
from web3 import Web3
from pathlib import Path


class MetagraphUpdater:
    """Example class showing how to use updateMetagraph function"""

    def __init__(self, contract_address: str, rpc_url: str):
        self.contract_address = contract_address
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))

        # ModernTensor ABI with new updateMetagraph function
        self.contract_abi = [
            {
                "inputs": [
                    {"name": "minerAddrs", "type": "address[]"},
                    {"name": "newPerformances", "type": "uint64[]"},
                    {"name": "newTrustScores", "type": "uint64[]"},
                ],
                "name": "updateMetagraph",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "inputs": [
                    {"name": "roundId", "type": "uint64"},
                    {"name": "minerAddrs", "type": "address[]"},
                    {"name": "newPerformances", "type": "uint64[]"},
                    {"name": "newTrustScores", "type": "uint64[]"},
                    {"name": "rewards", "type": "uint256[]"},
                ],
                "name": "updateMetagraphWithConsensusRound",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            },
        ]

        self.contract = self.w3.eth.contract(
            address=self.contract_address, abi=self.contract_abi
        )

    def submit_consensus_batch(
        self, final_scores: Dict[str, float], validator_private_key: str
    ):
        """
        Submit consensus results using batch updateMetagraph() function
        Much more efficient than individual updateMinerScores() calls
        """
        print(
            f"🔗 Submitting {len(final_scores)} consensus scores via batch updateMetagraph..."
        )

        # Prepare batch data
        addresses = []
        performances = []
        trust_scores = []

        # UID to address mapping (reuse from existing code)
        uid_to_address_map = {
            "subnet1_miner_001": "0xd89fBAbb72190ed22F012ADFC693ad974bAD3005",
            "subnet1_miner_002": "0x16102CA8BEF74fb6214AF352989b664BF0e50498",
            "7375626e6574315f6d696e65725f303031": "0xd89fBAbb72190ed22F012ADFC693ad974bAD3005",
            "7375626e6574315f6d696e65725f303032": "0x16102CA8BEF74fb6214AF352989b664BF0e50498",
        }

        for miner_uid, consensus_score in final_scores.items():
            # Find miner address
            miner_address = uid_to_address_map.get(miner_uid)
            if not miner_address:
                print(f"⚠️ Miner {miner_uid} address not found, skipping...")
                continue

            # Scale score (0.0-1.0 -> 0-1000000 for 6 decimal precision)
            score_scaled = int(consensus_score * 1_000_000)
            score_scaled = max(0, min(1_000_000, score_scaled))

            addresses.append(miner_address)
            performances.append(score_scaled)
            trust_scores.append(score_scaled)

        if not addresses:
            print("❌ No valid miners to update")
            return None

        print(f"📊 Batch update for {len(addresses)} miners:")
        for i, addr in enumerate(addresses):
            print(f"   {addr}: performance={performances[i]}, trust={trust_scores[i]}")

        try:
            # Create validator account
            validator_account = self.w3.eth.account.from_key(validator_private_key)

            # Build transaction
            transaction = self.contract.functions.updateMetagraph(
                addresses, performances, trust_scores
            ).build_transaction(
                {
                    "from": validator_account.address,
                    "gas": 200000
                    + (50000 * len(addresses)),  # Base gas + per-miner gas
                    "gasPrice": self.w3.to_wei(20, "gwei"),
                    "nonce": self.w3.eth.get_transaction_count(
                        validator_account.address
                    ),
                }
            )

            # Sign and send
            signed_txn = validator_account.sign_transaction(transaction)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            tx_hash_hex = tx_hash.hex()

            print(f"✅ Batch updateMetagraph submitted: {tx_hash_hex}")
            print(f"⛽ Estimated gas: {transaction['gas']:,}")

            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
            print(f"🎉 Transaction confirmed! Gas used: {receipt['gasUsed']:,}")

            return tx_hash_hex

        except Exception as e:
            print(f"❌ Batch updateMetagraph failed: {e}")
            return None

    def submit_consensus_with_round(
        self,
        round_id: int,
        final_scores: Dict[str, float],
        rewards: Dict[str, float],
        validator_private_key: str,
    ):
        """
        Submit consensus results with round tracking using updateMetagraphWithConsensusRound()
        Includes rewards distribution and consensus round storage
        """
        print(
            f"🔗 Submitting consensus round {round_id} with {len(final_scores)} scores..."
        )

        # Prepare batch data
        addresses = []
        performances = []
        trust_scores = []
        reward_amounts = []

        uid_to_address_map = {
            "subnet1_miner_001": "0xd89fBAbb72190ed22F012ADFC693ad974bAD3005",
            "subnet1_miner_002": "0x16102CA8BEF74fb6214AF352989b664BF0e50498",
            "7375626e6574315f6d696e65725f303031": "0xd89fBAbb72190ed22F012ADFC693ad974bAD3005",
            "7375626e6574315f6d696e65725f303032": "0x16102CA8BEF74fb6214AF352989b664BF0e50498",
        }

        for miner_uid, consensus_score in final_scores.items():
            miner_address = uid_to_address_map.get(miner_uid)
            if not miner_address:
                continue

            # Scale score and reward
            score_scaled = max(0, min(1_000_000, int(consensus_score * 1_000_000)))
            reward_amount = int(rewards.get(miner_uid, 0) * 1e18)  # Convert to wei

            addresses.append(miner_address)
            performances.append(score_scaled)
            trust_scores.append(score_scaled)
            reward_amounts.append(reward_amount)

        if not addresses:
            print("❌ No valid miners to update")
            return None

        try:
            validator_account = self.w3.eth.account.from_key(validator_private_key)

            transaction = self.contract.functions.updateMetagraphWithConsensusRound(
                round_id, addresses, performances, trust_scores, reward_amounts
            ).build_transaction(
                {
                    "from": validator_account.address,
                    "gas": 300000
                    + (75000 * len(addresses)),  # More gas for advanced function
                    "gasPrice": self.w3.to_wei(20, "gwei"),
                    "nonce": self.w3.eth.get_transaction_count(
                        validator_account.address
                    ),
                }
            )

            signed_txn = validator_account.sign_transaction(transaction)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            tx_hash_hex = tx_hash.hex()

            print(f"✅ Consensus round {round_id} submitted: {tx_hash_hex}")

            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
            print(f"🎉 Consensus round confirmed! Gas used: {receipt['gasUsed']:,}")

            return tx_hash_hex

        except Exception as e:
            print(f"❌ Consensus round submission failed: {e}")
            return None


def example_usage():
    """Example of how to use the new batch functions"""

    # Configuration
    CONTRACT_ADDRESS = (
        "0xAA6B8200495F7741B0B151B486aEB895fEE8c272"  # ModernTensor contract
    )
    RPC_URL = "https://rpc.test2.btcs.network"
    VALIDATOR_PRIVATE_KEY = "your_validator_private_key_here"

    # Example consensus scores from P2P consensus
    final_scores = {
        "subnet1_miner_001": 0.85,  # 85% performance
        "subnet1_miner_002": 0.72,  # 72% performance
    }

    # Example rewards distribution
    rewards = {
        "subnet1_miner_001": 0.001,  # 0.001 CORE
        "subnet1_miner_002": 0.0008,  # 0.0008 CORE
    }

    # Create updater
    updater = MetagraphUpdater(CONTRACT_ADDRESS, RPC_URL)

    print("=" * 60)
    print("🎯 EXAMPLE 1: Basic Batch Update")
    print("=" * 60)

    # Method 1: Basic batch update
    tx_hash1 = updater.submit_consensus_batch(final_scores, VALIDATOR_PRIVATE_KEY)

    print("\n" + "=" * 60)
    print("🎯 EXAMPLE 2: Advanced Consensus Round")
    print("=" * 60)

    # Method 2: Advanced with consensus round tracking
    round_id = 123
    tx_hash2 = updater.submit_consensus_with_round(
        round_id, final_scores, rewards, VALIDATOR_PRIVATE_KEY
    )

    print(f"\n✅ BATCH SUBMISSION COMPLETE!")
    print(f"Basic batch TX: {tx_hash1}")
    print(f"Consensus round TX: {tx_hash2}")


if __name__ == "__main__":
    example_usage()
