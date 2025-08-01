#!/usr/bin/env python3
import sys
from pathlib import Path

# Add moderntensor path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "moderntensor_aptos"))

from mt_core.metagraph.core_metagraph_adapter import CoreMetagraphClient

def check_old_contract():
    print("🔍 CHECKING OLD CONTRACT FOR ENTITIES")
    print("=" * 60)
    
    # Contract cũ từ backup
    old_contract = "0x3dACb0Ac7A913Fa94f383f7d6CF0a7BC2b5498DD"
    new_contract = "0x6C1f1e9B1196AA11c0A0C799e62Ab2248695276d"
    
    print(f"🏗️ Contract cũ: {old_contract}")
    print(f"🏗️ Contract mới: {new_contract}")
    
    # Entities từ files
    entities_addresses = [
        "0xd89fBAbb72190ed22F012ADFC693ad974bAD3005",  # miner_1
        "0x16102CA8BEF74fb6214AF352989b664BF0e50498",  # miner_2
        "0x25F3D6316017FDF7A4f4e54003b29212a198768f",  # validator_1
        "0x352516F491DFB3E6a55bFa9c58C551Ef10267dbB",  # validator_2
    ]
    
    print(f"\n🔍 KIỂM TRA TRÊN CONTRACT CŨ:")
    try:
        # Tạo client với contract cũ
        client = CoreMetagraphClient()
        client.contract_address = old_contract
        client.contract = client.web3.eth.contract(
            address=old_contract, 
            abi=client.contract.abi
        )
        
        miners = client.get_all_miners()
        validators = client.get_all_validators()
        
        print(f"   📊 Miners: {len(miners)}")
        print(f"   📊 Validators: {len(validators)}")
        
        found_count = 0
        for addr in entities_addresses:
            if addr in miners:
                print(f"   ✅ FOUND MINER: {addr}")
                found_count += 1
            elif addr in validators:
                print(f"   ✅ FOUND VALIDATOR: {addr}")
                found_count += 1
            else:
                print(f"   ❌ NOT FOUND: {addr}")
        
        print(f"\n📊 SUMMARY:")
        print(f"   Found {found_count}/{len(entities_addresses)} entities on old contract")
        
        if found_count > 0:
            print(f"\n💡 SOLUTION:")
            print(f"   Khôi phục .env backup để dùng contract cũ:")
            print(f"   cp .env.backup_1753868733 .env")
        
    except Exception as e:
        print(f"❌ Error checking old contract: {e}")

if __name__ == "__main__":
    check_old_contract()
