import pytest
import os
import json
from aptos_sdk.account import Account, AccountAddress
from aptos_sdk.async_client import RestClient
from typing import Optional
from mnemonic import Mnemonic
import hmac
import hashlib
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os
import getpass
from pathlib import Path

# Định nghĩa đường dẫn cho thư mục lưu trữ key
DEFAULT_KEY_DIR = os.path.join(os.path.expanduser("~"), ".aptos", "keys")

def derive_encryption_key(password: str, salt: bytes) -> bytes:
    """
    Tạo khóa mã hóa từ mật khẩu và salt sử dụng PBKDF2
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def encrypt_mnemonic(mnemonic: str, password: str) -> tuple[bytes, bytes]:
    """
    Mã hóa mnemonic bằng mật khẩu. Trả về cặp (salt, encrypted_data)
    """
    salt = os.urandom(16)
    key = derive_encryption_key(password, salt)
    cipher_suite = Fernet(key)
    encrypted_data = cipher_suite.encrypt(mnemonic.encode('utf-8'))
    return salt, encrypted_data

def decrypt_mnemonic(encrypted_data: bytes, password: str, salt: bytes) -> str:
    """
    Giải mã mnemonic từ dữ liệu đã mã hóa và mật khẩu
    """
    key = derive_encryption_key(password, salt)
    cipher_suite = Fernet(key)
    decrypted_data = cipher_suite.decrypt(encrypted_data)
    return decrypted_data.decode('utf-8')

def save_encrypted_wallet(name: str, salt: bytes, encrypted_data: bytes, directory: str = DEFAULT_KEY_DIR):
    """
    Lưu dữ liệu đã mã hóa vào thư mục chỉ định
    """
    wallet_dir = os.path.join(directory, name)
    os.makedirs(wallet_dir, exist_ok=True)
    
    # Lưu salt
    with open(os.path.join(wallet_dir, "salt.bin"), "wb") as f:
        f.write(salt)
    
    # Lưu mnemonic đã mã hóa
    with open(os.path.join(wallet_dir, "mnemonic.enc"), "wb") as f:
        f.write(encrypted_data)
    
    # Tạo file hotkeys.json trống
    with open(os.path.join(wallet_dir, "hotkeys.json"), "w") as f:
        json.dump({"hotkeys": {}}, f, indent=2)

def load_encrypted_wallet(name: str, password: str, directory: str = DEFAULT_KEY_DIR) -> str:
    """
    Đọc và giải mã mnemonic từ thư mục đã lưu
    """
    wallet_dir = os.path.join(directory, name)
    
    # Đọc salt
    with open(os.path.join(wallet_dir, "salt.bin"), "rb") as f:
        salt = f.read()
    
    # Đọc dữ liệu đã mã hóa
    with open(os.path.join(wallet_dir, "mnemonic.enc"), "rb") as f:
        encrypted_data = f.read()
    
    # Giải mã
    return decrypt_mnemonic(encrypted_data, password, salt)

def derive_account_from_mnemonic(mnemonic: str, purpose: int = 44, coin_type: int = 637, 
                                account: int = 0, change: int = 0, address_index: int = 0) -> Account:
    """
    Tạo tài khoản Aptos từ mnemonic theo đường dẫn BIP44
    m/purpose'/coin_type'/account'/change/address_index
    """
    # Convert mnemonic to seed
    mnemo = Mnemonic("english")
    seed = mnemo.to_seed(mnemonic)
    
    # Build path with hardened indexes as needed
    path_parts = []
    path_parts.append(str(purpose) + "'")  # Purpose: hardened
    path_parts.append(str(coin_type) + "'")  # Coin Type: hardened
    path_parts.append(str(account) + "'")  # Account: hardened
    path_parts.append(str(change) + "'")  # Change: hardened
    path_parts.append(str(address_index) + "'")  # Address Index: hardened
    
    path = "m/" + "/".join(path_parts)
    
    # Derive key
    key = b"ed25519 seed"
    for part in path.split('/')[1:]:
        # Handle hardened derivation
        if part.endswith("'"):
            part = int(part[:-1]) + 0x80000000  # Hardened
        else:
            part = int(part)
            
        # Convert part to bytes
        part_bytes = part.to_bytes(4, byteorder='big')
        
        # HMAC-SHA512 derivation
        if part >= 0x80000000:  # Hardened
            data = b'\x00' + seed[:32] + part_bytes
        else:
            data = seed[32:] + part_bytes
            
        # Update seed for next derivation
        seed = hmac.new(key, data, hashlib.sha512).digest()
        key = seed[:32]  # Use first 32 bytes as key for next iteration
    
    # Use first 32 bytes as private key
    private_key = seed[:32]
    
    # Create Aptos account from private key
    return Account.load_key(private_key.hex())

def save_hotkey(coldkey_name: str, hotkey_name: str, account: Account, 
               mnemonic: str, derivation_path: str, directory: str = DEFAULT_KEY_DIR):
    """
    Lưu thông tin hotkey vào file hotkeys.json của coldkey
    """
    wallet_dir = os.path.join(directory, coldkey_name)
    hotkeys_path = os.path.join(wallet_dir, "hotkeys.json")
    
    # Đọc file hotkeys.json hiện có
    with open(hotkeys_path, "r") as f:
        hotkeys_data = json.load(f)
    
    # Chuẩn bị dữ liệu hotkey
    address = str(account.address())
    if not address.startswith("0x"):
        address = f"0x{address}"
    
    # Thêm hotkey mới
    hotkeys_data["hotkeys"][hotkey_name] = {
        "address": address,
        "derivation_path": derivation_path,
        "private_key": account.private_key.hex(),
    }
    
    # Ghi lại file
    with open(hotkeys_path, "w") as f:
        json.dump(hotkeys_data, f, indent=2)
    
    return address

@pytest.mark.asyncio
async def test_create_and_use_hd_wallet():
    """Test tạo HD Wallet và sử dụng cho coldkey và nhiều hotkey."""
    # Tạo thư mục tạm thời để lưu key
    import tempfile
    test_dir = tempfile.mkdtemp()
    
    try:
        # 1. Tạo mnemonic mới
        mnemo = Mnemonic("english")
        mnemonic = mnemo.generate(strength=256)  # 24 words
        print(f"\nMnemonic mới tạo: {mnemonic}")
        
        # 2. Mã hóa và lưu vào coldkey
        password = "test_password"  # Trong thực tế, nên dùng getpass để nhập mật khẩu an toàn
        salt, encrypted_data = encrypt_mnemonic(mnemonic, password)
        coldkey_name = "test_coldkey"
        save_encrypted_wallet(coldkey_name, salt, encrypted_data, test_dir)
        print(f"\nĐã lưu coldkey '{coldkey_name}' vào {test_dir}")
        
        # 3. Tạo coldkey account từ mnemonic (index 0)
        coldkey_account = derive_account_from_mnemonic(mnemonic, account=0)
        coldkey_address = str(coldkey_account.address())
        if not coldkey_address.startswith("0x"):
            coldkey_address = f"0x{coldkey_address}"
        print(f"\nCold key address: {coldkey_address}")
        
        # 4. Tạo các hotkey account từ cùng mnemonic (các index khác nhau)
        hotkeys = []
        for i in range(3):  # Tạo 3 hotkey
            # Mỗi hotkey sẽ dùng account index khác nhau
            derivation_path = f"m/44'/637'/{i+1}'/0'/0'"
            hotkey_account = derive_account_from_mnemonic(mnemonic, account=i+1)
            hotkey_name = f"hotkey_{i+1}"
            
            # Lưu hotkey vào file hotkeys.json
            address = save_hotkey(
                coldkey_name, 
                hotkey_name, 
                hotkey_account, 
                mnemonic, 
                derivation_path, 
                test_dir
            )
            
            hotkeys.append({"name": hotkey_name, "address": address})
            print(f"Hotkey {i+1} address: {address}")
        
        # 5. Giải mã và kiểm tra lại
        decrypted_mnemonic = load_encrypted_wallet(coldkey_name, password, test_dir)
        assert decrypted_mnemonic == mnemonic
        print("\nGiải mã mnemonic thành công!")
        
        # 6. Tạo lại các account từ mnemonic đã giải mã
        recovered_coldkey = derive_account_from_mnemonic(decrypted_mnemonic, account=0)
        recovered_address = str(recovered_coldkey.address())
        if not recovered_address.startswith("0x"):
            recovered_address = f"0x{recovered_address}"
        
        assert recovered_address == coldkey_address
        print(f"\nKhôi phục coldkey thành công: {recovered_address}")
        
        # 7. Đọc file hotkeys.json và kiểm tra
        hotkeys_path = os.path.join(test_dir, coldkey_name, "hotkeys.json")
        with open(hotkeys_path, "r") as f:
            hotkeys_data = json.load(f)
        
        for hotkey in hotkeys:
            assert hotkey["name"] in hotkeys_data["hotkeys"]
            assert hotkeys_data["hotkeys"][hotkey["name"]]["address"] == hotkey["address"]
        
        print("\nKiểm tra hotkeys thành công!")
        
        # 8. Demo: Lấy account từ path cho trong hotkeys.json
        for hotkey_name, hotkey_info in hotkeys_data["hotkeys"].items():
            # Parse derivation path để lấy account index
            # Ví dụ: m/44'/637'/1'/0'/0' -> account=1
            path_parts = hotkey_info["derivation_path"].split("/")
            account_index = int(path_parts[3].replace("'", ""))
            
            # Tạo lại account từ mnemonic và path
            recreated_account = derive_account_from_mnemonic(mnemonic, account=account_index)
            recreated_address = str(recreated_account.address())
            if not recreated_address.startswith("0x"):
                recreated_address = f"0x{recreated_address}"
            
            assert recreated_address == hotkey_info["address"]
            print(f"Khôi phục {hotkey_name} thành công: {recreated_address}")
    
    finally:
        # Dọn dẹp thư mục tạm thời
        import shutil
        shutil.rmtree(test_dir)
        print(f"\nĐã xóa thư mục tạm thời: {test_dir}")

if __name__ == "__main__":
    # Để có thể chạy trực tiếp file này, không chỉ qua pytest
    import asyncio
    asyncio.run(test_create_and_use_hd_wallet()) 