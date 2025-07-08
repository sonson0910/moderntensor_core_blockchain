# ModernTensor Core Blockchain Examples

This directory contains comprehensive examples for using ModernTensor on Core blockchain with Bitcoin staking integration.

## Overview

ModernTensor has been migrated from Aptos to Core blockchain, featuring:
- **Bitcoin Staking Integration**: Self-custodial Bitcoin staking with CLTV timelock
- **Dual Staking Economics**: Four-tier system with reward multipliers
- **EVM Compatibility**: Full Solidity smart contract support
- **High Performance**: ~5000 TPS with <$0.01 fees
- **Security**: Backed by Bitcoin's hash power

## Available Examples

### 1. 🚀 [quickstart.py](quickstart.py)
**Purpose**: Quick start guide for new users
**Features**:
- Interactive setup wizard
- Multiple setup paths (miner, validator, Bitcoin staking)
- Network information display
- Balance checking
- Account creation

**Usage**:
```bash
python quickstart.py
```

Choose from:
- Full quickstart (recommended)
- Miner setup only
- Validator setup only
- Bitcoin staking demo
- Manual step-by-step

### 2. 🔧 [create_account.py](create_account.py)
**Purpose**: Account management for Core blockchain
**Features**:
- Create new Core accounts
- Import/export private keys
- Check account balances
- Network information
- Encrypted storage

**Usage**:
```bash
python create_account.py
```

Options:
1. Create new Core account
2. Load existing account
3. Import from private key
4. List all accounts
5. Check account balance
6. Export private key
7. Get account info
8. Network information

### 3. ⛏️ [register_miner.py](register_miner.py)
**Purpose**: Register miners with Core blockchain
**Features**:
- Miner registration with staking tiers
- Bitcoin staking integration
- Reward multipliers
- Transaction tracking
- Configuration saving

**Usage**:
```bash
python register_miner.py --account miner1 --api http://localhost:8080
```

**Arguments**:
- `--account`: Account name
- `--api`: Miner API endpoint
- `--subnet`: Subnet UID (default: 1)
- `--stake`: CORE tokens to stake (default: 1000)
- `--tier`: Staking tier (base/boost/super/satoshi)
- `--bitcoin-staking`: Enable Bitcoin staking
- `--bitcoin-stake`: Bitcoin amount (default: 0.1 BTC)

### 4. ₿ [bitcoin_staking_example.py](bitcoin_staking_example.py)
**Purpose**: Bitcoin staking integration demo
**Features**:
- Bitcoin staking with CLTV timelock
- Dual staking setup
- Reward calculations
- Staking tier management
- Economics visualization

**Usage**:
```bash
python bitcoin_staking_example.py
```

**Staking Tiers**:
1. **Base (1.0x)**: CORE tokens only
2. **Boost (1.25x)**: CORE + 0.01 BTC minimum
3. **Super (1.5x)**: CORE + 0.1 BTC minimum
4. **Satoshi (2.0x)**: CORE + 1.0 BTC minimum

### 5. 🎯 [advanced_usage.py](advanced_usage.py)
**Purpose**: Advanced features for experienced users
**Features**:
- Multi-account batch operations
- Subnet creation and management
- Network performance monitoring
- Staking strategy optimization
- Automated operations setup
- Complete network deployment

**Usage**:
```bash
python advanced_usage.py
```

**Advanced Features**:
1. Multi-account batch operations
2. Subnet creation and management
3. Dual staking network setup
4. Network performance monitoring
5. Staking strategy optimization
6. Advanced reward claiming
7. Automated operations setup
8. Complete network deployment

## Bitcoin Staking Integration

### How It Works

1. **Self-Custodial**: You maintain control of your Bitcoin
2. **CLTV Timelock**: Bitcoin is locked for a specified period
3. **Dual Rewards**: Earn both CORE and Bitcoin rewards
4. **No Slashing**: Bitcoin staking has no slashing risk

### Staking Tiers & Rewards

| Tier | Multiplier | CORE Required | BTC Required | Lock Time |
|------|------------|---------------|--------------|-----------|
| Base | 1.0x | ✅ | ❌ | None |
| Boost | 1.25x | ✅ | 0.01 BTC | 30 days |
| Super | 1.5x | ✅ | 0.1 BTC | 60 days |
| Satoshi | 2.0x | ✅ | 1.0 BTC | 90 days |

### Revenue Streams

1. **AI Training Rewards**: CORE tokens for model training
2. **Bitcoin Staking Rewards**: BTC rewards for Bitcoin staking
3. **Network Fees**: CORE tokens from network transactions
4. **Validator Rewards**: CORE tokens for validation services

## Network Configuration

### Core Blockchain Networks

**Testnet**:
- Network: Core Testnet
- Chain ID: 1115
- RPC URL: https://rpc.test.btcs.network
- Explorer: https://scan.test.btcs.network
- Faucet: https://scan.test.btcs.network/faucet

**Mainnet**:
- Network: Core Mainnet
- Chain ID: 1116
- RPC URL: https://rpc.coredao.org
- Explorer: https://scan.coredao.org

### Getting Started

1. **Install Dependencies**:
```bash
pip install -r requirements.txt
```

2. **Create Account**:
```bash
python create_account.py
```

3. **Get Testnet Tokens**:
   - Visit: https://scan.test.btcs.network/faucet
   - Get CORE tokens and ETH for gas

4. **Run Quickstart**:
```bash
python quickstart.py
```

5. **Register as Miner**:
```bash
python register_miner.py --account myaccount --api http://localhost:8080
```

## Configuration Files

### Account Storage
- Location: `./wallets/`
- Format: Encrypted JSON files
- Naming: `{account_name}.json`

### Settings
- File: `../config/settings.py`
- Contains network endpoints, contract addresses, and configuration

### Automation
- Script: `./wallets/automation_script.sh`
- Config: `./wallets/automation_config.json`
- Features: Auto-claiming, monitoring, optimization

## Security Best Practices

1. **Private Key Management**:
   - Never share private keys
   - Use encrypted storage
   - Backup your keys securely

2. **Bitcoin Staking**:
   - Understand timelock mechanics
   - Only stake what you can afford to lock
   - Monitor unlock times

3. **Network Security**:
   - Use testnet for development
   - Verify contract addresses
   - Monitor transactions

## Troubleshooting

### Common Issues

1. **Account Not Found**:
   - Run `create_account.py` first
   - Check account name spelling
   - Verify wallet directory

2. **Insufficient Balance**:
   - Get testnet tokens from faucet
   - Check both CORE and ETH balances
   - Monitor gas fees

3. **Transaction Failures**:
   - Check network connection
   - Verify contract addresses
   - Ensure sufficient gas

### Getting Help

- **Documentation**: `../README_CORE.md`
- **Core Network**: https://coredao.org
- **Discord**: [Join Community]
- **GitHub**: [Submit Issues]

## Example Workflows

### Basic Miner Setup
```bash
# 1. Create account
python create_account.py

# 2. Quick setup
python quickstart.py

# 3. Register miner
python register_miner.py --account miner1 --api http://localhost:8080
```

### Bitcoin Staking Setup
```bash
# 1. Create account
python create_account.py

# 2. Setup Bitcoin staking
python bitcoin_staking_example.py

# 3. Register with Bitcoin staking
python register_miner.py --account miner1 --api http://localhost:8080 --bitcoin-staking --tier boost
```

### Advanced Network Setup
```bash
# 1. Multi-account setup
python advanced_usage.py

# 2. Create subnet
python advanced_usage.py

# 3. Deploy network
python advanced_usage.py
```

## Contributing

1. Fork the repository
2. Create feature branch
3. Add comprehensive examples
4. Test thoroughly
5. Submit pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Note**: This is a migration from Aptos to Core blockchain. All examples have been updated to use Core's EVM-compatible environment with Bitcoin staking integration.
