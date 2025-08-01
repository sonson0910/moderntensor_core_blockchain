# Moderntensor Tokenomic

## Overview

The **Moderntensor Token Project** is a decentralized system ported from **Aptos** to **Core DAO**, an EVM-compatible Layer-1 blockchain.
It implements a token distribution algorithm for the `MTNSRTEST01` token, featuring:

* **Vesting**
* **Periodic reward emission with halving**
* **Governance**
* **Treasury management**

Smart contracts are written in **Solidity** using **OpenZeppelin** for security and ERC-20 compliance.

---

## 🔑 Key Features

* **MTNSRTEST01 Token**: ERC-20 token with minting, burning, and freezing capabilities.
* **Vesting**: Linear token vesting for fair distribution.
* **Reward Emission**: \~850,340 tokens every \~5 days, with halving every \~4 years.
* **Governance**: Token-based proposal and voting system.
* **Treasury**: Secure vault for storing and managing tokens.

---

## 📁 Project Structure

```
project/
├── contracts/
│   ├── MTNSRTEST01.sol       # ERC-20 token contract
│   ├── Vesting.sol           # Token vesting contract
│   ├── RewardEmission.sol    # Reward distribution contract
│   ├── Governance.sol        # Governance and voting contract
│   ├── Treasury.sol          # Treasury management contract
├── scripts/
│   ├── automate.js             # Deployment script for Core DAO
│   ├── createWallet.js             # Deployment script for Core DAO
│   ├── deploy.js             # Deployment script for Core DAO
│   ├── interact.js             # Deployment script for Core DAO
├── contracts/
│   ├── MTNSRTEST01.test.js       # ERC-20 token contract testing
│   ├── Vesting.test.js           # Token vesting contract testing
│   ├── RewardEmission.test.js    # Reward distribution contract testing
│   ├── Governance.test.js        # Governance and voting contract testing
│   ├── Treasury.test.js          # Treasury management contract testing
├── wallets.txt                 # This store wallet test
├── hardhat.config.js         # Hardhat configuration
├── package.json              # Project dependencies
├── README.md                 # This file
```

---

## 📜 Smart Contracts

### 1. `MTNSRTEST01.sol`

* **Purpose**: ERC-20 token with 8 decimals and 1 billion initial supply.
* **Features**:

  * Minting (owner-only)
  * Burning
  * Freezing/unfreezing accounts (owner-only)

### 2. `Vesting.sol`

* **Purpose**: Linear vesting for scheduled distribution.
* **Features**:

  * Vesting initialization with deposits
  * Schedule setup for recipients
  * Release tokens over time
  * Top-up vesting pool

### 3. `RewardEmission.sol`

* **Purpose**: Periodic token emission with halving logic.
* **Features**:

  * Emission every \~5 days
  * Halving every \~4 years
  * Epoch pool logic and parameter updates

### 4. `Governance.sol`

* **Purpose**: Decentralized proposal and voting system.
* **Features**:

  * Create and vote on proposals
  * Vote using token balances
  * Execute proposals (owner-only)

### 5. `Treasury.sol`

* **Purpose**: Secure token vault.
* **Features**:

  * Deposit and withdrawal management (owner-only)

---

## 🛠 Prerequisites

* Node.js: `v16.x` or higher
* Hardhat
* MetaMask
* Core DAO RPC (e.g., `https://rpc.coredao.org`)
* CORE tokens for gas (Chain ID: `1116`)

---

## 📦 Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd moderntensor-core-dao
```

### 2. Install Dependencies

```bash
npm install
```

### 3. Install Hardhat & OpenZeppelin

```bash
npm install --save-dev hardhat
npm install @openzeppelin/contracts
npm install --save-dev hardhat @nomicfoundation/hardhat-toolbox @openzeppelin/hardhat-upgrades dotenv
```

### 4. Configure Hardhat (`hardhat.config.js`)

```javascript
module.exports = {
  solidity: "0.8.20",
  networks: {
    coredao: {
      url: "https://rpc.coredao.org",
      accounts: ["YOUR_PRIVATE_KEY"]
    }
  }
};
```

---

## 🚀 Deployment

### Compile Smart Contracts

```bash
npx hardhat compile
```

### Deploy to Core DAO

Ensure your wallet has CORE tokens for gas. Then:

```bash
npx hardhat run scripts/deploy.js --network coredao
```

### Token Distribution Summary

* `MTNSRTEST01`: 1B tokens
* `Vesting`: 400M
* `RewardEmission`: 400M
* `Treasury`: 200M

### Verify Contracts (Optional)

```bash
npx hardhat verify --network coredao <CONTRACT_ADDRESS> <CONSTRUCTOR_ARGS>
```

---

## 🧪 Usage

### MetaMask Setup

* **Network Name**: Core DAO Mainnet
* **RPC URL**: `https://rpc.coredao.org`
* **Chain ID**: `1116`
* **Symbol**: CORE

Add the `MTNSRTEST01` token using deployed contract address.

### Token Management

* Mint / Burn / Freeze accounts using `MTNSRTEST01` contract (owner-only)

### Vesting

* Deposit tokens
* Schedule and release vesting

### Reward Emission

* Deposit to vault
* Trigger periodic emissions

### Governance

* Propose and vote using token balances
* Execute (owner-only)

### Treasury

* Deposit and withdraw securely (owner-only)

---

## 🌐 Ecosystem Integration

* **Liquidity**: Add MTNSRTEST01/CORE pair on ArcherSwap or CoreSwap
* **Cross-Chain**: Use Core Bridge
* **Explorer**: Track activity on [Core DAO Explorer](https://scan.coredao.org)

---

## 🧪 Testing

### Testnet Deployment

```bash
npx hardhat run scripts/deploy.js --network coredao_testnet
```

### Local Testing

* Write test cases in `test/` folder

```bash
npx hardhat test
```

---

## 🔒 Security Considerations

* **Audits**: Use Slither, Mythril before mainnet deployment
* **Access Control**: Owner-only functions; consider multisig
* **Gas Optimization**: Especially for loops and storage
* **Token Migration**: Core DAO migration logic

---

## 📬 Contact

Contact the Moderntensor team via **\[your contact details or website]**.


