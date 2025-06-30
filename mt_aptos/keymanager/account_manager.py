"""
Account Manager cho ModernTensor trên Aptos - Quản lý các khóa và tài khoản
"""

import os
import json
import binascii
import getpass
from pathlib import Path
from typing import Tuple, Dict, Any, Optional, List, Union
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from mt_aptos.account import Account, AccountAddress
from mt_aptos.account import ed25519
from mt_aptos.bcs import Serializer


class AccountKeyManager:
    """
    Quản lý các tài khoản Aptos cho ModernTensor, cung cấp tính năng:
    - Tạo tài khoản mới
    - Khôi phục từ private key hoặc seed phrase
    - Mã hóa và giải mã private key để lưu trữ an toàn
    - Quản lý thông tin tài khoản
    """

    def __init__(self, base_dir: str = "./wallets"):
        """
        Khởi tạo AccountKeyManager với thư mục cơ sở để lưu trữ ví.
        
        Args:
            base_dir: Đường dẫn thư mục để lưu trữ ví.
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._keys_file = self.base_dir / "accounts.json"
        self._accounts_info = self._load_accounts_info()

    def _load_accounts_info(self) -> Dict[str, Dict]:
        """Tải thông tin tài khoản từ file accounts.json."""
        if self._keys_file.exists():
            try:
                with open(self._keys_file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def _save_accounts_info(self) -> None:
        """Lưu thông tin tài khoản vào file accounts.json."""
        with open(self._keys_file, "w") as f:
            json.dump(self._accounts_info, f, indent=4)

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """
        Tạo key từ password và salt sử dụng PBKDF2.
        
        Args:
            password: Mật khẩu người dùng.
            salt: Salt ngẫu nhiên.
        
        Returns:
            bytes: Key dẫn xuất.
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        return kdf.derive(password.encode())

    def _encrypt_private_key(self, private_key: bytes, password: str) -> Tuple[bytes, bytes, bytes]:
        """
        Mã hóa private key sử dụng AES-GCM.
        
        Args:
            private_key: Private key dạng bytes.
            password: Mật khẩu người dùng.
            
        Returns:
            Tuple[bytes, bytes, bytes]: Ciphertext, salt, và nonce.
        """
        salt = os.urandom(16)
        key = self._derive_key(password, salt)
        
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        
        ciphertext = aesgcm.encrypt(nonce, private_key, None)
        return ciphertext, salt, nonce

    def _decrypt_private_key(self, ciphertext: bytes, salt: bytes, nonce: bytes, password: str) -> bytes:
        """
        Giải mã private key.
        
        Args:
            ciphertext: Ciphertext đã mã hóa.
            salt: Salt đã sử dụng để mã hóa.
            nonce: Nonce đã sử dụng để mã hóa.
            password: Mật khẩu người dùng.
            
        Returns:
            bytes: Private key đã giải mã.
        """
        key = self._derive_key(password, salt)
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, None)

    def create_account(self, name: str, password: Optional[str] = None) -> Account:
        """
        Tạo một tài khoản Aptos mới và lưu trữ nó.
        
        Args:
            name: Tên cho tài khoản mới.
            password: Mật khẩu để mã hóa private key. Nếu không cung cấp, sẽ hỏi người dùng.
            
        Returns:
            Account: Đối tượng Account Aptos đã tạo.
        """
        if name in self._accounts_info:
            raise ValueError(f"Account with name '{name}' already exists.")
        
        # Tạo tài khoản mới
        account = Account.generate()
        
        # Yêu cầu mật khẩu nếu không được cung cấp
        if password is None:
            password = getpass.getpass(f"Enter password to encrypt account '{name}': ")
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                raise ValueError("Passwords do not match.")
        
        # Serialize private_key
        private_key_bytes = account.private_key.key.encode()
        
        # Mã hóa private key
        ciphertext, salt, nonce = self._encrypt_private_key(private_key_bytes, password)
        
        # Lưu thông tin tài khoản
        self._accounts_info[name] = {
            "address": str(account.address()),
            "ciphertext": binascii.hexlify(ciphertext).decode(),
            "salt": binascii.hexlify(salt).decode(),
            "nonce": binascii.hexlify(nonce).decode(),
        }
        
        self._save_accounts_info()
        return account
    
    def load_account(self, name: str, password: Optional[str] = None) -> Account:
        """
        Tải một tài khoản Aptos đã lưu.
        
        Args:
            name: Tên của tài khoản.
            password: Mật khẩu để giải mã private key. Nếu không cung cấp, sẽ hỏi người dùng.
            
        Returns:
            Account: Đối tượng Account Aptos đã tải.
        """
        if name not in self._accounts_info:
            raise ValueError(f"Account with name '{name}' does not exist.")
        
        account_info = self._accounts_info[name]
        
        # Yêu cầu mật khẩu nếu không được cung cấp
        if password is None:
            password = getpass.getpass(f"Enter password to decrypt account '{name}': ")
        
        # Giải mã private key
        ciphertext = binascii.unhexlify(account_info["ciphertext"])
        salt = binascii.unhexlify(account_info["salt"])
        nonce = binascii.unhexlify(account_info["nonce"])
        
        try:
            private_key_bytes = self._decrypt_private_key(ciphertext, salt, nonce, password)
            private_key_hex = binascii.hexlify(private_key_bytes).decode('utf-8')
            private_key = ed25519.PrivateKey.from_hex(private_key_hex)
            
            # Tạo AccountAddress từ chuỗi địa chỉ đã lưu
            account_address = AccountAddress.from_hex(account_info["address"])
            
            # Tạo Account với address và private_key
            return Account(account_address, private_key)
        except Exception as e:
            raise ValueError(f"Failed to decrypt account. Incorrect password? Error: {e}")

    def load_or_create_account(self, name: str, password: Optional[str] = None, auto_password: str = None) -> Account:
        """
        Tải account nếu tồn tại, hoặc tự động tạo mới nếu chưa có.
        
        Args:
            name: Tên của tài khoản.
            password: Mật khẩu để giải mã/mã hóa private key.
            auto_password: Mật khẩu tự động để tạo account mới (không cần hỏi user)
            
        Returns:
            Account: Đối tượng Account Aptos đã tải hoặc tạo mới.
        """
        try:
            # Thử tải account trước
            return self.load_account(name, password)
        except ValueError as e:
            if "does not exist" in str(e):
                print(f"🔧 Account '{name}' not found. Creating new account...")
                
                # Sử dụng auto_password nếu có, nếu không thì hỏi user
                create_password = auto_password if auto_password else password
                
                # Tạo account mới
                account = self.create_account(name, create_password)
                print(f"✅ Created new account '{name}' with address: {account.address()}")
                return account
            else:
                # Lỗi khác (mật khẩu sai, etc.) - re-raise
                raise
    
    def list_accounts(self) -> List[Dict[str, str]]:
        """
        Liệt kê tất cả các tài khoản đã lưu.
        
        Returns:
            List[Dict[str, str]]: Danh sách thông tin tài khoản.
        """
        return [{"name": name, "address": info["address"]} for name, info in self._accounts_info.items()]
    
    def delete_account(self, name: str, password: Optional[str] = None) -> bool:
        """
        Xóa một tài khoản đã lưu.
        
        Args:
            name: Tên của tài khoản cần xóa.
            password: Mật khẩu để xác thực. Nếu không cung cấp, sẽ hỏi người dùng.
            
        Returns:
            bool: True nếu xóa thành công, False nếu không.
        """
        if name not in self._accounts_info:
            return False
        
        # Xác thực mật khẩu trước khi xóa
        if password is None:
            password = getpass.getpass(f"Enter password to verify account '{name}' for deletion: ")
        
        try:
            self.load_account(name, password)  # Kiểm tra xem mật khẩu có đúng không
            del self._accounts_info[name]
            self._save_accounts_info()
            return True
        except ValueError:
            return False
    
    def import_private_key(self, name: str, private_key_hex: str, password: Optional[str] = None) -> Account:
        """
        Nhập một tài khoản từ private key.
        
        Args:
            name: Tên cho tài khoản.
            private_key_hex: Private key dạng hex string.
            password: Mật khẩu để mã hóa private key. Nếu không cung cấp, sẽ hỏi người dùng.
            
        Returns:
            Account: Đối tượng Account Aptos đã nhập.
        """
        if name in self._accounts_info:
            raise ValueError(f"Account with name '{name}' already exists.")
        
        # Yêu cầu mật khẩu nếu không được cung cấp
        if password is None:
            password = getpass.getpass(f"Enter password to encrypt account '{name}': ")
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                raise ValueError("Passwords do not match.")
        
        try:
            # Lấy private key từ hex string
            private_key = ed25519.PrivateKey.from_hex(private_key_hex)
            
            # Tạo địa chỉ tài khoản từ public key
            account_address = AccountAddress.from_key(private_key.public_key())
            
            # Tạo Account với address và private_key
            account = Account(account_address, private_key)
            
            # Serialize private_key cho lưu trữ
            private_key_bytes = binascii.unhexlify(private_key_hex)
            
            # Mã hóa private key
            ciphertext, salt, nonce = self._encrypt_private_key(private_key_bytes, password)
            
            # Lưu thông tin tài khoản
            self._accounts_info[name] = {
                "address": str(account.address()),
                "ciphertext": binascii.hexlify(ciphertext).decode(),
                "salt": binascii.hexlify(salt).decode(),
                "nonce": binascii.hexlify(nonce).decode(),
            }
            
            self._save_accounts_info()
            return account
        except Exception as e:
            raise ValueError(f"Failed to import private key: {e}") 