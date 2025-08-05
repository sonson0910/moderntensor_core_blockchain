# ModernTensor Smart Contracts

This directory contains the Solidity smart contracts for ModernTensor on Core blockchain, featuring Bitcoin staking integration and dual staking economics.

## 📁 Directory Structure

```
smartcontract/
├── contracts/
│   ├── ModernTensor.sol      # Main contract with Bitcoin staking
│   └── MockCoreToken.sol     # Mock CORE token for testing
├── deploy/
│   └── 01_deploy_moderntensor.js  # Deployment script
├── test/
│   └── ModernTensor.test.js  # Comprehensive test suite
├── hardhat.config.js         # Hardhat configuration
├── package.json             # Dependencies and scripts
└── README.md               # This file
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd smartcontract
npm install
```

### 2. Set Environment Variables

Create a `.env` file:

```bash
# Private key for deployment (DO NOT commit real private keys)
PRIVATE_KEY=0x0000000000000000000000000000000000000000000000000000000000000000

# Core blockchain RPC endpoints
CORE_TESTNET_RPC=https://rpc.test2.btcs.network
CORE_MAINNET_RPC=https://rpc.test2.btcs.network

# Etherscan API key for contract verification
ETHERSCAN_API_KEY=your_etherscan_api_key_here
```

### 3. Compile Contracts

```bash
npm run compile
```

### 4. Run Tests

```bash
npm test
```

### 5. Deploy to Local Network

```bash
# Start local hardhat node
npm run node

# Deploy to local network (in another terminal)
npm run deploy:local
```

### 6. Deploy to Testnet

```bash
npm run deploy:testnet
```

### 7. Deploy to Mainnet

```bash
npm run deploy:mainnet
```

## 🏗️ Contract Architecture

### ModernTensor.sol

The main contract implementing:

- **Miner Registration**: Register miners with CORE token staking
- **Validator Registration**: Register validators with higher stake requirements
- **Bitcoin Staking**: Self-custodial Bitcoin staking with CLTV timelock
- **Dual Staking Tiers**: Four-tier reward system
- **Subnet Management**: Create and manage AI training subnets
- **Score Updates**: Performance and trust score management

### Staking Tiers

| Tier | Name | Threshold | Multiplier |
|------|------|-----------|------------|
| 0 | Base | 0+ CORE | 1.0x |
| 1 | Boost | 1,000+ CORE | 1.25x |
| 2 | Super | 10,000+ CORE | 1.5x |
| 3 | Satoshi | 50,000+ CORE | 2.0x |

### Key Features

- **Bitcoin Integration**: Stake Bitcoin alongside CORE tokens
- **No Slashing**: Bitcoin staking without validator slashing risk
- **EVM Compatible**: Full Solidity smart contract support
- **High Performance**: Optimized for Core blockchain's ~5000 TPS
- **Security**: OpenZeppelin contracts with comprehensive testing

## 📊 Contract Functions

### Miner Functions

```solidity
function registerMiner(
    bytes32 uid,
    uint64 subnetUid,
    uint256 stakeAmount,
    string memory apiEndpoint
) external payable nonReentrant
```

### Validator Functions

```solidity
function registerValidator(
    bytes32 uid,
    uint64 subnetUid,
    uint256 stakeAmount,
    string memory apiEndpoint
) external nonReentrant
```

### Bitcoin Staking

```solidity
function stakeBitcoin(
    bytes32 txHash,
    uint256 amount,
    uint256 lockTime
) external
```

### View Functions

```solidity
function getMinerInfo(address minerAddr) external view returns (MinerInfo memory)
function getValidatorInfo(address validatorAddr) external view returns (ValidatorInfo memory)
function calculateStakingTier(address user) external view returns (uint256)
function getAllMiners() external view returns (address[] memory)
function getAllValidators() external view returns (address[] memory)
```

## 🧪 Testing

The test suite covers:

- Contract deployment and initialization
- Miner and validator registration
- Bitcoin staking functionality
- Staking tier calculations
- Score updates and events
- Access control and security

Run tests with:

```bash
npm test
```

For gas reporting:

```bash
npm run gas-report
```

For coverage:

```bash
npm run coverage
```

## 🌐 Network Configuration

### Core Testnet
- **Chain ID**: 1115
- **RPC**: https://rpc.test2.btcs.network
- **Explorer**: https://scan.test.btcs.network
- **Gas Price**: 20 gwei

### Core Mainnet
- **Chain ID**: 1116
- **RPC**: https://rpc.test2.btcs.network
- **Explorer**: https://scan.coredao.org
- **Gas Price**: 20 gwei

## 📋 Deployment Checklist

### Pre-deployment
- [ ] Set up environment variables
- [ ] Compile contracts successfully
- [ ] Run comprehensive tests
- [ ] Verify gas optimizations
- [ ] Review security considerations

### Post-deployment
- [ ] Verify contract on explorer
- [ ] Test contract interactions
- [ ] Set up monitoring
- [ ] Update client configurations
- [ ] Document contract addresses

## 🔐 Security Considerations

### Smart Contract Security
- Uses OpenZeppelin battle-tested contracts
- Implements ReentrancyGuard for protection
- Comprehensive input validation
- Owner-only functions for critical operations

### Bitcoin Staking Security
- CLTV timelock prevents premature withdrawal
- Transaction hash verification
- No private key custody required
- Trustless verification process

### Access Control
- Owner-only functions for score updates
- Miner/validator registration restrictions
- Emergency pause capabilities
- Role-based permissions

## 🔧 Development Scripts

```bash
# Compile contracts
npm run compile

# Run tests
npm test

# Deploy to local network
npm run deploy:local

# Deploy to testnet
npm run deploy:testnet

# Deploy to mainnet
npm run deploy:mainnet

# Verify contracts
npm run verify:testnet
npm run verify:mainnet

# Start local node
npm run node

# Clean artifacts
npm run clean

# Generate coverage report
npm run coverage

# Check contract sizes
npm run size

# Flatten contracts
npm run flatten
```

## 📈 Gas Optimization

The contracts are optimized for:
- Efficient storage packing
- Minimal external calls
- Batch operations where possible
- OpenZeppelin's gas-efficient implementations

## 🐛 Troubleshooting

### Common Issues

1. **Compilation Errors**
   - Ensure Node.js version >= 16
   - Run `npm install` to update dependencies

2. **Deployment Failures**
   - Check network configuration
   - Verify private key and gas settings
   - Ensure sufficient balance for deployment

3. **Test Failures**
   - Run `npm run clean` and recompile
   - Check Hardhat network configuration
   - Verify mock token setup

### Support

For technical support:
- Check the main [ModernTensor documentation](../README_CORE.md)
- Review test files for usage examples
- Consult Core blockchain documentation

## 🔄 Upgrade Path

For contract upgrades:
1. Use proxy patterns for upgradeable contracts
2. Implement proper migration scripts
3. Test thoroughly on testnet before mainnet
4. Consider governance mechanisms for upgrades

## 📚 Additional Resources

- [Core Blockchain Documentation](https://docs.coredao.org/)
- [OpenZeppelin Contracts](https://docs.openzeppelin.com/contracts/)
- [Hardhat Documentation](https://hardhat.org/docs)
- [Solidity Documentation](https://docs.soliditylang.org/) 