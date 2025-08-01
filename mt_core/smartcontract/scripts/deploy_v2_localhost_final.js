const { ethers } = require("hardhat");
require("dotenv").config();

async function main() {
    console.log("🚀 DEPLOYING ModernTensorAI v2.0 - Localhost Edition");
    console.log("============================================================");
    
    try {
        const [deployer] = await ethers.getSigners();
        console.log("📝 Deploying with account:", deployer.address);
        
        const balance = await ethers.provider.getBalance(deployer.address);
        console.log("💰 Account balance:", ethers.utils.formatEther(balance), "CORE");
        
        if (balance.lt(ethers.utils.parseEther("0.1"))) {
            console.log("❌ Insufficient balance for deployment");
            return;
        }

        // Deploy Mock Tokens for Testnet
        console.log("\n🪙 Deploying Mock CORE Token...");
        const MockCoreToken = await ethers.getContractFactory("MockCoreToken");
        const coreToken = await MockCoreToken.deploy("Mock CORE Token", "MCORE");
        await coreToken.deployed();
        const coreTokenAddress = coreToken.address;
        console.log("✅ Mock CORE Token deployed to:", coreTokenAddress);

        console.log("\n🟠 Deploying Mock BTC Token...");
        const btcToken = await MockCoreToken.deploy("Mock Bitcoin Token", "MBTC");
        await btcToken.deployed();
        const btcTokenAddress = btcToken.address;
        console.log("✅ Mock BTC Token deployed to:", btcTokenAddress);

        // Deploy ModernTensorAI v2.0 Contract
        console.log("\n🧠 Deploying ModernTensorAI v2.0 Contract...");
        const ModernTensorAI = await ethers.getContractFactory("ModernTensorAI_v2_Bittensor");
        
        // Ultra-low stake requirements for testnet
        const minMinerStake = ethers.utils.parseEther("0.05");    // 0.05 CORE
        const minValidatorStake = ethers.utils.parseEther("0.08"); // 0.08 CORE
        
        console.log(`📊 Min Miner Stake: ${ethers.utils.formatEther(minMinerStake)} CORE`);
        console.log(`📊 Min Validator Stake: ${ethers.utils.formatEther(minValidatorStake)} CORE`);
        
        const modernTensorAI = await ModernTensorAI.deploy(
            coreTokenAddress,
            btcTokenAddress,
            minMinerStake,
            minValidatorStake
        );
        
        await modernTensorAI.deployed();
        const contractAddress = modernTensorAI.address;
        
        console.log("\n🎉 SUCCESS! ModernTensorAI v2.0 deployed to:", contractAddress);
        
        // Log all important addresses
        console.log("\n📋 CONTRACT SUMMARY:");
        console.log("===================");
        console.log("🧠 ModernTensorAI v2.0:", contractAddress);
        console.log("🪙 CORE Token:", coreTokenAddress);
        console.log("🟠 BTC Token:", btcTokenAddress);
        console.log("⛽ Gas Price:", (await ethers.provider.getGasPrice()).toString());
        
        // Update .env file with new addresses
        const fs = require('fs');
        const envContent = `# CORE TESTNET CONFIGURATION
PRIVATE_KEY=${process.env.PRIVATE_KEY}
CORE_TESTNET_RPC=https://rpc.test.btcs.network
CORE_MAINNET_RPC=https://rpc.coredao.org
GAS_PRICE=20000000000
GAS_LIMIT=8000000

# CONTRACT ADDRESSES
CORE_CONTRACT_ADDRESS=${contractAddress}
CORE_TOKEN_ADDRESS=${coreTokenAddress}
BTC_TOKEN_ADDRESS=${btcTokenAddress}
CORE_NODE_URL=https://rpc.test.btcs.network
`;
        fs.writeFileSync('.env', envContent);
        console.log("\n✅ .env file updated with new contract addresses");
        
        // Also update the main project .env files
        const mainEnvContent = `# CORE TESTNET CONFIGURATION
CORE_CONTRACT_ADDRESS=${contractAddress}
CORE_TOKEN_ADDRESS=${coreTokenAddress}
BTC_TOKEN_ADDRESS=${btcTokenAddress}
CORE_NODE_URL=https://rpc.test.btcs.network

# ENTITY CONFIGURATIONS FOR LOCALHOST
MINER_1_PRIVATE_KEY=0xe9c03148c011d553d43b485d73b1407d24f1498a664f782dc0204e524855be4e
MINER_1_ADDRESS=0xd89fBAbb72190ed22F012ADFC693ad974bAD3005
MINER_1_API_ENDPOINT=http://localhost:8101
MINER_1_PORT=8101

MINER_2_PRIVATE_KEY=0x3ace434e2cd05cd0e614eb5d423cf04e4b925c17db9869e9c598851f88f52840
MINER_2_ADDRESS=0x16102CA8BEF74fb6214AF352989b664BF0e50498
MINER_2_API_ENDPOINT=http://localhost:8102
MINER_2_PORT=8102

VALIDATOR_1_PRIVATE_KEY=0x3ac6e82cf34e51d376395af0338d0b1162c1d39b9d34614ed40186fd2367b33d
VALIDATOR_1_ADDRESS=0x25F3D6316017FDF7A4f4e54003b29212a198768f
VALIDATOR_1_API_ENDPOINT=http://localhost:8001
VALIDATOR_1_PORT=8001

VALIDATOR_2_PRIVATE_KEY=0xdf51093c674459eb0a5cc8a273418061fe4d7ca189bd84b74f478271714e0920
VALIDATOR_2_ADDRESS=0x352516F491DFB3E6a55bFa9c58C551Ef10267dbB
VALIDATOR_2_API_ENDPOINT=http://localhost:8002
VALIDATOR_2_PORT=8002

# NETWORK SETTINGS
SUBNET1_MINER_HOST=0.0.0.0
MINER_AGENT_CHECK_INTERVAL=10
LOG_LEVEL=INFO
`;
        
        // Update subnet1_aptos .env
        fs.writeFileSync('../../../subnet1_aptos/.env', mainEnvContent);
        console.log("✅ subnet1_aptos/.env updated with localhost endpoints");
        
        // Update moderntensor_aptos .env
        fs.writeFileSync('../../.env', envContent);
        console.log("✅ moderntensor_aptos/.env updated");
        
        console.log("\n🎯 NEXT STEPS:");
        console.log("1. Register entities with localhost endpoints");
        console.log("2. Start miner/validator processes");
        console.log("3. Test network communication");
        
    } catch (error) {
        console.error("💥 Deployment failed:", error.message);
        process.exit(1);
    }
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
