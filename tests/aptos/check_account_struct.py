from aptos_sdk.account import Account
import sys

def explore_account():
    """Khám phá cấu trúc của đối tượng Account trong SDK Aptos hiện tại."""
    account = Account.generate()
    
    print("\n===== THÔNG TIN ĐỐI TƯỢNG ACCOUNT =====")
    print(f"Kiểu của account: {type(account)}")
    print(f"Các thuộc tính: {dir(account)}")
    
    print("\n----- PRIVATE KEY -----")
    print(f"Kiểu của private_key: {type(account.private_key)}")
    print(f"Các thuộc tính của private_key: {dir(account.private_key)}")
    
    try:
        print(f"private_key.hex(): {account.private_key.hex()}")
    except Exception as e:
        print(f"Lỗi khi gọi private_key.hex(): {e}")
    
    try:
        key_bytes = account.private_key.encode()
        print(f"private_key.encode(): {key_bytes}")
        print(f"Độ dài key_bytes: {len(key_bytes)}")
    except Exception as e:
        print(f"Lỗi khi gọi private_key.encode(): {e}")
    
    print("\n----- PUBLIC KEY -----")
    print(f"Kiểu của public_key(): {type(account.public_key())}")
    print(f"Các thuộc tính của public_key(): {dir(account.public_key())}")
    
    try:
        pub_key_bytes = bytes(account.public_key().key)
        print(f"Độ dài pub_key_bytes: {len(pub_key_bytes)}")
    except Exception as e:
        print(f"Lỗi khi lấy bytes của public_key: {e}")
    
    print("\n----- ADDRESS -----")
    print(f"address(): {account.address()}")
    print(f"str(address()): {str(account.address())}")
    print(f"Kiểu của address(): {type(account.address())}")
    
    print("\n===== PHƯƠNG THỨC LOAD_KEY =====")
    # Kiểm tra phương thức load_key
    try:
        private_key_value = account.private_key.key.encode()
        print(f"private_key.key.encode(): {private_key_value}")
        print(f"Độ dài private_key.key.encode(): {len(private_key_value)}")
        
        # Tạo lại account từ khóa riêng tư
        encoded_key = account.private_key.key.encode()
        new_account = Account.load_key(encoded_key.hex())
        print(f"Địa chỉ từ account gốc: {account.address()}")
        print(f"Địa chỉ từ account mới: {new_account.address()}")
        assert str(account.address()) == str(new_account.address()), "Địa chỉ không khớp!"
    except Exception as e:
        print(f"Lỗi khi thử load_key: {e}")

if __name__ == "__main__":
    explore_account()
    sys.exit(0) 