# ModernTensor Core Blockchain Integration Guide 🌟

Detailed guide for integrating ModernTensor with Core blockchain and Bitcoin staking.

## ✅ Migration Status - 100% COMPLETE

ModernTensor has been fully migrated from Aptos to Core blockchain with all features:

### 🔧 **Completed:**
- ✅ **Smart Contract Migration**: Converted from Move to Solidity
- ✅ **Hardhat Setup**: Deployment configuration for Core testnet/mainnet
- ✅ **Bitcoin Staking Integration**: Bitcoin staking integration with CLTV
- ✅ **Dual Staking Tiers**: 4-tier system (Base, Boost, Super, Satoshi)
- ✅ **Web3 Client**: ModernTensorCoreClient for blockchain interactions
- ✅ **Examples Migration**: All examples updated
- ✅ **Consensus Module**: ValidatorNodeConsensus fully migrated
- ✅ **Core Client**: All Aptos client references replaced
- ✅ **Code Cleanup**: All Aptos SDK imports cleaned up
- ✅ **Testing Suite**: Comprehensive test coverage
- ✅ **Documentation**: Detailed guides and API references

### 🎯 **Core Blockchain Features:**
- **EVM-Compatible**: Full Solidity smart contract support
- **Bitcoin Staking**: Self-custodial Bitcoin staking with CLTV
- **High Performance**: ~5,000 TPS with gas fees < $0.01
- **Security**: Backed by Bitcoin's hash power
- **No Slashing**: Bitcoin staking has no validator slashing risk

### 🧹 **Code Migration Details:**
- **validator_node_core.py**: ✅ Migrated to Web3/Core blockchain
- **validator_node_consensus.py**: ✅ Migrated to Core blockchain transactions
- **consensus/state.py**: ✅ Updated to use ModernTensorCoreClient
- **network/app/main.py**: ✅ Updated imports for Core blockchain
- **API endpoints**: ✅ Updated for Web3 compatibility
- **Legacy modules**: ✅ Aptos SDK imports commented out/replaced

**🎉 Migration Status: 100% COMPLETE - Ready for Core blockchain deployment!**

## 📖 Overview

ModernTensor Core is the first decentralized AI training platform that combines Bitcoin staking with machine learning. Using Core blockchain as the execution layer with Bitcoin staking integration to create a sustainable ecosystem.

## 🏗️ Core Blockchain Architecture

### Core Blockchain Features
- **EVM-Compatible**: Full Solidity smart contract support
- **Bitcoin Staking**: Self-custodial Bitcoin staking with CLTV
- **Dual Consensus**: Delegated Proof of Stake + Proof of Work  
- **High Performance**: ~5000 TPS with gas fees < $0.01
- **Security**: Backed by Bitcoin's hash power

### Bitcoin Staking Mechanism
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Bitcoin TX    │    │  Core Validator  │    │  ModernTensor   │
│  (Timelock)     │───▶│   (Delegation)   │───▶│   (AI Rewards)  │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🔧 Environment Setup

### 1. Core Blockchain Development

```bash
# Install development dependencies
npm install -g hardhat
npm install @openzeppelin/contracts web3 ethers

# Install Python dependencies
pip install web3 eth-account bitcoin bitcoinlib
```

### 2. Network Configuration

```javascript
// hardhat.config.js
module.exports = {
  networks: {
    "core-testnet": {
      url: "https://rpc.test.btcs.network",
      accounts: [process.env.PRIVATE_KEY],
      chainId: 1115,
    },
    "core-mainnet": {
      url: "https://rpc.coredao.org", 
      accounts: [process.env.PRIVATE_KEY],
      chainId: 1116,
    }
  }
};
```

### 3. Environment Variables

```bash
# .env file
CORE_NODE_URL=https://rpc.test.btcs.network
CORE_CONTRACT_ADDRESS=0x...
CORE_TOKEN_ADDRESS=0x40375C92d9FAf44d2f9db9Bd9ba41a3317a2404f
BITCOIN_RPC_URL=https://bitcoin-rpc.com
PRIVATE_KEY=0x...
```

## 💎 Smart Contract Architecture

### ModernTensor.sol Features

```solidity
contract ModernTensor {
    // Dual staking integration
    mapping(address => uint256) public coreStake;
    mapping(address => uint256) public bitcoinStake;
    
    // Staking tiers with multipliers
    struct StakingTier {
        uint256 minCoreRatio;  // CORE:Bitcoin ratio
        uint256 multiplier;    // Reward multiplier
        string name;           // Tier name
    }
    
    // Bitcoin staking verification
    mapping(bytes32 => BitcoinStake) public bitcoinStakes;
    
    struct BitcoinStake {
        uint256 amount;      // Amount in satoshis
        uint256 lockTime;    // CLTV lock time
        bool verified;       // Verification status
    }
}
```

### Key Functions

#### Miner Registration with Dual Staking
```solidity
function registerMiner(
    bytes32 uid,
    uint64 subnetUid, 
    uint256 stakeAmount,  // CORE tokens
    string calldata apiEndpoint
) external payable;
```

#### Bitcoin Staking Integration
```solidity
function stakeBitcoin(
    bytes32 txHash,       // Bitcoin transaction hash
    uint256 amount,       // Amount in satoshis
    uint256 lockTime      // CLTV lock time
) external;
```

#### Staking Tier Calculation
```solidity
function calculateStakingTier(address user) 
    public view returns (uint256) {
    
    uint256 ratio = (coreStake[user] * 1000) / bitcoinStake[user];
    
    // Tier 0: Base (1x) - CORE only
    // Tier 1: Boost (1.25x) - CORE:Bitcoin ≥ 1:10
    // Tier 2: Super (1.5x) - CORE:Bitcoin ≥ 1:2  
    // Tier 3: Satoshi (2x) - CORE:Bitcoin ≥ 1:1
}
```

## ₿ Bitcoin Staking Implementation

### Self-Custodial Bitcoin Staking

```python
from bitcoinlib import BitcoinLib
from moderntensor.mt_core.staking import BitcoinStaking

class BitcoinStaking:
    def create_timelock_transaction(
        self,
        amount: float,  # BTC amount
        lock_time_hours: int,
        core_validator_address: str
    ) -> BitcoinTransaction:
        """
        Create Bitcoin transaction with CLTV timelock
        """
        lock_time = int(time.time()) + (lock_time_hours * 3600)
        
        # Create CLTV script
        script = Script([
            lock_time,
            OP_CHECKLOCKTIMEVERIFY,
            OP_DROP,
            OP_DUP,
            OP_HASH160,
            hash160(core_validator_address),
            OP_EQUALVERIFY,
            OP_CHECKSIG
        ])
        
        return self.create_transaction(amount, script)
```

### Bitcoin Transaction Verification

```python
def verify_bitcoin_transaction(
    self, 
    tx_hash: str,
    expected_amount: int,
    expected_lock_time: int
) -> bool:
    """
    Verify Bitcoin transaction on-chain
    """
    tx = self.bitcoin_client.get_transaction(tx_hash)
    
    # Verify amount and lock time
    if tx.amount != expected_amount:
        return False
        
    if tx.lock_time != expected_lock_time:
        return False
        
    # Verify CLTV script
    return self.verify_cltv_script(tx.script)
```

## 🎯 Dual Staking Economics

### Staking Tiers & Multipliers

| Tier | Name | CORE:Bitcoin Ratio | Multiplier | APY Boost |
|------|------|-------------------|------------|-----------|
| 0 | Base | CORE only | 1.0x | 3-5% |
| 1 | Boost | ≥ 1:10 | 1.25x | 4-6% |
| 2 | Super | ≥ 1:2 | 1.5x | 5-8% |
| 3 | Satoshi | ≥ 1:1 | 2.0x | 6-10% |

### Revenue Streams

```python
def calculate_total_rewards(user_address: str) -> dict:
    """
    Calculate total rewards from all sources
    """
    tier = client.calculate_staking_tier(user_address)
    multiplier = TIER_MULTIPLIERS[tier]
    
    rewards = {
        'bitcoin_staking': base_bitcoin_yield * multiplier,
        'ai_training_fees': ai_training_rewards * multiplier,
        'validation_rewards': consensus_rewards * multiplier,
        'dual_staking_bonus': bonus_rewards * (multiplier - 1.0)
    }
    
    return rewards
```

## 🚀 Deployment Guide

### 1. Compile Smart Contracts

```bash
cd contracts
npx hardhat compile
```

### 2. Deploy to Core Testnet

```bash
# Deploy with verification
npx hardhat run scripts/deploy.js --network core-testnet

# Verify on CoreScan
npx hardhat verify --network core-testnet <CONTRACT_ADDRESS> "<CORE_TOKEN_ADDRESS>"
```

### 3. Initialize Default Subnet

```javascript
// scripts/initialize.js
const modernTensor = await ethers.getContractAt("ModernTensor", contractAddress);

await modernTensor.createSubnet(
    1,  // subnet ID
    "AI Training Subnet",
    "Default subnet for AI model training",
    1000,  // max miners
    100,   // max validators
    86400, // immunity period (24h)
    ethers.utils.parseEther("10"),  // min miner stake
    ethers.utils.parseEther("50"),  // min validator stake
    ethers.utils.parseEther("1")    // registration cost
);
```

### 4. Register Miners & Validators

```python
# Register miner with dual staking
tx_hash = client.register_miner(
    uid=os.urandom(32),
    subnet_uid=1,
    stake_amount=10 * 10**18,  # 10 CORE
    api_endpoint="https://my-miner.com/api"
)

# Stake Bitcoin for enhanced rewards
bitcoin_tx = client.stake_bitcoin(
    tx_hash=bitcoin_transaction_hash,
    amount=100_000_000,  # 1 BTC in satoshis
    lock_time=int(time.time()) + 86400
)
```

## 📊 Monitoring & Analytics

### Network Statistics

```python
def get_network_stats():
    """Get comprehensive network statistics"""
    return {
        'total_miners': client.totalMiners(),
        'total_validators': client.totalValidators(), 
        'total_core_staked': get_total_core_staked(),
        'total_bitcoin_staked': get_total_bitcoin_staked(),
        'average_tier': calculate_average_tier(),
        'network_hashrate': get_bitcoin_hashrate(),
        'ai_tasks_completed': get_completed_tasks()
    }
```

### Performance Tracking

```python
def track_miner_performance(miner_address: str):
    """Track individual miner performance"""
    info = client.get_miner_info(miner_address)
    
    metrics = {
        'performance_score': info['last_performance'] / 1_000_000,
        'trust_score': info['trust_score'] / 1_000_000,
        'total_rewards': info['accumulated_rewards'],
        'staking_tier': client.calculate_staking_tier(miner_address),
        'uptime': calculate_uptime(miner_address),
        'ai_tasks_completed': get_tasks_completed(miner_address)
    }
    
    return metrics
```

## 🔒 Security Considerations

### Bitcoin Staking Security

1. **Self-Custodial**: Users maintain control of Bitcoin
2. **CLTV Protection**: Time-locked transactions prevent early withdrawal
3. **Multi-Sig Support**: Optional multi-signature validation
4. **Fraud Detection**: On-chain verification of Bitcoin transactions

### Smart Contract Security

```solidity
// Reentrancy protection
modifier nonReentrant() {
    require(_status != _ENTERED, "ReentrancyGuard: reentrant call");
    _status = _ENTERED;
    _;
    _status = _NOT_ENTERED;
}

// Access control
modifier onlyValidator() {
    require(validators[msg.sender].status == STATUS_ACTIVE, 
            "Not an active validator");
    _;
}
```

## 🧪 Testing Framework

### Unit Tests

```javascript
// test/ModernTensor.test.js
describe("ModernTensor", function () {
    it("Should register miner with dual staking", async function () {
        await modernTensor.registerMiner(
            uid, subnetUid, stakeAmount, apiEndpoint
        );
        
        const minerInfo = await modernTensor.getMinerInfo(miner.address);
        expect(minerInfo.stake).to.equal(stakeAmount);
    });
    
    it("Should calculate staking tier correctly", async function () {
        await modernTensor.stakeBitcoin(txHash, bitcoinAmount, lockTime);
        
        const tier = await modernTensor.calculateStakingTier(user.address);
        expect(tier).to.equal(expectedTier);
    });
});
```

### Integration Tests

```python
# tests/test_integration.py
def test_full_staking_flow():
    """Test complete dual staking workflow"""
    
    # 1. Register miner
    tx_hash = client.register_miner(...)
    assert tx_hash is not None
    
    # 2. Stake Bitcoin
    bitcoin_tx = stake_bitcoin(...)
    assert bitcoin_tx['status'] == 'confirmed'
    
    # 3. Verify tier calculation
    tier = client.calculate_staking_tier(address)
    assert tier >= 1  # Should get boost tier
    
    # 4. Check rewards multiplier
    rewards = calculate_rewards(address)
    assert rewards['multiplier'] > 1.0
```

## 🎯 Performance Optimizations

### Gas Optimization

```solidity
// Batch operations to reduce gas costs
function batchUpdateScores(
    address[] calldata miners,
    uint256[] calldata performances,
    uint256[] calldata trustScores
) external onlyValidator {
    require(miners.length == performances.length, "Array length mismatch");
    
    for (uint i = 0; i < miners.length; i++) {
        _updateMinerScore(miners[i], performances[i], trustScores[i]);
    }
}
```

### Caching Strategies

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_miner_info(address: str) -> dict:
    """Cache miner info to reduce RPC calls"""
    return client.get_miner_info(address)

@lru_cache(maxsize=100)  
def get_cached_staking_tier(address: str) -> int:
    """Cache staking tier calculations"""
    return client.calculate_staking_tier(address)
```

## 🔮 Future Enhancements

### lstBTC Integration
- Liquid staking Bitcoin through institutional custodians
- Enhanced yield strategies with DeFi protocols
- Cross-chain Bitcoin wrapped tokens

### Advanced Mining Features
- GPU compute verification on-chain
- Specialized AI model training tasks
- Zero-knowledge proof integration

### Governance & DAO
- Decentralized parameter updates
- Community-driven subnet creation
- Revenue sharing mechanisms

---

**ModernTensor Core - Pioneering Bitcoin-Powered AI Training** 🚀₿🧠 