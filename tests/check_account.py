import asyncio
from aptos_sdk.account import Account, AccountAddress
from aptos_sdk.async_client import RestClient

async def main():
    # Client kết nối đến Aptos testnet
    client = RestClient("https://fullnode.testnet.aptoslabs.com/v1")
    
    # Thông tin tài khoản cần kiểm tra
    account_address = "0x7b8efb0de5bb99a89a235014eb70fd788f102d29190985ec9f1d8b4ad1b87ff9"
    txn_hash = "0xf8256ec2037813d0367ced2478e8ffc224598bb5ec8ffa7cd2d2696fda5af090"
    
    # Kiểm tra thông tin tài khoản
    print(f"\n===== THÔNG TIN TÀI KHOẢN {account_address} =====")
    try:
        address = AccountAddress.from_str(account_address)
        resources = await client.account_resources(address)
        
        print(f"Số lượng resources: {len(resources)}")
        
        # Kiểm tra có coin không
        for resource in resources:
            print(f"Resource: {resource['type']}")
            if resource["type"] == "0x1::coin::CoinStore<0x1::aptos_coin::AptosCoin>":
                balance = int(resource["data"]["coin"]["value"])
                print(f"Số dư: {balance} octas ({balance/100_000_000} APT)")
                print("Tài khoản CÓ APT!")
                break
        else:
            print("Tài khoản KHÔNG CÓ APT!")
    
    except Exception as e:
        print(f"Lỗi khi kiểm tra tài khoản: {e}")
    
    # Kiểm tra thông tin giao dịch
    print(f"\n===== THÔNG TIN GIAO DỊCH {txn_hash} =====")
    try:
        response = await client.client.get(f"{client.base_url}/transactions/by_hash/{txn_hash}")
        if response.status_code == 200:
            txn_data = response.json()
            print(f"Giao dịch tồn tại!")
            print(f"Loại giao dịch: {txn_data.get('type', 'N/A')}")
            print(f"Trạng thái: {'Thành công' if txn_data.get('success', False) else 'Thất bại'}")
            
            if "sender" in txn_data:
                print(f"Người gửi: {txn_data['sender']}")
            
            if "payload" in txn_data and "function" in txn_data["payload"]:
                print(f"Hàm: {txn_data['payload']['function']}")
                
            # Kiểm tra nếu là giao dịch chuyển tiền
            if ("payload" in txn_data and "function" in txn_data["payload"] and 
                    "0x1::coin::transfer" in txn_data["payload"]["function"]):
                print("Đây là giao dịch chuyển tiền!")
                if "arguments" in txn_data["payload"] and len(txn_data["payload"]["arguments"]) >= 2:
                    print(f"Người nhận: {txn_data['payload']['arguments'][0]}")
                    print(f"Số tiền: {txn_data['payload']['arguments'][1]} octas")
                    
                    # Kiểm tra xem người nhận có phải là tài khoản cần kiểm tra không
                    if account_address.lower() == txn_data['payload']['arguments'][0].lower():
                        print(f">>> GIAO DỊCH NÀY ĐÃ CHUYỂN TIỀN ĐẾN TÀI KHOẢN {account_address}")
                    else:
                        print(f">>> GIAO DỊCH NÀY KHÔNG CHUYỂN TIỀN ĐẾN TÀI KHOẢN {account_address}")
        else:
            print(f"Không tìm thấy giao dịch, mã lỗi: {response.status_code}")
    except Exception as e:
        print(f"Lỗi khi kiểm tra giao dịch: {e}")

# Chạy hàm main bất đồng bộ
if __name__ == "__main__":
    asyncio.run(main()) 