require("@nomiclabs/hardhat-waffle");
require("@nomiclabs/hardhat-ethers");
require("dotenv").config();

const PRIVATE_KEY = process.env.PRIVATE_KEY || "0x0000000000000000000000000000000000000000000000000000000000000000";
const CORE_TESTNET_RPC = process.env.CORE_TESTNET_RPC || "https://rpc.test.btcs.network";
const CORE_MAINNET_RPC = process.env.CORE_MAINNET_RPC || "https://rpc.coredao.org";

module.exports = {
  defaultNetwork: "hardhat",
  
  networks: {
    hardhat: {
      chainId: 31337,
    },
    core_testnet: {
      url: CORE_TESTNET_RPC,
      accounts: [PRIVATE_KEY],
      chainId: 1115,
      gasPrice: 40000000000,
      gas: 8000000,
    },
    core_mainnet: {
      url: CORE_MAINNET_RPC,
      accounts: [PRIVATE_KEY],
      chainId: 1116,
      gasPrice: 40000000000,
      gas: 8000000,
    },
  },
  
  solidity: {
    version: "0.8.19",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
      viaIR: true,
    },
  },

  paths: {
    sources: "./contracts",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts",
  },
  
  mocha: {
    timeout: 20000,
  },
};
