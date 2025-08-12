# ModernTensor Core 🚀

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**ModernTensor Core** is a version of ModernTensor built on the Core blockchain, delivering a decentralized AI model training platform with Bitcoin staking integration and dual staking rewards. The project leverages EVM-compatible smart contracts and Core blockchain's Bitcoin staking mechanism to create a sustainable AI training ecosystem.

## 📋 Key Features

* **Bitcoin Staking Integration:** Integration with Core's Self-Custodial Bitcoin Staking
* **Dual Staking Rewards:** Stake both Bitcoin and CORE tokens to receive higher yields
* **Staking Tiers:** Base, Boost, Super, Satoshi tiers with different multipliers
* **Account Management:** Create, store, and manage secure Core blockchain accounts
* **Miner/Validator Registration:** Participate in the ModernTensor network with Bitcoin staking bonuses
* **Decentralized Consensus:** Miners provide AI services and receive rewards from dual staking
* **Subnet Management:** Create and manage customizable subnets for specific AI tasks
* **EVM Compatibility:** Full interaction with Core blockchain ecosystem

## 🌟 Core Blockchain Advantages

### **Bitcoin-Powered AI Training**
- **First-of-its-kind:** Combines Bitcoin staking with AI model training
- **Enhanced Security:** Backed by Bitcoin's security model
- **Self-Custodial:** Maintain control of your Bitcoin
- **No Slashing Risk:** Bitcoin staking has no slashing risk

### **Dual Staking Economics**
- **Base Tier (1x):** CORE tokens only
- **Boost Tier (1.25x):** CORE + Bitcoin ratio ≥ 1:10
- **Super Tier (1.5x):** CORE + Bitcoin ratio ≥ 1:2
- **Satoshi Tier (2x):** CORE + Bitcoin ratio ≥ 1:1

### **Institutional Ready**
- **lstBTC Integration:** Liquid staking Bitcoin through institutional custodians
- **Compliance:** Regulated custodial solutions (BitGo, Copper, Hex Trust)
- **Scalability:** High TPS with low fees (<$0.01 median)

## 🔧 Project Structure

* `contracts/`: Solidity smart contracts for Core blockchain
* `mt_core/`: ModernTensor Core SDK
  * `core/`: Smart contract interactions and blockchain client
  * `core_client/`: Core blockchain client utilities
  * `keymanager/`: Account and key management
  * `consensus/`: Consensus logic with Bitcoin staking integration
  * `cli/`: Command line interface
* `examples/`: Examples of using the SDK with Bitcoin staking

## 🚀 Getting Started

### Installation

1. **Install dependencies:**
   ```bash
   pip install web3 eth-account bitcoin
   ```

2. **Install ModernTensor Core SDK:**
   ```bash
   pip install -e .
   ```

3. **Clone repository:**
   ```bash
   git clone https://github.com/sonson0910/moderntensor_core.git
   cd moderntensor_core
   ```

### Core Blockchain Configuration

```python
from moderntensor.mt_core.config.settings import Settings

# Configuration for Core testnet
settings = Settings(
    CORE_NODE_URL="https://rpc.test2.btcs.network",
    CORE_CONTRACT_ADDRESS="0x56C2F2d0914DF10CE048e07EF1eCbac09AF80cd2",  # ModernTensorAI_Optimized - DEPLOYED
    CORE_TOKEN_ADDRESS="0x7B74e4868c8C500D6143CEa53a5d2F94e94c7637",     # Mock CORE token (ultra-low testnet)
    BTC_TOKEN_ADDRESS="0x44Ed1441D79FfCb76b7D6644dBa930309E0E6F31",      # Mock BTC token (ultra-low testnet)
    BITCOIN_STAKING_ENABLED=True,
    DUAL_STAKING_ENABLED=True
)
```

### Account Management

```python
from moderntensor.mt_core.account import CoreAccount

# Create new account
account = CoreAccount()
print(f"Address: {account.address}")
print(f"Private Key: {account.private_key}")

# Load account from private key
account = CoreAccount(private_key="0x...")
```

### Interacting with ModernTensor Smart Contract

```python
import asyncio
from web3 import Web3
from moderntensor.mt_core.core_client import ModernTensorCoreClient

# Initialize Web3 and client
w3 = Web3(Web3.HTTPProvider("https://rpc.test2.btcs.network"))
client = ModernTensorCoreClient(
    w3=w3,
    contract_address="0x...",  # ModernTensor contract
    account=account.account
)

# Register miner with dual staking
tx_hash = client.register_miner(
    uid=b"my_unique_miner_id",
    subnet_uid=1,
    stake_amount=10_000_000_000_000_000_000,  # 10 CORE tokens
    api_endpoint="http://my-miner-endpoint.com"
)

# Stake Bitcoin to increase rewards
bitcoin_tx_hash = client.stake_bitcoin(
    tx_hash=b"bitcoin_transaction_hash",
    amount=100_000_000,  # 1 BTC in satoshis
    lock_time=int(time.time()) + 86400  # 24 hours
)

# Check staking tier
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

ModernTensor's Solidity smart contracts are designed to manage Miner, Validator, Subnet information, and Bitcoin staking integration.

### Deployment on Core Blockchain

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

## 💰 Economics and Rewards

### Bitcoin Staking Yields
- **Base APY:** 3-5% from Bitcoin staking
- **CORE Rewards:** Additional CORE tokens from AI training
- **Tier Multipliers:** Up to 2x rewards at Satoshi tier

### Revenue Streams
1. **Bitcoin Staking Rewards:** Native Bitcoin yields
2. **AI Training Fees:** Payments from AI model training
3. **Validation Rewards:** Consensus participation rewards
4. **Dual Staking Bonuses:** Enhanced yields from CORE + Bitcoin

## 🔗 Core Blockchain Integration

### Network Configuration
- **Testnet RPC:** https://rpc.test2.btcs.network
- **Mainnet RPC:** https://rpc.test2.btcs.network
- **Explorer:** https://scan.coredao.org
- **Chain ID:** 1116 (mainnet), 1115 (testnet)

### Bitcoin Integration
- **Timelock Method:** CLTV (CheckLockTimeVerify)
- **Minimum Lock:** 24 hours
- **Verification:** On-chain Bitcoin transaction proofs
- **Custody:** Self-custodial (you keep your Bitcoin)

## 📊 Monitoring and Analytics

```python
# Check network statistics
stats = client.get_network_stats()
print(f"Total Miners: {stats['total_miners']}")
print(f"Total Validators: {stats['total_validators']}")
print(f"Bitcoin Staked: {stats['bitcoin_staked']} BTC")
print(f"CORE Staked: {stats['core_staked']} CORE")

# Track personal performance
miner_info = client.get_miner_info(account.address)
print(f"Performance Score: {miner_info['last_performance'] / 1000000:.2f}")
print(f"Trust Score: {miner_info['trust_score'] / 1000000:.2f}")
print(f"Total Rewards: {miner_info['accumulated_rewards']}")
```

## 🤝 Contributing

We welcome contributions to ModernTensor Core! You can:

1. Fork the repository
2. Create a new feature branch (`git checkout -b feature/bitcoin-ai-integration`)
3. Commit your changes (`git commit -m 'Add Bitcoin AI training integration'`)
4. Push the branch (`git push origin feature/bitcoin-ai-integration`)
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the `LICENSE` file for details.

## 📞 Contact

For more information, please contact:
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
