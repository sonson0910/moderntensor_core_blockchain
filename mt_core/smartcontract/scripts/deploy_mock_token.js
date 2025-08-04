const { ethers } = require("hardhat");

async function main() {
    console.log("🪙 Deploying MockCoreToken for validator...");
    console.log("=" .repeat(60));

    const [deployer] = await ethers.getSigners();
    const network = await ethers.provider.getNetwork();
    
    console.log("📍 Network Information:");
    console.log(`   Chain ID: ${network.chainId}`);
    console.log(`   Deployer: ${deployer.address}`);
    console.log(`   Balance: ${ethers.utils.formatEther(await deployer.getBalance())} CORE`);
    console.log("");

    // Deploy MockCoreToken
    console.log("🏗️  Deploying MockCoreToken...");
    
    const MockCoreToken = await ethers.getContractFactory("MockCoreToken");
    const coreToken = await MockCoreToken.deploy("Testnet Core Token", "tCORE");
    
    console.log("⏳ Waiting for deployment...");
    await coreToken.deployed();
    
    const coreTokenAddress = coreToken.address;
    console.log("✅ MockCoreToken deployed to:", coreTokenAddress);

    // Verify deployment
    try {
        const name = await coreToken.name();
        const symbol = await coreToken.symbol();
        const owner = await coreToken.owner();
        const totalSupply = await coreToken.totalSupply();
        
        console.log("");
        console.log("🔍 Verification:");
        console.log(`   ✅ Name: ${name}`);
        console.log(`   ✅ Symbol: ${symbol}`);
        console.log(`   ✅ Owner: ${owner}`);
        console.log(`   ✅ Total Supply: ${ethers.utils.formatEther(totalSupply)} ${symbol}`);
        console.log("   ✅ Contract functional!");
        
    } catch (error) {
        console.log(`   ❌ Verification failed: ${error.message}`);
    }

    // Save deployment info
    const deploymentInfo = {
        network: "core_testnet",
        chainId: network.chainId,
        contractName: "MockCoreToken",
        contractAddress: coreTokenAddress,
        deployer: deployer.address,
        transactionHash: coreToken.deployTransaction.hash,
        parameters: {
            name: "Testnet Core Token",
            symbol: "tCORE"
        },
        deployedAt: new Date().toISOString()
    };

    console.log("");
    console.log("💾 Deployment Summary:");
    console.log(`   ✅ Contract: ${coreTokenAddress}`);
    console.log(`   ✅ Owner: ${deployer.address}`);
    console.log(`   ✅ Transaction: ${coreToken.deployTransaction.hash}`);
    console.log("   ✅ Ready for minting tokens!");
    
    return coreTokenAddress;
}

main()
    .then((address) => {
        console.log(`\n✅ MockCoreToken ready at: ${address}`);
        console.log("🚀 Next step: Update contract address in test scripts");
        process.exit(0);
    })
    .catch((error) => {
        console.error("❌ Deployment failed:");
        console.error(error);
        process.exit(1);
    }); 