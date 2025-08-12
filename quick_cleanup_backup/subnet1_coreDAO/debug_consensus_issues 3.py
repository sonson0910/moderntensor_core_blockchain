#!/usr/bin/env python3
"""
Debug consensus issues: timing, metagraph update loops, and transaction verification
"""

import os
import sys
import time
import json
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3

def debug_consensus_issues():
    print("🔍 DEBUGGING CONSENSUS ISSUES")
    print("=" * 50)
    
    # Load environment
    load_dotenv()
    
    # Configuration
    rpc_url = os.getenv("CORE_NODE_URL")
    contract_address = os.getenv("CORE_CONTRACT_ADDRESS")
    
    print(f"🌐 RPC URL: {rpc_url}")
    print(f"📝 Contract: {contract_address}")
    
    # Connect to blockchain
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print("❌ Cannot connect to Core blockchain")
        return
    
    print(f"✅ Connected to Core: {w3.is_connected()}")
    print(f"🔗 Current block: {w3.eth.block_number}")
    
    # Load contract ABI
    try:
        abi_path = Path(__file__).parent.parent / "moderntensor_aptos" / "mt_core" / "smartcontract" / "artifacts" / "contracts" / "ModernTensor.sol" / "ModernTensor.json"
        with open(abi_path, "r") as f:
            contract_abi = json.load(f)["abi"]
        contract = w3.eth.contract(address=contract_address, abi=contract_abi)
        print("✅ Contract ABI loaded")
    except Exception as e:
        print(f"❌ Error loading contract ABI: {e}")
        return
    
    # 1. Check transaction status
    print("\n📋 1. CHECKING TRANSACTION STATUS:")
    tx_hash = "0x25f7d067e25039a14baaf48ed7bee328fa94933fa1a59f26e1b2f4c7a52a6f0b"
    
    try:
        receipt = w3.eth.get_transaction_receipt(tx_hash)
        if receipt:
            print(f"✅ Transaction found:")
            print(f"   📄 Hash: {receipt.transactionHash.hex()}")
            print(f"   📦 Block: {receipt.blockNumber}")
            print(f"   ✅ Status: {'Success' if receipt.status == 1 else 'Failed'}")
            print(f"   🔗 Explorer: https://scan.test.btcs.network/tx/{tx_hash}")
            
            # Check logs
            if receipt.logs:
                print(f"   📋 Logs: {len(receipt.logs)} events")
                for i, log in enumerate(receipt.logs[:3]):  # Show first 3 logs
                    print(f"     {i+1}. Address: {log.address}")
                    print(f"        Topics: {[t.hex() for t in log.topics]}")
        else:
            print(f"❌ Transaction not found: {tx_hash}")
            print(f"   🔍 This might be due to:")
            print(f"      - Transaction not yet mined")
            print(f"      - Wrong network (testnet vs mainnet)")
            print(f"      - Transaction failed and was dropped")
    except Exception as e:
        print(f"❌ Error checking transaction: {e}")
    
    # 2. Check recent transactions from validators
    print("\n📋 2. CHECKING RECENT VALIDATOR TRANSACTIONS:")
    
    validator_addresses = [
        "0x25F3D6316017FDF7A4f4e54003b29212a198768f",
        "0x352516F491DFB3E6a55bFa9c58C551Ef10267dbB", 
        "0x0469C6644c07F6e860Af368Af8104F8D8829a78e"
    ]
    
    for i, address in enumerate(validator_addresses, 1):
        print(f"\n  🛡️ Validator {i}: {address}")
        try:
            # Get transaction count
            nonce = w3.eth.get_transaction_count(address)
            print(f"     📊 Nonce: {nonce}")
            
            # Get recent transactions (last 5 blocks)
            current_block = w3.eth.block_number
            recent_txs = []
            
            for block_num in range(current_block - 5, current_block + 1):
                try:
                    block = w3.eth.get_block(block_num, full_transactions=True)
                    for tx in block.transactions:
                        if tx['from'].lower() == address.lower():
                            recent_txs.append({
                                'hash': tx.hash.hex(),
                                'block': block_num,
                                'to': tx.to.hex() if tx.to else None,
                                'value': w3.from_wei(tx.value, 'ether')
                            })
                except Exception as e:
                    continue
            
            if recent_txs:
                print(f"     📋 Recent transactions: {len(recent_txs)}")
                for tx in recent_txs[-3:]:  # Show last 3
                    print(f"        📄 {tx['hash'][:10]}... (Block {tx['block']})")
                    if tx['to']:
                        print(f"           → {tx['to']}")
            else:
                print(f"     ⚠️ No recent transactions found")
                
        except Exception as e:
            print(f"     ❌ Error: {e}")
    
    # 3. Check contract events
    print("\n📋 3. CHECKING CONTRACT EVENTS:")
    
    try:
        # Get recent events from contract
        current_block = w3.eth.block_number
        from_block = current_block - 10  # Last 10 blocks
        
        # Check for consensus events
        consensus_events = contract.events.ConsensusResultSubmitted.get_logs(
            fromBlock=from_block,
            toBlock=current_block
        )
        
        if consensus_events:
            print(f"✅ Found {len(consensus_events)} consensus events:")
            for event in consensus_events[-3:]:  # Show last 3
                print(f"   📄 Block {event.blockNumber}: {event.transactionHash.hex()}")
                print(f"      Validator: {event.args.validatorAddress}")
                print(f"      Slot: {event.args.slot}")
        else:
            print("⚠️ No consensus events found in recent blocks")
        
        # Check for metagraph update events
        metagraph_events = contract.events.MetagraphUpdated.get_logs(
            fromBlock=from_block,
            toBlock=current_block
        )
        
        if metagraph_events:
            print(f"✅ Found {len(metagraph_events)} metagraph update events:")
            for event in metagraph_events[-3:]:
                print(f"   📄 Block {event.blockNumber}: {event.transactionHash.hex()}")
        else:
            print("⚠️ No metagraph update events found in recent blocks")
            
    except Exception as e:
        print(f"❌ Error checking contract events: {e}")
    
    # 4. Check consensus timing
    print("\n📋 4. CONSENSUS TIMING ANALYSIS:")
    
    try:
        # Get contract state
        network_stats = contract.functions.getNetworkStats().call()
        print(f"📊 Network Stats:")
        print(f"   👥 Miners: {network_stats[0]}")
        print(f"   🛡️ Validators: {network_stats[1]}")
        print(f"   💰 Total Staked: {w3.from_wei(network_stats[2], 'ether')} CORE")
        
        # Check if consensus is active
        try:
            # Try to get consensus state
            consensus_active = contract.functions.isConsensusActive().call()
            print(f"   🔄 Consensus Active: {consensus_active}")
        except:
            print(f"   ⚠️ Cannot check consensus state (function not available)")
            
    except Exception as e:
        print(f"❌ Error checking network stats: {e}")
    
    # 5. Recommendations
    print("\n📋 5. RECOMMENDATIONS:")
    print("🔍 To debug further:")
    print("   1. Check if validators are running on same network")
    print("   2. Verify consensus timing configuration")
    print("   3. Check metagraph update intervals")
    print("   4. Monitor transaction gas and nonce issues")
    print("   5. Verify contract function calls")

if __name__ == "__main__":
    debug_consensus_issues() 