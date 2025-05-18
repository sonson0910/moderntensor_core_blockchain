# Tích hợp ModernTensor trên Aptos

Kho lưu trữ này chứa mạng đào tạo AI phi tập trung ModernTensor đã được chuyển đổi sang blockchain Aptos.

## Tổng quan

ModernTensor là một mạng phi tập trung dành cho việc đào tạo AI với ba loại tham gia chính:
- **Miners (Thợ đào)**: Đóng góp tài nguyên tính toán để chạy các tác vụ đào tạo
- **Validators (Người xác thực)**: Xác minh kết quả tác vụ và chạy đồng thuận
- **Subnets (Mạng con)**: Nhóm các thợ đào và người xác thực thành các miền chuyên biệt

Phiên bản gốc sử dụng blockchain Cardano, nhưng phiên bản này đã được chuyển sang Aptos.

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

- `move/`: Chứa hợp đồng thông minh Move cho Aptos
- `sdk/`: SDK Python để tương tác với hợp đồng và mạng ModernTensor
  - `aptos_core/`: Module tương tác với blockchain Aptos
    - `contract_client.py`: Client tương tác với hợp đồng ModernTensor
    - `context.py`: Tạo ngữ cảnh Aptos dễ dàng sử dụng
    - `address.py`: Xử lý địa chỉ Aptos
    - `account_service.py`: Dịch vụ quản lý tài khoản và giao dịch
    - `validator_helper.py`: Tiện ích để tương tác với validator
  - `consensus/`: Logic đồng thuận
  - `core/`: Các kiểu dữ liệu cốt lõi
  - `metagraph/`: Quản lý tập dữ liệu của mạng lưới
  - `config/`: Cấu hình ứng dụng
  - `service/`: Các dịch vụ cũ từ phiên bản Cardano
  - `smartcontract/`: Tương tác với hợp đồng Cardano (sẽ bị loại bỏ)

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

## Quá trình chuyển đổi

Dự án đã được chuyển đổi từ Cardano sang Aptos với các thay đổi chính:

1. Chuyển đổi hợp đồng Plutus thành hợp đồng Move
2. Thay thế BlockFrostChainContext bằng client RestClient của Aptos
3. Cập nhật tất cả tương tác blockchain để sử dụng Aptos API
4. Tạo module mới để trừu tượng hóa việc tương tác với Aptos
5. Cập nhật quy trình đồng thuận để phản ánh mô hình Aptos thay vì Cardano UTxO

## Lưu ý phát triển

Một số khu vực vẫn đang trong quá trình chuyển đổi:

1. Tương tác với hợp đồng mới của Aptos
2. Truy cập vào trạng thái validator và miner trên blockchain Aptos
3. Quá trình đồng thuận và xác thực

## Smart Contracts

The Move smart contracts for ModernTensor are in the `move/sources` directory:

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

## Run the Node

### Miner Node

```bash
python -m sdk.runner.py miner
```

### Validator Node

```bash
python -m sdk.runner.py validator
```

## API Endpoints

Both miners and validators expose HTTP APIs:

- Miner API: Default port 8080
- Validator API: Default port 9090

## Components

The key SDK components have been migrated to Aptos:

- `sdk/aptos_core/contract_client.py`: Client for Aptos contract interactions
- `sdk/aptos_core/context.py`: Context provider for Aptos blockchain
- `sdk/consensus/state.py`: Consensus state management adapted for Aptos
- `sdk/consensus/node.py`: Validator node implementation using Aptos

## Consensus Process

The consensus process remains similar to the original implementation:

1. Validators select miners and send tasks
2. Miners process tasks and return results
3. Validators score results and broadcast scores to peers
4. Validators run consensus to calculate final scores
5. Scores and trust values are updated on the blockchain

## Development and Testing

For development and testing purposes, use the Aptos testnet.

## License

[Insert your license information here] 