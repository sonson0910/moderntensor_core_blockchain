# Tích hợp ModernTensor trên Aptos

Kho lưu trữ này chứa mạng đào tạo AI phi tập trung ModernTensor đã được chuyển đổi sang blockchain Aptos.

## Tổng quan

ModernTensor là một mạng phi tập trung dành cho việc đào tạo AI với ba loại tham gia chính:
- **Miners (Thợ đào)**: Đóng góp tài nguyên tính toán để chạy các tác vụ đào tạo
- **Validators (Người xác thực)**: Xác minh kết quả tác vụ và chạy đồng thuận
- **Subnets (Mạng con)**: Nhóm các thợ đào và người xác thực thành các miền chuyên biệt

## Cài đặt

### Yêu cầu

1. Aptos CLI đã cài đặt
2. Python 3.9+ đã cài đặt
3. Các gói Python cần thiết (cài đặt với `pip install -r requirements.txt`)

### Thiết lập tài khoản Aptos

1. Tạo tài khoản Aptos mới:
   ```bash
   aptos key generate
   ```

2. Khởi tạo cấu hình cục bộ:
   ```bash
   aptos init
   ```

3. Ở lần đầu tiên sử dụng, bạn sẽ cần tạo tài khoản và nhận tokens từ faucet Aptos.

## Cấu trúc dự án

Dự án bao gồm các thành phần chính sau:

- `sdk/`: SDK Python để tương tác với hợp đồng và mạng ModernTensor
  - `aptos/`: Module chính cho Aptos
    - `contract_client.py`: Client tương tác với hợp đồng ModernTensor
    - `service.py`: Dịch vụ chính cho Aptos
    - `metagraph.py`: Quản lý metagraph
    - `module_manager.py`: Quản lý các module
    - `sources/`: Mã nguồn Move
  - `aptos_core/`: Module cốt lõi cho Aptos
    - `contract_client.py`: Client tương tác với hợp đồng
    - `context.py`: Tạo ngữ cảnh Aptos
    - `address.py`: Xử lý địa chỉ Aptos
    - `account_service.py`: Dịch vụ quản lý tài khoản
    - `validator_helper.py`: Tiện ích cho validator
  - `consensus/`: Logic đồng thuận
  - `core/`: Các kiểu dữ liệu cốt lõi
  - `metagraph/`: Quản lý tập dữ liệu của mạng lưới
  - `config/`: Cấu hình ứng dụng
  - `keymanager/`: Quản lý khóa và tài khoản
  - `examples/`: Các ví dụ sử dụng SDK
  - `scripts/`: Các script tiện ích

## Sử dụng

### Chạy Validator Node

1. Cập nhật file cấu hình:
   ```
   cp sdk/config/settings.example.py sdk/config/settings.py
   ```

2. Chỉnh sửa tệp `settings.py` và cập nhật:
   - `APTOS_NODE_URL`
   - `APTOS_CONTRACT_ADDRESS` 
   - `APTOS_PRIVATE_KEY`
   - `APTOS_ACCOUNT_ADDRESS`
   - `VALIDATOR_API_ENDPOINT`

3. Chạy validator node:
   ```bash
   python -m sdk.runner validator
   ```

### Chạy Miner Node

1. Cập nhật file cấu hình như trên

2. Chạy miner node:
   ```bash
   python -m sdk.runner miner
   ```

## Smart Contracts

The Move smart contracts for ModernTensor are in the `sdk/aptos/sources` directory:

- `miner.move`: Handles miner registration and performance tracking
- `validator.move`: Manages validator registration, consensus, and rewards
- `subnet.move`: Manages subnet creation and member assignment
- `moderntensor.move`: Main contract coordinating the system

### Deploy Contracts

1. Compile the contracts:
   ```bash
   aptos move compile
   ```

2. Deploy to testnet:
   ```bash
   aptos move publish
   ```

## Initialize the Network

1. Initialize registry and settings:
   ```bash
   aptos move run --function-id $ACCOUNT_ADDRESS::moderntensor::initialize
   ```

2. Create a subnet:
   ```bash
   aptos move run --function-id $ACCOUNT_ADDRESS::moderntensor::create_subnet --args u64:1
   ```

## Register as Miner/Validator

1. Register as miner:
   ```bash
   aptos move run --function-id $ACCOUNT_ADDRESS::moderntensor::register_miner --args u64:1 string:http://your-miner-endpoint.com
   ```

2. Register as validator:
   ```bash
   aptos move run --function-id $ACCOUNT_ADDRESS::moderntensor::register_validator --args u64:1 string:http://your-validator-endpoint.com
   ```

## API Endpoints

Both miners and validators expose HTTP APIs:

- Miner API: Default port 8080
- Validator API: Default port 9090

## Components

The key SDK components:

- `sdk/aptos/contract_client.py`: Client for Aptos contract interactions
- `sdk/aptos/service.py`: Main service for Aptos integration
- `sdk/consensus/state.py`: Consensus state management
- `sdk/consensus/node.py`: Validator node implementation

## Consensus Process

The consensus process:

1. Validators select miners and send tasks
2. Miners process tasks and return results
3. Validators score results and broadcast scores to peers
4. Validators run consensus to calculate final scores
5. Scores and trust values are updated on the blockchain

## Development and Testing

For development and testing purposes, use the Aptos testnet.

## Testing (Kiểm thử)

Để chạy các test case cho dự án, bạn nên sử dụng môi trường ảo với conda để đảm bảo tương thích và tránh lỗi phụ thuộc.

### 1. Tạo và kích hoạt môi trường conda

```bash
conda create -n aptos python=3.11 -y
conda activate aptos
```

### 2. Cài đặt các dependencies cần thiết

```bash
pip install -r requirements-test.txt
```

### 3. Chạy test

Ví dụ chạy toàn bộ test:
```bash
pytest
```

Chạy một file test cụ thể:
```bash
pytest tests/aptos/test_aptos_basic.py -v
```

**Lưu ý:**
- Luôn kích hoạt môi trường bằng `conda activate aptos` trước khi chạy test.
- Nếu bạn chưa cài conda, hãy cài Anaconda hoặc Miniconda trước.
- Các test case được thiết kế cho Python 3.11, không nên dùng Python 3.12 trở lên.

## License

MIT License 