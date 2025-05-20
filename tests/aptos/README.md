# Tests cho ModernTensor Aptos SDK

Thư mục này chứa các bài kiểm thử (tests) cho ModernTensor Aptos SDK. 

## Vấn đề với Rate Limits

Aptos API có giới hạn số lượng requests từ một IP không xác thực:

```
Per anonymous IP rate limit exceeded. Limit: 50000 compute units per 300 seconds window.
```

Điều này có thể gây khó khăn khi chạy các tests tự động, đặc biệt là khi:
- Chạy nhiều tests cùng lúc
- Chạy tests liên tục (ví dụ: trong CI/CD pipeline)
- Không có API key

## Giải pháp: Mock Client

Để giải quyết vấn đề rate limit, chúng tôi đã tạo ra `MockRestClient`, một phiên bản giả lập của `RestClient` từ Aptos SDK. Mock client này:

1. Giả lập tất cả các API calls để không cần kết nối internet
2. Trả về dữ liệu cố định phù hợp với các tests
3. Không bao giờ gây ra rate limit

## Cách sử dụng Mock Client

### Chạy Tests với Mock Client

Cách đơn giản nhất để chạy tests với mock client là sử dụng script `run_tests_with_mock.py`:

```bash
python tests/aptos/run_tests_with_mock.py
```

Hoặc sử dụng pytest với biến môi trường:

```bash
USE_REAL_APTOS_CLIENT=false pytest tests/aptos/test_aptos_hd_wallet_contract.py -v
```

### Chạy Tests với Real Client

Nếu bạn muốn chạy tests với real client (kết nối đến Aptos Testnet thật), bạn có thể:

```bash
USE_REAL_APTOS_CLIENT=true pytest tests/aptos/test_aptos_hd_wallet_contract.py -v
```

Lưu ý: Bạn có thể gặp rate limit khi sử dụng real client.

## Cấu trúc của Mock Client

Mock client được định nghĩa trong file `tests/aptos/mock_client.py` và bao gồm:

1. `MockResponse`: Giả lập HTTP response
2. `MockHttpClient`: Giả lập HTTP client để thay thế `RestClient.client`
3. `MockRestClient`: Giả lập `RestClient` từ Aptos SDK

## Tùy chỉnh Mock Data

Bạn có thể tùy chỉnh dữ liệu trả về cho các API calls cụ thể:

```python
from tests.aptos.mock_client import MockRestClient

# Tạo mock client
client = MockRestClient()

# Cấu hình resources cho một tài khoản cụ thể
client.configure_account_resources("0x123", [
    {
        "type": "0x1::coin::CoinStore<0x1::aptos_coin::AptosCoin>",
        "data": {
            "coin": {"value": "1000000000"},  # 10 APT
            "frozen": False
        }
    }
])
```

## Lưu ý quan trọng

1. Tests với mock client không kiểm tra tính tương thích với Aptos Testnet thực
2. Chỉ nên sử dụng mock client cho unit tests và CI/CD
3. Vẫn nên chạy tests với real client trước khi release
4. Sử dụng API key nếu muốn gọi Aptos API thường xuyên

## Tài liệu liên quan

- [Aptos SDK Python Documentation](https://github.com/aptos-labs/aptos-python-sdk)
- [Aptos Rate Limiting Information](https://build.aptoslabs.com/docs/start)

## Các file kiểm thử hoạt động

Những bài kiểm thử sau đã được xác nhận hoạt động:

1. **test_aptos_basic.py** - Kiểm thử chức năng cơ bản của Aptos SDK
   - Tạo tài khoản và kiểm tra thuộc tính
   - Kiểm tra số dư
   - Gửi giao dịch
   - Tương tác với hợp đồng thông minh

2. **test_aptos_hd_wallet.py** - Kiểm thử chức năng ví HD
   - Tạo ví từ mnemonic
   - Mã hóa khóa an toàn
   - Xử lý đường dẫn dẫn xuất
   - Khôi phục tài khoản

3. **test_aptos_hd_wallet_contract.py** - Kiểm thử tương tác hợp đồng sử dụng ví HD
   - Gọi hàm view
   - Gửi giao dịch
   - Kiểm tra tài nguyên
   - Tương tác với hợp đồng

4. **test_account_debug.py** - Kiểm thử đơn giản để kiểm tra tài khoản

## Các file kiểm thử không hoạt động

Có một số file kiểm thử khác trong thư mục này hiện không hoạt động do lỗi import:

- test_health_monitoring.py
- test_key_management.py
- test_p2p_consensus.py  
- test_remaining_functions.py
- test_smart_contract.py
- test_subnet.py
- test_token_nft.py
- test_validator_miner.py

Các file này có lỗi import: `from aptos_sdk.client import RestClient` trong khi đúng phải là 
`from aptos_sdk.async_client import RestClient`.

## Chạy kiểm thử

Để chạy các kiểm thử đang hoạt động:

```bash
python -m pytest aptos/test_aptos_basic.py aptos/test_aptos_hd_wallet.py aptos/test_aptos_hd_wallet_contract.py aptos/test_account_debug.py -v -s
```

Để chạy các kiểm thử cụ thể với đầu ra chi tiết:

```bash
python -m pytest aptos/test_aptos_basic.py -v -s
python -m pytest aptos/test_aptos_hd_wallet.py -v -s
python -m pytest aptos/test_aptos_hd_wallet_contract.py -v -s
```

## Tài khoản kiểm thử

Các bài kiểm thử sử dụng tài khoản sau:

```
Khóa riêng tư: 0x82a167f420cfd52500bdcf2754ccf68167ee70e9eef9cc4f95d387e42c97cfd7
Địa chỉ: 0x7b8efb0de5bb99a89a235014eb70fd788f102d29190985ec9f1d8b4ad1b87ff9
```

Tài khoản này tồn tại trên mạng thử nghiệm Aptos nhưng không có token APT. Các bài kiểm thử được thiết kế để hoạt động mà không cần token, tự động bỏ qua các bài kiểm thử chuyển token nếu tài khoản không có số dư.

Để thêm token vào tài khoản này để kiểm thử đầy đủ:
1. Sử dụng vòi cấp token testnet Aptos: https://aptoslabs.com/testnet-faucet
2. Nhập địa chỉ tài khoản nêu trên
3. Yêu cầu token thử nghiệm

## Ghi chú

- Hầu hết các bài kiểm thử có thể chạy mà không cần token APT vì chúng sử dụng các hàm view
- Các bài kiểm thử giao dịch sẽ được bỏ qua nếu tài khoản không có token
- Các bài kiểm thử sử dụng mạng thử nghiệm Aptos (ID mạng 2)
- Xử lý lỗi được thiết kế để hoạt động với các xung đột số thứ tự và vấn đề mempool 

# Mock Client cho Aptos Tests

Mock client cho Aptos SDK tests, giúp tránh vấn đề rate limit API và cho phép chạy tests mà không cần kết nối mạng.

## Cách sử dụng

### Chạy tất cả tests

```bash
# Chạy tất cả tests với mock client
python run_tests_with_mock.py
```

### Chạy ở chế độ CI (chỉ các tests an toàn)

```bash
# Chạy ở chế độ CI - chỉ chạy các tests đã biết là hoạt động trong môi trường CI
python run_tests_with_mock.py --ci
```

### Chạy các tests cụ thể

```bash
# Chỉ chạy một số tests nhất định
python run_tests_with_mock.py --tests test_account_debug.py test_health_monitoring.py
```

## Xử lý lỗi "Rate Limit Exceeded"

Khi chạy tests cho SDK, bạn có thể gặp phải vấn đề về giới hạn tốc độ API (rate limit):

```
Per anonymous IP rate limit exceeded. Limit: 50000 compute units per 300 seconds window.
```

Mock client giải quyết vấn đề này bằng cách giả lập tất cả các API calls, loại bỏ sự phụ thuộc vào Aptos API.

## Debugging tests thất bại

Một số tests có thể thất bại trong môi trường CI vì:

1. **Cần cài đặt đầy đủ Aptos CLI** - dù được mock trong CI nhưng một số tests có thể cần Aptos CLI thực sự
2. **Thiếu file hoặc tài nguyên cụ thể** - một số tests hy vọng tài nguyên đã tồn tại trên máy local
3. **Thiếu bởi biến môi trường** - một số tests cần biến môi trường cụ thể để chạy đúng

### Tests có thể thất bại trong CI

Các tests sau đây có thể thất bại trong môi trường CI nhưng thành công trên máy local với cài đặt đầy đủ:

- `test_aptos_hd_wallet_contract.py` - Cần đặt khóa và file wallet
- `test_aptos_basic.py` - Có thể cần chi tiết hơn về môi trường Aptos
- `test_aptos_hd_wallet.py` - Cần cấu hình wallet thích hợp

### Khắc phục lỗi tests

1. **Chạy với cài đặt đầy đủ**: Đảm bảo có Aptos CLI cùng với wallet và keypair cần thiết
2. **Sử dụng chế độ --ci**: Nếu đang chạy trong môi trường tự động, dùng `--ci` để chạy tests an toàn
3. **Cấu hình MockRestClient**: Bạn có thể thêm mocks tùy chỉnh cho các endpoint cụ thể nếu cần:

```python
client = MockRestClient()
client.configure_account_resources("0x123", [{...}])
```

## Phát triển thêm tests mới

Khi phát triển tests mới, hãy đảm bảo nó hoạt động ổn định với mock client:

1. **Thêm mocks cho endpoint mới** khi cần thiết
2. **Xử lý trường hợp vắng mặt Aptos CLI** bằng cách kiểm tra sự hiện diện hoặc bỏ qua tests
3. **Thêm tests mới vào mảng ci_safe_tests** trong `run_tests_with_mock.py` nếu chúng đủ ổn định

Để biết thêm thông tin về mock client, xem tệp [mock_client.py](./mock_client.py). 