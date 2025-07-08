require("@nomiclabs/hardhat-waffle");
require("@nomiclabs/hardhat-ethers");
require("@nomiclabs/hardhat-etherscan");
require("hardhat-deploy");
require("hardhat-gas-reporter");
require("solidity-coverage");
require("dotenv").config();

const PRIVATE_KEY = process.env.PRIVATE_KEY || "0x0000000000000000000000000000000000000000000000000000000000000000";
const CORE_TESTNET_RPC = process.env.CORE_TESTNET_RPC || "https://rpc.test.btcs.network";
const CORE_MAINNET_RPC = process.env.CORE_MAINNET_RPC || "https://rpc.coredao.org";
const ETHERSCAN_API_KEY = process.env.ETHERSCAN_API_KEY || "";

module.exports = {
  defaultNetwork: "hardhat",
  networks: {
    hardhat: {
      chainId: 31337,
      accounts: {
        count: 20,
        initialIndex: 0,
        mnemonic: "test test test test test test test test test test test junk",
        path: "m/44'/60'/0'/0",
        accountsBalance: "10000000000000000000000", // 10,000 ETH
      },
    },
    core_testnet: {
      url: CORE_TESTNET_RPC,
      accounts: [PRIVATE_KEY],
      chainId: 1115,
      gasPrice: 20000000000, // 20 gwei
      gas: 6000000,
      timeout: 60000,
    },
    core_mainnet: {
      url: CORE_MAINNET_RPC,
      accounts: [PRIVATE_KEY],
      chainId: 1116,
      gasPrice: 20000000000, // 20 gwei
      gas: 6000000,
      timeout: 60000,
    },
  },
  solidity: {
    version: "0.8.19",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
    },
  },
  namedAccounts: {
    deployer: {
      default: 0,
    },
    user1: {
      default: 1,
    },
    user2: {
      default: 2,
    },
  },
  etherscan: {
    apiKey: {
      core_testnet: ETHERSCAN_API_KEY,
      core_mainnet: ETHERSCAN_API_KEY,
    },
    customChains: [
      {
        network: "core_testnet",
        chainId: 1115,
        urls: {
          apiURL: "https://api.test.btcs.network/api",
          browserURL: "https://scan.test.btcs.network",
        },
      },
      {
        network: "core_mainnet",
        chainId: 1116,
        urls: {
          apiURL: "https://openapi.coredao.org/api",
          browserURL: "https://scan.coredao.org",
        },
      },
    ],
  },
  gasReporter: {
    enabled: process.env.REPORT_GAS !== undefined,
    currency: "USD",
    gasPrice: 20,
    coinmarketcap: process.env.COINMARKETCAP_API_KEY,
  },
  paths: {
    artifacts: "./artifacts",
    cache: "./cache",
    sources: "./contracts",
    tests: "./test",
    deploy: "./deploy",
  },
  mocha: {
    timeout: 40000,
  },
}; 