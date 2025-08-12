from eth_account.entities folder
ENTITIES  =  {
    "miner_1": {
        "address": "0xd89fBAbb72190ed22F012ADFC693ad974bAD3005",
        "private_key": "e9c03148c011d553d43b485d73b1407d24f1498a664f782dc0204e524855be4e"
    },
    "miner_2": {
        "address": "0x16102CA8BEF74fb6214AF352989b664BF0e50498",
        "private_key": "3ace434e2cd05cd0e614eb5d423cf04e4b925c17db9869e9c598851f88f52840"
    },
    "validator_1": {
        "address": "0x25F3D6316017FDF7A4f4e54003b29212a198768f",
        "private_key": "3ac6e82cf34e51d376395af0338d0b1162c1d39b9d34614ed40186fd2367b33d"
    },
    "validator_2": {
        "address": "0x352516F491DFB3E6a55bFa9c58C551Ef10267dbB",
        "private_key": "df51093c674459eb0a5cc8a273418061fe4d7ca189bd84b74f478271714e0920"
    }
}

# Registered on blockchain
REGISTERED  =  {
    "miner_1": "0x1Be31A94361a391bBaFB2a4CCd704F57dc04d4bb",
    "miner_2": "0xf42138298fa1Fc8514BC17D59eBB451AceF3cDBa", 
    "validator_1": "0x580A1998965dD6a0128d5cBB39e58c2960679f38",
    "validator_2": "0x581e88B38eF1Fd056E811b8BE7Ad7F012eFBB7db"
}

print("🔍 CHECKING ENTITIES KEYS vs BLOCKCHAIN")
print(" = " * 60)

print("\n📋 ENTITIES FROM FILES:")
for name, data in ENTITIES.items(): Account:

# Keys.items():
    print(f"🔧 {name}:")
    print(f"   Address: {data['address']}")
    print(f"   Key: {data['private_key'][:16]}...")
    
    # Verify key matches address
    try:
        account  =  Account.from_key('0x' + data['private_key'])
        if account.address.lower() == data['address'].lower():
            print(f"   ✅ Key matches address")
        else:
            print(f"   ❌ Key MISMATCH! Generated: {account.address}")
    except Exception as e:
        print(f"   💥 Error: {e}")

print("\n📋 REGISTERED ON BLOCKCHAIN:")
for name, addr in REGISTERED.items():
    print(f"🌐 {name}: {addr}")

print("\n🔍 COMPARISON:")
print("-" * 40)
for name in ENTITIES.keys():
    entity_addr  =  ENTITIES[name]['address'].lower()
    registered_addr  =  REGISTERED[name].lower()
    
    if entity_addr == registered_addr:
        print(f"✅ {name}: ALREADY REGISTERED")
    else:
        print(f"❌ {name}: NOT REGISTERED")
        print(f"   Entity:     {ENTITIES[name]['address']}")
        print(f"   Registered: {REGISTERED[name]}")

print("\n🎯 SUMMARY:")
matches  =  sum(1 for name in ENTITIES.keys() :
              if ENTITIES[name]['address'].lower() == REGISTERED[name].lower()):
print(f"   {matches}/{len(ENTITIES)} entities already registered")

if matches == 0:
    print("\n🚀 NEXT STEP: Register all entities from files")
    print("   Run: python register_entities_from_files.py")
elif matches < len(ENTITIES):
    print(f"\n⚠️ NEXT STEP: Register {len(ENTITIES)-matches} missing entities")
    print("   Run: python register_entities_from_files.py")
else:
    print("\n✅ ALL ENTITIES ALREADY REGISTERED!")
