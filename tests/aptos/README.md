# Bộ kiểm thử Aptos

Thư mục này chứa các bài kiểm thử cho việc tích hợp blockchain Aptos trong ModernTensor SDK.

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