import pytest
from aptos_sdk.account import Account
from aptos_sdk.async_client import RestClient
import sys

@pytest.fixture
def aptos_client():
    """Tạo client kiểm thử cho Aptos."""
    return RestClient("https://fullnode.testnet.aptoslabs.com/v1")

@pytest.fixture
def test_account():
    """Sử dụng tài khoản đã được cấp tiền để kiểm thử."""
    private_key_hex = "0x82a167f420cfd52500bdcf2754ccf68167ee70e9eef9cc4f95d387e42c97cfd7"
    account = Account.load_key(private_key_hex)
    
    print("\n" + "="*50)
    print("THÔNG TIN TÀI KHOẢN KIỂM THỬ")
    print("="*50)
    print(f"Khóa riêng tư: {account.private_key.hex()}")
    print(f"Địa chỉ: {account.address()}")
    print("="*50 + "\n")
    return account

@pytest.mark.asyncio
async def test_account_info(aptos_client, test_account):
    """Kiểm tra thông tin tài khoản."""
    print("\nĐịa chỉ tài khoản:", test_account.address())
    print("Loại địa chỉ tài khoản:", type(test_account.address()))
    print("Chuỗi địa chỉ tài khoản:", str(test_account.address()))
    
    # Lấy resources của tài khoản
    try:
        resources = await aptos_client.account_resources(test_account.address())
        print("\nĐã tìm thấy resources:", len(resources))
        
        for i, resource in enumerate(resources):
            print(f"Resource {i}: {resource['type']}")
            
            if resource["type"] == "0x1::coin::CoinStore<0x1::aptos_coin::AptosCoin>":
                balance = int(resource["data"]["coin"]["value"])
                print(f"\nĐã tìm thấy resource coin với số dư: {balance}")
                print(f"Số dư tính theo APT: {balance / 100000000} APT")
                break
        else:
            print("\nKhông tìm thấy resource coin")
            
    except Exception as e:
        print("\nLỗi khi lấy resources:", e)
        raise e

def main():
    # Sử dụng private key từ test để xác định địa chỉ đúng
    private_key_hex = "0x82a167f420cfd52500bdcf2754ccf68167ee70e9eef9cc4f95d387e42c97cfd7"
    
    # Nếu private_key bắt đầu bằng 0x, cần loại bỏ
    if private_key_hex.startswith("0x"):
        private_key_hex = private_key_hex[2:]
    
    # Tạo tài khoản từ private key
    try:
        account = Account.load_key(private_key_hex)
        
        # Lấy địa chỉ
        address = account.address()
        address_str = str(address)
        
        # In thông tin
        print("\n" + "=" * 50)
        print("THÔNG TIN TÀI KHOẢN TỪ PRIVATE KEY")
        print("=" * 50)
        print(f"Private key: 0x{private_key_hex}")
        print(f"Address (raw): {address}")
        print(f"Address (str): {address_str}")
        
        # In lệnh kiểm tra tài khoản
        print("\n" + "=" * 50)
        print("LỆNH KIỂM TRA TÀI KHOẢN")
        print("=" * 50)
        print(f"curl https://fullnode.testnet.aptoslabs.com/v1/accounts/{address_str}")
        print(f"curl https://fullnode.testnet.aptoslabs.com/v1/accounts/{address_str}/resources")
        print("=" * 50 + "\n")
        
    except Exception as e:
        print(f"Lỗi: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 