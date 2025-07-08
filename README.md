# ModernTensor Core 🚀

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**ModernTensor Core** là phiên bản của ModernTensor được xây dựng trên blockchain Core, mang đến một nền tảng huấn luyện mô hình AI phi tập trung với Bitcoin staking integration và dual staking rewards. Dự án tận dụng EVM-compatible smart contracts và Bitcoin staking mechanism của Core blockchain để tạo ra một hệ sinh thái AI training bền vững.

## 📋 Tính năng chính

* **Bitcoin Staking Integration:** Tích hợp với Core's Self-Custodial Bitcoin Staking
* **Dual Staking Rewards:** Stake cả Bitcoin và CORE tokens để nhận yield cao hơn  
* **Staking Tiers:** Base, Boost, Super, Satoshi tiers với multipliers khác nhau
* **Quản lý tài khoản:** Tạo, lưu trữ và quản lý các tài khoản Core blockchain an toàn
* **Đăng ký Miner/Validator:** Tham gia vào mạng ModernTensor với Bitcoin staking bonuses
* **Đồng thuận phi tập trung:** Các miner cung cấp dịch vụ AI và nhận phần thưởng từ dual staking
* **Quản lý Subnet:** Tạo và quản lý các subnet có thể tùy chỉnh cho các tác vụ AI cụ thể
* **EVM Compatibility:** Tương tác đầy đủ với Core blockchain ecosystem

## 🌟 Core Blockchain Advantages

### **Bitcoin-Powered AI Training**
- **First-of-its-kind:** Kết hợp Bitcoin staking với AI model training
- **Enhanced Security:** Backed by Bitcoin's security model
- **Self-Custodial:** Giữ quyền kiểm soát Bitcoin của bạn
- **No Slashing Risk:** Bitcoin staking không có rủi ro slashing

### **Dual Staking Economics**
- **Base Tier (1x):** CORE tokens only
- **Boost Tier (1.25x):** CORE + Bitcoin ratio ≥ 1:10  
- **Super Tier (1.5x):** CORE + Bitcoin ratio ≥ 1:2
- **Satoshi Tier (2x):** CORE + Bitcoin ratio ≥ 1:1

### **Institutional Ready**
- **lstBTC Integration:** Liquid staking Bitcoin through institutional custodians
- **Compliance:** Regulated custodial solutions (BitGo, Copper, Hex Trust)
- **Scalability:** High TPS with low fees (<$0.01 median)

## 🔧 Cấu trúc dự án

* `contracts/`: Smart contracts Solidity cho Core blockchain
* `mt_core/`: ModernTensor Core SDK
  * `core/`: Smart contract interactions và blockchain client
  * `core_client/`: Core blockchain client utilities  
  * `keymanager/`: Quản lý tài khoản và khóa
  * `consensus/`: Consensus logic với Bitcoin staking integration
  * `cli/`: Giao diện dòng lệnh
* `examples/`: Ví dụ cách sử dụng SDK với Bitcoin staking

## 🚀 Bắt đầu

### Cài đặt

1. **Cài đặt các phụ thuộc:**
   ```bash
   pip install web3 eth-account bitcoin
   ```

2. **Cài đặt ModernTensor Core SDK:**
   ```bash
   pip install -e .
   ```

3. **Clone repository:**
   ```bash
   git clone https://github.com/sonson0910/moderntensor_core.git
   cd moderntensor_core
   ```

### Cấu hình Core Blockchain

```python
from moderntensor.mt_core.config.settings import Settings

# Cấu hình cho Core testnet
settings = Settings(
    CORE_NODE_URL="https://rpc.test.btcs.network",
    CORE_CONTRACT_ADDRESS="0x...",  # ModernTensor contract
    CORE_TOKEN_ADDRESS="0x...",     # CORE token
    BITCOIN_STAKING_ENABLED=True,
    DUAL_STAKING_ENABLED=True
)
```

### Quản lý tài khoản

```python
from moderntensor.mt_core.account import CoreAccount

# Tạo tài khoản mới
account = CoreAccount()
print(f"Address: {account.address}")
print(f"Private Key: {account.private_key}")

# Load tài khoản từ private key
account = CoreAccount(private_key="0x...")
```

### Tương tác với ModernTensor Smart Contract

```python
import asyncio
from web3 import Web3
from moderntensor.mt_core.core_client import ModernTensorCoreClient

# Khởi tạo Web3 và client
w3 = Web3(Web3.HTTPProvider("https://rpc.test.btcs.network"))
client = ModernTensorCoreClient(
    w3=w3,
    contract_address="0x...",  # ModernTensor contract
    account=account.account
)

# Đăng ký miner với dual staking
tx_hash = client.register_miner(
    uid=b"my_unique_miner_id",
    subnet_uid=1,
    stake_amount=10_000_000_000_000_000_000,  # 10 CORE tokens
    api_endpoint="http://my-miner-endpoint.com"
)

# Stake Bitcoin để tăng rewards
bitcoin_tx_hash = client.stake_bitcoin(
    tx_hash=b"bitcoin_transaction_hash",
    amount=100_000_000,  # 1 BTC in satoshis
    lock_time=int(time.time()) + 86400  # 24 hours
)

# Kiểm tra staking tier
tier = client.calculate_staking_tier(account.address)
tier_name = client.get_staking_tier_name(tier)
print(f"Staking Tier: {tier_name}")
```

### Bitcoin Staking Integration

```python
# Self-Custodial Bitcoin Staking
from moderntensor.mt_core.staking import BitcoinStaking

staker = BitcoinStaking(
    bitcoin_rpc_url="https://bitcoin-rpc.com",
    core_client=client
)

# Create Bitcoin timelock transaction
bitcoin_tx = staker.create_timelock_transaction(
    amount=1.0,  # 1 BTC
    lock_time_hours=24,
    core_validator_address="0x..."
)

# Broadcast to Bitcoin network
tx_hash = staker.broadcast_transaction(bitcoin_tx)

# Register on Core blockchain for rewards
core_tx = client.stake_bitcoin(
    tx_hash=tx_hash.encode(),
    amount=100_000_000,  # 1 BTC in satoshis
    lock_time=bitcoin_tx.lock_time
)
```

## 🧠 Smart Contracts

Smart contracts Solidity của ModernTensor được thiết kế để quản lý thông tin Miner, Validator, Subnet, và Bitcoin staking integration.

### Deployment trên Core Blockchain

```bash
# Compile contracts
cd contracts
npx hardhat compile

# Deploy to Core testnet
npx hardhat run scripts/deploy.js --network core-testnet

# Deploy to Core mainnet
npx hardhat run scripts/deploy.js --network core-mainnet

# Verify contract
npx hardhat verify --network core-testnet <contract_address> "<constructor_args>"
```

### Key Contract Features

- **ERC20 Integration:** Full CORE token integration
- **Bitcoin Verification:** On-chain Bitcoin transaction verification
- **Dual Staking Logic:** Automatic tier calculation and rewards
- **Subnet Management:** Dynamic subnet creation and management
- **Performance Tracking:** Real-time miner/validator scoring

## 💰 Economics và Rewards

### Bitcoin Staking Yields
- **Base APY:** 3-5% từ Bitcoin staking
- **CORE Rewards:** Additional CORE tokens từ AI training
- **Tier Multipliers:** Up to 2x rewards ở Satoshi tier

### Revenue Streams
1. **Bitcoin Staking Rewards:** Native Bitcoin yields
2. **AI Training Fees:** Payments từ AI model training
3. **Validation Rewards:** Consensus participation rewards
4. **Dual Staking Bonuses:** Enhanced yields từ CORE + Bitcoin

## 🔗 Core Blockchain Integration

### Network Configuration
- **Testnet RPC:** https://rpc.test.btcs.network
- **Mainnet RPC:** https://rpc.coredao.org  
- **Explorer:** https://scan.coredao.org
- **Chain ID:** 1116 (mainnet), 1115 (testnet)

### Bitcoin Integration
- **Timelock Method:** CLTV (CheckLockTimeVerify)
- **Minimum Lock:** 24 hours
- **Verification:** On-chain Bitcoin transaction proofs
- **Custody:** Self-custodial (you keep your Bitcoin)

## 📊 Monitoring và Analytics

```python
# Kiểm tra network statistics
stats = client.get_network_stats()
print(f"Total Miners: {stats['total_miners']}")
print(f"Total Validators: {stats['total_validators']}")
print(f"Bitcoin Staked: {stats['bitcoin_staked']} BTC")
print(f"CORE Staked: {stats['core_staked']} CORE")

# Theo dõi personal performance
miner_info = client.get_miner_info(account.address)
print(f"Performance Score: {miner_info['last_performance'] / 1000000:.2f}")
print(f"Trust Score: {miner_info['trust_score'] / 1000000:.2f}")
print(f"Total Rewards: {miner_info['accumulated_rewards']}")
```

## 🤝 Đóng góp

Chúng tôi hoan nghênh đóng góp vào ModernTensor Core! Bạn có thể:

1. Fork repository
2. Tạo nhánh tính năng mới (`git checkout -b feature/bitcoin-ai-integration`)
3. Commit các thay đổi (`git commit -m 'Add Bitcoin AI training integration'`)
4. Push nhánh (`git push origin feature/bitcoin-ai-integration`)
5. Mở một Pull Request

## 📜 Giấy phép

Dự án này được cấp phép theo Giấy phép MIT - xem tệp `LICENSE` để biết chi tiết.

## 📞 Liên hệ

Để biết thêm thông tin, vui lòng liên hệ:
- GitHub: [https://github.com/sonson0910/moderntensor_core](https://github.com/sonson0910/moderntensor_core)
- Telegram: [ModernTensor Community](https://t.me/moderntensor)

## 🎯 Roadmap

### Phase 1: Core Integration ✅
- [x] Smart contract migration to Solidity
- [x] Core blockchain client integration  
- [x] Bitcoin staking mechanism
- [x] Dual staking rewards

### Phase 2: Enhanced Features 🚧
- [ ] lstBTC institutional integration
- [ ] Advanced Bitcoin mining integration
- [ ] Cross-chain bridge support
- [ ] Mobile app for staking

### Phase 3: Ecosystem Growth 🔮
- [ ] DeFi protocol partnerships
- [ ] Bitcoin L2 integration
- [ ] Institutional custody solutions
- [ ] Governance token migration

---

**ModernTensor Core - Where Bitcoin meets AI Training** 🚀🧠₿
