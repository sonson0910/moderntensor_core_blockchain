#!/usr/bin/env python3
import sys
from pathlib import Path

# Add moderntensor path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "moderntensor_aptos"))

from mt_core.metagraph.core_metagraph_adapter import CoreMetagraphClient

def get_all_registered():
    """Get all registered entities with full details"""
    print("🌐 GETTING ALL REGISTERED ENTITIES FROM BLOCKCHAIN")
    print("=" * 70)
    
    try:
        client = CoreMetagraphClient()
        
        # Get all addresses
        miners = client.get_all_miners()
        validators = client.get_all_validators()
        
        print(f"📊 REGISTERED ENTITIES:")
        print(f"   Miners: {len(miners)}")
        print(f"   Validators: {len(validators)}")
        
        print(f"\n🔧 REGISTERED MINERS:")
        print("=" * 50)
        for i, miner_addr in enumerate(miners, 1):
            print(f"\n📋 MINER {i}:")
            print(f"   Address: {miner_addr}")
            
            try:
                info = client.get_miner_info(miner_addr)
                print(f"   UID: {info.get('uid', 'N/A')}")
                print(f"   Endpoint: {info.get('api_endpoint', 'N/A')}")
                print(f"   Stake: {info.get('stake', 0)} CORE")
                print(f"   Status: {info.get('status', 'Unknown')}")
                print(f"   Active: {info.get('active', False)}")
                print(f"   Trust Score: {info.get('scaled_trust_score', 0)}")
                print(f"   Performance: {info.get('scaled_last_performance', 0)}")
                print(f"   Registration Time: {info.get('registration_time', 0)}")
            except Exception as e:
                print(f"   ❌ Error getting details: {e}")
        
        print(f"\n🛡️ REGISTERED VALIDATORS:")
        print("=" * 50)
        for i, validator_addr in enumerate(validators, 1):
            print(f"\n📋 VALIDATOR {i}:")
            print(f"   Address: {validator_addr}")
            
            try:
                info = client.get_validator_info(validator_addr)
                print(f"   UID: {info.get('uid', 'N/A')}")
                print(f"   Endpoint: {info.get('api_endpoint', 'N/A')}")
                print(f"   Stake: {info.get('stake', 0)} CORE")
                print(f"   Status: {info.get('status', 'Unknown')}")
                print(f"   Active: {info.get('active', False)}")
                print(f"   Trust Score: {info.get('scaled_trust_score', 0)}")
                print(f"   Performance: {info.get('scaled_last_performance', 0)}")
                print(f"   Registration Time: {info.get('registration_time', 0)}")
            except Exception as e:
                print(f"   ❌ Error getting details: {e}")
        
        # Check specific address mentioned by user
        target_address = "0xd89fBAbb72190ed22F012ADFC693ad974bAD3005"
        print(f"\n🎯 CHECKING SPECIFIC ADDRESS: {target_address}")
        print("=" * 70)
        
        if target_address in miners:
            print(f"✅ FOUND in MINERS list")
            try:
                info = client.get_miner_info(target_address)
                print(f"   Details: {info}")
            except Exception as e:
                print(f"   Error getting details: {e}")
        elif target_address in validators:
            print(f"✅ FOUND in VALIDATORS list")
            try:
                info = client.get_validator_info(target_address)
                print(f"   Details: {info}")
            except Exception as e:
                print(f"   Error getting details: {e}")
        else:
            print(f"❌ NOT FOUND in either miners or validators")
        
        # Case-insensitive check
        print(f"\n🔍 CASE-INSENSITIVE CHECK:")
        target_lower = target_address.lower()
        for addr in miners:
            if addr.lower() == target_lower:
                print(f"✅ FOUND MINER (case-insensitive): {addr}")
                break
        for addr in validators:
            if addr.lower() == target_lower:
                print(f"✅ FOUND VALIDATOR (case-insensitive): {addr}")
                break
        
        return {
            'miners': miners,
            'validators': validators
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    get_all_registered()
