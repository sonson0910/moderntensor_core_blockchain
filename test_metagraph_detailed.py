#!/usr/bin/env python3

import os
import sys
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
import json
from dotenv import load_dotenv

# Add mt_core to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mt_core'))

load_dotenv()

def test_detailed_metagraph():
    print("🔍 DETAILED METAGRAPH TEST WITH DATA PARSING")
    print("=" * 60)
    
    # Connect to Core Testnet
    rpc_url = "https://rpc.test.btcs.network"
    web3 = Web3(Web3.HTTPProvider(rpc_url))
    web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    # Contract details
    contract_address = os.getenv('CORE_CONTRACT_ADDRESS')
    
    # Load contract ABI
    abi_path = "mt_core/smartcontract/artifacts/contracts/ModernTensorAI_v2_Bittensor.sol/ModernTensorAI_v2_Bittensor.json"
    with open(abi_path, 'r') as f:
        contract_data = json.load(f)
        contract_abi = contract_data['abi']
    
    # Create contract instance
    contract = web3.eth.contract(address=contract_address, abi=contract_abi)
    
    print(f"📊 DETAILED MINER AND VALIDATOR DATA...")
    print("-" * 50)
    
    # Get miners
    miners = contract.functions.getAllMiners().call()
    print(f"\n👥 MINERS ({len(miners)}):")
    
    for i, miner_addr in enumerate(miners):
        print(f"\n  Miner {i+1}: {miner_addr}")
        try:
            miner_info = contract.functions.getMinerInfo(miner_addr).call()
            
            # Parse MinerData struct
            uid = miner_info[0].hex()
            core_stake = web3.from_wei(miner_info[1], 'ether')
            btc_stake = web3.from_wei(miner_info[2], 'ether')  
            api_endpoint = miner_info[3]
            is_active = miner_info[4]
            trust_score = miner_info[5]
            performance_score = miner_info[6]
            last_activity = miner_info[7]
            
            print(f"    UID: {uid}")
            print(f"    CORE Stake: {core_stake} CORE")
            print(f"    BTC Stake: {btc_stake} BTC")
            print(f"    API Endpoint: {api_endpoint}")
            print(f"    Active: {is_active}")
            print(f"    Trust Score: {trust_score}")
            print(f"    Performance: {performance_score}")
            print(f"    Last Activity: {last_activity}")
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
    
    # Get validators
    validators = contract.functions.getAllValidators().call()
    print(f"\n🛡️ VALIDATORS ({len(validators)}):")
    
    for i, validator_addr in enumerate(validators):
        print(f"\n  Validator {i+1}: {validator_addr}")
        try:
            validator_info = contract.functions.getValidatorInfo(validator_addr).call()
            
            # Parse ValidatorData struct
            uid = validator_info[0].hex()
            core_stake = web3.from_wei(validator_info[1], 'ether')
            btc_stake = web3.from_wei(validator_info[2], 'ether')
            api_endpoint = validator_info[3]
            is_active = validator_info[4]
            consensus_weight = validator_info[5]
            last_consensus = validator_info[6]
            
            print(f"    UID: {uid}")
            print(f"    CORE Stake: {core_stake} CORE")
            print(f"    BTC Stake: {btc_stake} BTC")
            print(f"    API Endpoint: {api_endpoint}")
            print(f"    Active: {is_active}")
            print(f"    Consensus Weight: {consensus_weight}")
            print(f"    Last Consensus: {last_consensus}")
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
    
    # Test creating metagraph-compatible data
    print(f"\n�� CREATING METAGRAPH DATA FORMAT...")
    print("-" * 40)
    
    metagraph_data = {
        "miners": [],
        "validators": [],
        "network_stats": {
            "total_miners": len(miners),
            "total_validators": len(validators),
            "contract_address": contract_address
        }
    }
    
    # Convert to metagraph format
    for miner_addr in miners:
        try:
            miner_info = contract.functions.getMinerInfo(miner_addr).call()
            miner_data = {
                "address": miner_addr,
                "uid": miner_info[0].hex(),
                "core_stake": float(web3.from_wei(miner_info[1], 'ether')),
                "btc_stake": float(web3.from_wei(miner_info[2], 'ether')),
                "api_endpoint": miner_info[3],
                "active": bool(miner_info[4]),
                "trust_score": int(miner_info[5]),
                "performance_score": int(miner_info[6]),
                "last_activity": int(miner_info[7])
            }
            metagraph_data["miners"].append(miner_data)
        except:
            pass
    
    for validator_addr in validators:
        try:
            validator_info = contract.functions.getValidatorInfo(validator_addr).call()
            validator_data = {
                "address": validator_addr,
                "uid": validator_info[0].hex(),
                "core_stake": float(web3.from_wei(validator_info[1], 'ether')),
                "btc_stake": float(web3.from_wei(validator_info[2], 'ether')),
                "api_endpoint": validator_info[3],
                "active": bool(validator_info[4]),
                "consensus_weight": int(validator_info[5]),
                "last_consensus": int(validator_info[6])
            }
            metagraph_data["validators"].append(validator_data)
        except:
            pass
    
    print(f"✅ Metagraph data created successfully!")
    print(f"📊 Network Stats:")
    print(f"   - Miners: {metagraph_data['network_stats']['total_miners']}")
    print(f"   - Validators: {metagraph_data['network_stats']['total_validators']}")
    print(f"   - Active Miners: {sum(1 for m in metagraph_data['miners'] if m['active'])}")
    print(f"   - Active Validators: {sum(1 for v in metagraph_data['validators'] if v['active'])}")
    
    # Save to file for metagraph system
    with open('metagraph_snapshot.json', 'w') as f:
        json.dump(metagraph_data, f, indent=2)
    print(f"\n�� Metagraph data saved to metagraph_snapshot.json")

if __name__ == "__main__":
    test_detailed_metagraph()
