# Troubleshooting Failed Tests

Một số tests có thể thất bại trong môi trường CI hoặc khi chạy trên hệ thống chưa được cấu hình đầy đủ. Tài liệu này cung cấp hướng dẫn để khắc phục các lỗi phổ biến trong các tests.

## Tổng quan về các tests thất bại

Ba tests chính thường thất bại trong môi trường CI:

1. `test_aptos_basic.py`
2. `test_aptos_hd_wallet.py`
3. `test_aptos_hd_wallet_contract.py`

## Nguyên nhân chung của các lỗi

- **Thiếu wallet keys**: Tests cần wallet keys cụ thể đã được cấu hình
- **Aptos CLI không khả dụng**: Một số tests cần Aptos CLI hoạt động đầy đủ
- **Vấn đề với `AccountAddress.from_str()`**: Thay vì sử dụng hàm này, cần sử dụng `AccountAddress.from_hex()`
- **Thiếu mock cho một số phương thức của client**: Không tất cả các phương thức đều được mock đầy đủ

## Hướng dẫn khắc phục từng test

### 1. Sửa `test_aptos_basic.py`

#### Vấn đề #1: AccountAddress.from_str()

```python
# Thay thế
to_address = AccountAddress.from_str("0x1")

# Bằng
to_address = AccountAddress.from_hex("0x1")
```

#### Vấn đề #2: Xử lý ngoại lệ trong test_error_handling

Trong hàm `test_error_handling`, chúng ta cần đảm bảo test tạo ra một ngoại lệ có thể dự đoán với mock client:

```python
@pytest.mark.asyncio
async def test_error_handling(aptos_client, test_account):
    """Test error handling."""
    # Tạo một địa chỉ không hợp lệ
    if isinstance(aptos_client, MockRestClient):
        # Mock client testing - sử dụng địa chỉ không hợp lệ
        invalid_address = "0xinvalid"
    else:
        # Real client testing - sử dụng địa chỉ hợp lệ nhưng không tồn tại
        invalid_address = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    
    # Kiểm tra xử lý lỗi với địa chỉ không hợp lệ
    with pytest.raises(Exception) as excinfo:
        await aptos_client.account(invalid_address)
    
    # Kiểm tra thông báo lỗi
    error_msg = str(excinfo.value)
    assert "not found" in error_msg.lower() or "invalid" in error_msg.lower()
    print(f"\nTested error handling successfully: {error_msg}")
```

#### Vấn đề #3: Bổ sung skip cho test_transaction_submission và test_transaction_wait

Thêm điều kiện để bỏ qua tests này trong môi trường CI:

```python
@pytest.mark.asyncio
async def test_transaction_submission(aptos_client, test_account):
    """Test submitting a transaction."""
    # Skip trong môi trường CI
    if os.environ.get("CI") == "true" or os.environ.get("USE_REAL_APTOS_CLIENT") == "false":
        pytest.skip("Skipping transaction test in CI environment")
        
    # Tiếp tục test như bình thường...
```

### 2. Sửa `test_aptos_hd_wallet.py`

#### Vấn đề #1: Tạo một fixture mới cho HD wallet

```python
@pytest.fixture
def test_hd_wallet():
    """
    Tạo HD wallet cho tests.
    Trong môi trường CI, trả về một ví cố định thay vì tạo ví mới.
    """
    # Trong CI, sử dụng một mnemonic cố định
    if os.environ.get("CI") == "true" or os.environ.get("USE_REAL_APTOS_CLIENT") == "false":
        test_mnemonic = "test test test test test test test test test test test junk"
        return create_hd_wallet(mnemonic=test_mnemonic)
    else:
        # Trong môi trường local, tạo ví mới
        return create_hd_wallet()
```

#### Vấn đề #2: Mock HD wallet functions

Thêm một class MockHDWallet vào mock_client.py:

```python
class MockHDWallet:
    """Mock cho HD wallet functions."""
    
    @staticmethod
    def create_wallet(mnemonic=None):
        """Tạo một wallet giả lập."""
        if not mnemonic:
            mnemonic = "test test test test test test test test test test test junk"
        # Tạo một account cố định từ mnemonic
        private_key = bytes.fromhex("a8cbf043a4c60c71f1424d0ab8a3a341e5e0b8e24daf5bd3b8299f1f8c2ece58")
        return Account.load_key(private_key)
```

### 3. Sửa `test_aptos_hd_wallet_contract.py`

#### Vấn đề #1: Contract address mocks

Thêm mock cho contract address vào MockRestClient:

```python
def configure_contract_resource(self, contract_address, resource_type, data):
    """Cấu hình resource cho một contract address."""
    if contract_address not in self._account_resources:
        self._account_resources[contract_address] = []
    
    # Thêm hoặc cập nhật resource
    found = False
    for i, resource in enumerate(self._account_resources[contract_address]):
        if resource["type"] == resource_type:
            self._account_resources[contract_address][i]["data"] = data
            found = True
            break
    
    if not found:
        self._account_resources[contract_address].append({
            "type": resource_type,
            "data": data
        })
```

#### Vấn đề #2: Cách thiết lập để tests hoạt động trong CI

Tạo một file setup script để chạy trước khi test:

```python
# tests/aptos/setup_ci_tests.py
from tests.aptos.mock_client import MockRestClient

def setup_contract_mocks():
    """Thiết lập mocks cho các contract tests."""
    client = MockRestClient()
    
    # Cấu hình resources cho các contract chung
    client.configure_contract_resource(
        "0x1", 
        "0x1::coin::CoinInfo<0x1::aptos_coin::AptosCoin>",
        {
            "name": "Aptos Coin",
            "symbol": "APT",
            "decimals": 8,
            "supply": {"value": "100000000000000000"}
        }
    )
    
    # Cấu hình cho ModernTensor contracts
    client.configure_contract_resource(
        "0x441e7a4984f621e9ece9747ac2ffe530e135a9ac6f60886ddb452dae5632ee27",
        "ModernTensor::subnet::SubnetRegistry",
        {
            "subnets": [
                {
                    "id": 1,
                    "name": "Default Subnet",
                    "owner": "0x1",
                    "miners": ["0x2", "0x3"],
                    "validators": ["0x4", "0x5"]
                }
            ]
        }
    )
    
    return client

# Chạy setup từ run_tests_with_mock.py
```

## Chạy tests sau khi sửa

Sau khi thực hiện các thay đổi này, bạn có thể chạy lại các tests:

```bash
# Chạy tất cả tests bao gồm cả các tests đã sửa
python run_tests_with_mock.py

# Chạy chỉ test đã sửa để xác nhận
python run_tests_with_mock.py --tests test_aptos_basic.py test_aptos_hd_wallet.py test_aptos_hd_wallet_contract.py
```

## Ghi chú bổ sung

- **Tính nhất quán của mocks**: Đảm bảo rằng các mocks được sử dụng nhất quán trong tất cả các tests
- **Mock phụ thuộc ngoài**: Mọi phụ thuộc ngoài (ví dụ: Aptos CLI) nên được mock trong CI
- **Cách bỏ qua các tests không an toàn**: Sử dụng `pytest.skip()` để bỏ qua các tests không an toàn trong CI

Khi bạn thêm tests mới, hãy xác nhận rằng chúng hoạt động ổn định với mock client, đặc biệt là trong môi trường CI. Thêm các tests an toàn vào mảng `ci_safe_tests` trong `run_tests_with_mock.py`. 