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

def test_metagraph_core():
    print("🔍 TESTING METAGRAPH WITH CORE BLOCKCHAIN")
    print("=" * 60)
    
    # Connect to Core Testnet
    rpc_url = "https://rpc.test.btcs.network"
    web3 = Web3(Web3.HTTPProvider(rpc_url))
    web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    print(f"🔗 Connected to Core Testnet: {web3.is_connected()}")
    
    # Contract details
    contract_address = os.getenv('CORE_CONTRACT_ADDRESS')
    print(f"📋 Contract Address: {contract_address}")
    
    # Load contract ABI
    try:
        abi_path = "mt_core/smartcontract/artifacts/contracts/ModernTensorAI_v2_Bittensor.sol/ModernTensorAI_v2_Bittensor.json"
        with open(abi_path, 'r') as f:
            contract_data = json.load(f)
            contract_abi = contract_data['abi']
    except Exception as e:
        print(f"❌ Error loading contract ABI: {e}")
        return
    
    # Create contract instance
    contract = web3.eth.contract(address=contract_address, abi=contract_abi)
    
    print(f"\n📊 TESTING CONTRACT CALLS...")
    print("-" * 40)
    
    try:
        # Test getAllMiners
        print("🔍 Fetching all miners...")
        miners = contract.functions.getAllMiners().call()
        print(f"   👥 Total Miners: {len(miners)}")
        for i, miner in enumerate(miners):
            print(f"   Miner {i+1}: {miner}")
            
            # Get miner details
            try:
                miner_info = contract.functions.getMinerInfo(miner).call()
                print(f"     UID: {miner_info[0].hex()}")
                print(f"     Stake: {web3.from_wei(miner_info[1], 'ether')} CORE")
                print(f"     Endpoint: {miner_info[3]}")
                print(f"     Active: {miner_info[4]}")
            except Exception as e:
                print(f"     ❌ Error getting miner info: {e}")
        
    except Exception as e:
        print(f"❌ Error fetching miners: {e}")
    
    try:
        # Test getAllValidators  
        print("\n🔍 Fetching all validators...")
        validators = contract.functions.getAllValidators().call()
        print(f"   🛡️ Total Validators: {len(validators)}")
        for i, validator in enumerate(validators):
            print(f"   Validator {i+1}: {validator}")
            
            # Get validator details
            try:
                validator_info = contract.functions.getValidatorInfo(validator).call()
                print(f"     UID: {validator_info[0].hex()}")
                print(f"     Stake: {web3.from_wei(validator_info[1], 'ether')} CORE")
                print(f"     Endpoint: {validator_info[3]}")
                print(f"     Active: {validator_info[4]}")
            except Exception as e:
                print(f"     ❌ Error getting validator info: {e}")
        
    except Exception as e:
        print(f"❌ Error fetching validators: {e}")
    
    try:
        # Test subnet info
        print("\n🔍 Fetching subnet info...")
        subnet_miners = contract.functions.getSubnetMiners(0).call()
        subnet_validators = contract.functions.getSubnetValidators(0).call()
        print(f"   🏗️ Subnet 0 Miners: {len(subnet_miners)}")
        print(f"   🏗️ Subnet 0 Validators: {len(subnet_validators)}")
        
    except Exception as e:
        print(f"❌ Error fetching subnet info: {e}")
    
    print(f"\n✅ METAGRAPH TEST COMPLETE!")

if __name__ == "__main__":
    test_metagraph_core()
