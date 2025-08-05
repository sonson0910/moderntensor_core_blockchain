const { ethers } = require("hardhat");
const fs = require('fs');

async function main() {
    console.log("�� Generating new wallet...");
    
    // Generate random wallet
    const wallet = ethers.Wallet.createRandom();
    
    console.log("\n🎯 NEW WALLET GENERATED:");
    console.log("=========================");
    console.log(`Address: ${wallet.address}`);
    console.log(`Private Key: ${wallet.privateKey.slice(2)}`); // Remove 0x prefix
    
    // Update .env file
    const envContent = `# CORE TESTNET CONFIGURATION
PRIVATE_KEY=${wallet.privateKey.slice(2)}
CORE_TESTNET_RPC=https://rpc.test2.btcs.network
CORE_MAINNET_RPC=https://rpc.test2.btcs.network
GAS_PRICE=20000000000
GAS_LIMIT=8000000

# CONTRACT ADDRESSES (will be updated after deployment)
CORE_CONTRACT_ADDRESS=
CORE_TOKEN_ADDRESS=
BTC_TOKEN_ADDRESS=
`;

    fs.writeFileSync('.env', envContent);
    console.log("\n✅ .env file updated with new private key");
    console.log("\n🚨 IMPORTANT: Request testnet tokens for this address:");
    console.log(`   https://scan.test.btcs.network/faucet`);
    console.log(`   Address: ${wallet.address}`);
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
