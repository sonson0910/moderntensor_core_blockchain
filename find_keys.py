from eth_account import Account

# Registered addresses on blockchain  
REGISTERED = {
    "miner_1": "0x1Be31A94361a391bBaFB2a4CCd704F57dc04d4bb",
    "miner_2": "0xf42138298fa1Fc8514BC17D59eBB451AceF3cDBa", 
    "validator_1": "0x580A1998965dD6a0128d5cBB39e58c2960679f38",
    "validator_2": "0x581e88B38eF1Fd056E811b8BE7Ad7F012eFBB7db"
}

# Found private keys
KEYS = [
    "e9c03148c011d553d43b485d73b1407d24f1498a664f782dc0204e524855be4e",
    "3ace434e2cd05cd0e614eb5d423cf04e4b925c17db9869e9c598851f88f52840", 
    "3ac6e82cf34e51d376395af0338d0b1162c1d39b9d34614ed40186fd2367b33d",
    "df51093c674459eb0a5cc8a273418061fe4d7ca189bd84b74f478271714e0920",
    "7e2c40ab431ddf141322ed93531e8e4b2cda01bb25aa947d297b680b635b715c",
    "a07b6e0db803f9a21ffd1001c76b0aa0b313aaba8faab8c771af47301c4452b4",
]

print("🔍 FINDING MATCHING KEYS...")
print("=" * 50)

matches = {}
for name, addr in REGISTERED.items():
    print(f"\n🎯 {name}: {addr}")
    found = False
    for i, key in enumerate(KEYS):
        try:
            full_key = '0x' + key if not key.startswith('0x') else key
            account = Account.from_key(full_key)
            if account.address.lower() == addr.lower():
                print(f"   ✅ MATCH! Key {i+1}: {key}")
                matches[name] = key
                found = True
                break
            else:
                print(f"   ❌ Key {i+1}: {account.address}")
        except Exception as e:
            print(f"   💥 Key {i+1}: ERROR - {e}")
    if not found:
        print(f"   😞 NO MATCH FOUND")

print("\n" + "=" * 50)        
print("🎯 FINAL RESULTS:")
print("=" * 50)
for name, key in matches.items():
    print(f"✅ {name}: {key}")

if not matches:
    print("❌ NO MATCHING KEYS FOUND!")
    print("   Keys might be generated elsewhere or lost.")
