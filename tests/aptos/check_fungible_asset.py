import asyncio
import json
from aptos_sdk.account import Account, AccountAddress
from aptos_sdk.async_client import RestClient

async def main():
    # Client kết nối đến Aptos testnet
    client = RestClient("https://fullnode.testnet.aptoslabs.com/v1")
    
    # Tài khoản kiểm tra
    private_key_hex = "0x82a167f420cfd52500bdcf2754ccf68167ee70e9eef9cc4f95d387e42c97cfd7"
    if private_key_hex.startswith("0x"):
        private_key_hex = private_key_hex[2:]
    account = Account.load_key(private_key_hex)
    address = account.address()
    
    print(f"\n===== THÔNG TIN TÀI KHOẢN {address} =====")
    print(f"Private key: 0x{private_key_hex}")
    
    # 1. Kiểm tra resource account
    try:
        resources = await client.account_resources(address)
        print(f"\nSố lượng resources: {len(resources)}")
        
        for resource in resources:
            print(f"Resource: {resource['type']}")
    except Exception as e:
        print(f"Lỗi khi lấy resources: {e}")
    
    # 2. Kiểm tra fungible store có thể được liên kết với account
    try:
        print("\n===== KIỂM TRA FUNGIBLE ASSET STORE =====")
        
        # Lấy danh sách tất cả đối tượng liên kết với address này (owner là address)
        response = await client.client.get(f"{client.base_url}/accounts/{address}/resources?limit=9999")
        
        if response.status_code == 200:
            resources = response.json()
            
            # Tìm ObjectCore cho FungibleStore
            fungible_stores = []
            for resource in resources:
                if "0x1::object::ObjectCore" in resource["type"]:
                    fungible_stores.append(resource["data"]["owner"])
                    print(f"Tìm thấy Object có owner: {resource['data']['owner']}")
            
            # Nếu không tìm thấy, thử cách khác
            if not fungible_stores:
                print("Không tìm thấy Object liên kết trực tiếp")
                
                # Kiểm tra transaction để tìm store đã được tạo 
                txn_hash = "0xf8256ec2037813d0367ced2478e8ffc224598bb5ec8ffa7cd2d2696fda5af090"
                response = await client.client.get(f"{client.base_url}/transactions/by_hash/{txn_hash}")
                
                if response.status_code == 200:
                    txn_data = response.json()
                    print(f"\nKiểm tra thông tin từ giao dịch: {txn_hash}")
                    
                    # Tìm thông tin về FungibleStore trong thay đổi từ giao dịch
                    store_address = None
                    for change in txn_data.get("changes", []):
                        if "0x1::fungible_asset::FungibleStore" in change.get("data", {}).get("type", ""):
                            store_address = change.get("address")
                            balance = change.get("data", {}).get("data", {}).get("balance", "0")
                            print(f"Tìm thấy FungibleStore tại địa chỉ: {store_address}")
                            print(f"Số dư: {balance} octas ({int(balance)/100000000} APT)")
                            break
                    
                    if not store_address:
                        # Kiểm tra trong các sự kiện
                        for event in txn_data.get("events", []):
                            if "0x1::fungible_asset::Deposit" in event.get("type", ""):
                                store_address = event.get("data", {}).get("store")
                                amount = event.get("data", {}).get("amount", "0")
                                print(f"Tìm thấy sự kiện nạp FungibleStore tại: {store_address}")
                                print(f"Số tiền: {amount} octas ({int(amount)/100000000} APT)")
                                break
                    
                    # Nếu tìm thấy, kiểm tra số dư của store
                    if store_address:
                        response = await client.client.get(f"{client.base_url}/accounts/{store_address}/resources")
                        if response.status_code == 200:
                            store_resources = response.json()
                            for resource in store_resources:
                                if "0x1::fungible_asset::FungibleStore" in resource["type"]:
                                    balance = resource["data"]["balance"]
                                    print(f"Số dư trong store: {balance} octas ({int(balance)/100000000} APT)")
                                    break
        else:
            print(f"Lỗi khi lấy resources, mã lỗi: {response.status_code}")
    
    except Exception as e:
        print(f"Lỗi khi kiểm tra FungibleStore: {e}")
    
    # 3. Kiểm tra bằng cách gọi view function của primary_fungible_store
    try:
        print("\n===== SỬ DỤNG VIEW FUNCTION KIỂM TRA SỐ DƯ =====")
        # Cố gắng kiểm tra số dư sử dụng view function
        payload = {
            "function": "0x1::coin::balance",
            "type_arguments": ["0x1::aptos_coin::AptosCoin"],
            "arguments": [str(address)]
        }
        
        response = await client.client.post(f"{client.base_url}/view", json=payload)
        if response.status_code == 200:
            result = response.json()
            print(f"Số dư coin: {result} octas ({int(result)/100000000} APT)")
        else:
            print(f"Lỗi khi sử dụng view function coin::balance, mã lỗi: {response.status_code}")
            
        # Thử với primary_fungible_store
        metadata = "0xa"  # Metadata của APT
        payload = {
            "function": "0x1::primary_fungible_store::balance",
            "type_arguments": ["0x1::aptos_coin::AptosCoin"],
            "arguments": [str(address)]
        }
        
        response = await client.client.post(f"{client.base_url}/view", json=payload)
        if response.status_code == 200:
            result = response.json()
            print(f"Số dư primary_fungible_store: {result} octas ({int(result)/100000000} APT)")
        else:
            print(f"Lỗi khi sử dụng view function primary_fungible_store::balance: {response.text}")
            
        # Thử kiểm tra với hàm fungible_asset::balance
        payload = {
            "function": "0x1::fungible_asset::balance",
            "type_arguments": [],
            "arguments": ["0x441e7a4984f621e9ece9747ac2ffe530e135a9ac6f60886ddb452dae5632ee27"]
        }
        
        response = await client.client.post(f"{client.base_url}/view", json=payload)
        if response.status_code == 200:
            result = response.json()
            print(f"Số dư fungible_asset::balance: {result} octas ({int(result)/100000000} APT)")
        else:
            print(f"Lỗi khi sử dụng view function fungible_asset::balance: {response.text}")
    
    except Exception as e:
        print(f"Lỗi khi kiểm tra số dư với view function: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 