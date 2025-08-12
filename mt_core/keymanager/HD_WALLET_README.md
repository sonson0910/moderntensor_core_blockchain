# HD Wallet System for ModernTensor Aptos

Hệ thống HD Wallet (Hierarchical Deterministic Wallet) cho ModernTensor Core, tương tự như hệ thống coldkey/hotkey của ModernTensor.

## 🏗️ Kiến trúc hệ thống

### Tổng quan
- **HD Wallet**: Ví phân cấp sử dụng BIP44 derivation
- **Coldkey**: Khóa chính (master account) để quản lý
- **Hotkey**: Khóa phụ (derived account) để thực hiện giao dịch
- **Mnemonic**: Cụm từ ghi nhớ 12-24 từ để khôi phục ví

### BIP44 Derivation Path
```
m/44'/637'/{account_index}'/0'/{address_index}'
```
- `44'`: BIP44 standard
- `637'`: Aptos coin type
- `{account_index}'`: Chỉ số coldkey (0, 1, 2, ...)
- `0'`: External chain (địa chỉ nhận)
- `{address_index}'`: Chỉ số hotkey (0, 1, 2, ...)

## 🔐 Bảo mật

### Mã hóa
- **Mnemonic**: Được mã hóa bằng Fernet với password
- **Salt**: Mỗi ví có salt riêng để tăng bảo mật
- **PBKDF2**: Key derivation với 100,000 iterations

### Cấu trúc thư mục
```
wallets/
├── my_wallet/
│   ├── mnemonic.enc      # Mnemonic được mã hóa
│   ├── salt.bin          # Salt cho encryption
│   └── metadata.json     # Thông tin ví và accounts
└── another_wallet/
    ├── mnemonic.enc
    ├── salt.bin
    └── metadata.json
```

## 📋 Sử dụng

### 1. CLI Interface

#### Tạo ví mới
```bash
mtcli hdwallet create --name my_wallet --words 24
```

#### Load ví
```bash
mtcli hdwallet load --name my_wallet
```

#### Tạo coldkey
```bash
mtcli hdwallet create-coldkey --wallet my_wallet --name validator
```

#### Tạo hotkey
```bash
mtcli hdwallet create-hotkey --wallet my_wallet --coldkey validator --name operator
```

#### Export private key
```bash
mtcli hdwallet export-key --wallet my_wallet --coldkey validator --hotkey operator
```

#### Xem thông tin ví
```bash
mtcli hdwallet info --wallet my_wallet
```

#### Khôi phục ví từ mnemonic
```bash
mtcli hdwallet restore --name restored_wallet
```

### 2. Python API

```python
from mt_aptos.keymanager.hd_wallet_manager import AptosHDWalletManager

# Khởi tạo manager
wallet_manager = AptosHDWalletManager()

# Tạo ví mới
mnemonic = wallet_manager.create_wallet("my_wallet", "password123", 24)

# Load ví
wallet_manager.load_wallet("my_wallet", "password123")

# Tạo coldkey
coldkey_info = wallet_manager.create_coldkey("my_wallet", "validator", 0)

# Tạo hotkey
hotkey_info = wallet_manager.create_hotkey("my_wallet", "validator", "operator", 1)

# Lấy Aptos Account object
account = wallet_manager.get_account("my_wallet", "validator", "operator")

# Export private key
private_key = wallet_manager.export_private_key("my_wallet", "validator", "operator")
```

## 🌟 Tính năng nổi bật

### 1. Tương thích với ModernTensor
- **Coldkey/Hotkey model**: Giống hệ thống ModernTensor
- **Hierarchical structure**: Một coldkey quản lý nhiều hotkey
- **Secure storage**: Mnemonic được mã hóa an toàn

### 2. HD Wallet chuẩn
- **BIP39**: Mnemonic phrase chuẩn
- **BIP44**: Derivation path chuẩn
- **Cross-compatible**: Tương thích với các ví khác

### 3. Aptos tích hợp
- **Native Aptos**: Sử dụng Aptos SDK
- **Ed25519**: Cryptography chuẩn của Aptos
- **Account objects**: Trả về Aptos Account objects để sử dụng

## 📖 Ví dụ sử dụng

### Scenario 1: Validator Setup
```python
# Tạo ví cho validator
wallet_manager = AptosHDWalletManager()
mnemonic = wallet_manager.create_wallet("validator_wallet", "strong_password", 24)
wallet_manager.load_wallet("validator_wallet", "strong_password")

# Tạo coldkey cho validator chính
validator_coldkey = wallet_manager.create_coldkey("validator_wallet", "main_validator", 0)

# Tạo hotkeys cho các chức năng khác nhau
operator_hotkey = wallet_manager.create_hotkey("validator_wallet", "main_validator", "operator", 1)
staking_hotkey = wallet_manager.create_hotkey("validator_wallet", "main_validator", "staking", 2)
governance_hotkey = wallet_manager.create_hotkey("validator_wallet", "main_validator", "governance", 3)

# Sử dụng accounts
operator_account = wallet_manager.get_account("validator_wallet", "main_validator", "operator")
# operator_account là Aptos Account object, có thể dùng để ký giao dịch
```

### Scenario 2: Multi-User Setup
```python
# Setup cho nhiều người dùng
wallet_manager = AptosHDWalletManager()

# Tạo ví chính
mnemonic = wallet_manager.create_wallet("org_wallet", "org_password", 24)
wallet_manager.load_wallet("org_wallet", "org_password")

# Tạo coldkeys cho từng team
dev_coldkey = wallet_manager.create_coldkey("org_wallet", "dev_team", 0)
ops_coldkey = wallet_manager.create_coldkey("org_wallet", "ops_team", 1)
finance_coldkey = wallet_manager.create_coldkey("org_wallet", "finance_team", 2)

# Tạo hotkeys cho từng thành viên
alice_hotkey = wallet_manager.create_hotkey("org_wallet", "dev_team", "alice", 1)
bob_hotkey = wallet_manager.create_hotkey("org_wallet", "dev_team", "bob", 2)
charlie_hotkey = wallet_manager.create_hotkey("org_wallet", "ops_team", "charlie", 1)
```

### Scenario 3: Import External Keys
```python
# Import private key từ bên ngoài
wallet_manager = AptosHDWalletManager()
wallet_manager.create_wallet("mixed_wallet", "password", 24)
wallet_manager.load_wallet("mixed_wallet", "password")

# Import external private key
external_key = "0x1234567890abcdef..."
imported_account = wallet_manager.import_account_by_private_key(
    "mixed_wallet", 
    external_key, 
    "imported_account"
)
```

## 🔄 So sánh với ModernTensor

| Tính năng | ModernTensor | ModernTensor HD Wallet |
|-----------|-----------|------------------------|
| Coldkey | ✅ Master key | ✅ Master account (coldkey) |
| Hotkey | ✅ Derived keys | ✅ Derived accounts (hotkey) |
| Mnemonic | ✅ 12 words | ✅ 12-24 words |
| Encryption | ✅ Password | ✅ Fernet + PBKDF2 |
| Hierarchical | ✅ Tree structure | ✅ BIP44 HD derivation |
| CLI | ✅ btcli | ✅ mtcli hdwallet |
| Blockchain | Substrate | Aptos |

## 🛠️ Development

### Thêm tính năng mới
1. Extend `AptosHDWalletManager` class
2. Add CLI commands trong `hd_wallet_cli.py`
3. Update tests và documentation

### Testing
```python
# Chạy demo
python examples/hd_wallet_demo.py

# Chạy tests
pytest tests/test_hd_wallet.py
```

## 🔒 Security Best Practices

### 1. Mnemonic Security
- **Never store mnemonic in plaintext**
- **Use strong passwords for encryption**
- **Backup mnemonic securely offline**
- **Test recovery process**

### 2. Key Management
- **Use coldkeys for high-value operations**
- **Use hotkeys for frequent transactions**
- **Rotate hotkeys regularly**
- **Monitor account activity**

### 3. Password Policy
- **Minimum 12 characters**
- **Include uppercase, lowercase, numbers, symbols**
- **Use password manager**
- **Don't reuse passwords**

## 📞 Support

### Issues & Questions
- GitHub Issues: [Link to issues]
- Documentation: [Link to docs]
- Community: [Link to community]

### Contributing
1. Fork repository
2. Create feature branch
3. Add tests
4. Submit PR

## 📄 License

MIT License - see LICENSE file for details. 