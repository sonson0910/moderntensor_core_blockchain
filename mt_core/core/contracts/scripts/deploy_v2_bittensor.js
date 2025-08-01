const { ethers } = require("hardhat");

async function main() {
    console.log("🚀 DEPLOYING ModernTensorAI v2.0 - Bittensor Edition");
    console.log("=" * 60);

    // Get network info
    const [deployer] = await ethers.getSigners();
    const network = await ethers.provider.getNetwork();
    const balance = await deployer.getBalance();

    console.log(`🌐 Network: ${network.name} (Chain ID: ${network.chainId})`);
    console.log(`👤 Deployer: ${deployer.address}`);
    console.log(`💰 Balance: ${ethers.utils.formatEther(balance)} CORE`);

    // Deploy mock tokens first (for testnet)
    let coreTokenAddress, btcTokenAddress;
    
    if (network.chainId === 1115) { // Core Testnet
        console.log("\n📦 DEPLOYING MOCK TOKENS FOR TESTNET...");
        
        // Deploy mock CORE token
        const MockCoreToken = await ethers.getContractFactory("MockCoreToken");
        const coreToken = await MockCoreToken.deploy("Core Token", "CORE");
        await coreToken.deployed();
        coreTokenAddress = coreToken.address;
        console.log(`✅ Mock CORE Token: ${coreTokenAddress}`);

        // Deploy mock BTC token  
        const btcToken = await MockCoreToken.deploy("Bitcoin Token", "BTC");
        await btcToken.deployed();
        btcTokenAddress = btcToken.address;
        console.log(`✅ Mock BTC Token: ${btcTokenAddress}`);

    } else if (network.chainId === 1116) { // Core Mainnet
        // Use real token addresses on mainnet
        coreTokenAddress = "0x40375C92d9FAf44d2f9db9Bd9ba41a3317a2404f"; // Real CORE
        btcTokenAddress = "0xYourBTCTokenAddress"; // Real BTC token
        console.log(`🔗 Using real CORE token: ${coreTokenAddress}`);
        console.log(`🔗 Using real BTC token: ${btcTokenAddress}`);
    } else {
        throw new Error(`Unsupported network: ${network.chainId}`);
    }

    // Contract parameters (ultra-low for testnet)
    const minMinerStake = ethers.utils.parseEther("0.05");    // 0.05 CORE
    const minValidatorStake = ethers.utils.parseEther("0.08"); // 0.08 CORE

    console.log("\n🏗️ DEPLOYING MODERNTENSORAI V2.0...");
    console.log(`📊 Min Miner Stake: ${ethers.utils.formatEther(minMinerStake)} CORE`);
    console.log(`📊 Min Validator Stake: ${ethers.utils.formatEther(minValidatorStake)} CORE`);

    // Deploy the main contract
    const ModernTensorAI_v2 = await ethers.getContractFactory("ModernTensorAI_v2_Bittensor");
    const modernTensorAI = await ModernTensorAI_v2.deploy(
        coreTokenAddress,
        btcTokenAddress,
        minMinerStake,
        minValidatorStake
    );

    console.log("⏳ Waiting for deployment confirmation...");
    await modernTensorAI.deployed();

    const receipt = await modernTensorAI.deployTransaction.wait();
    
    console.log("\n🎉 DEPLOYMENT SUCCESSFUL!");
    console.log(`📝 Contract Address: ${modernTensorAI.address}`);
    console.log(`🔗 Transaction Hash: ${modernTensorAI.deployTransaction.hash}`);
    console.log(`📊 Gas Used: ${receipt.gasUsed.toString()}`);
    console.log(`⛽ Gas Price: ${ethers.utils.formatUnits(modernTensorAI.deployTransaction.gasPrice, 'gwei')} Gwei`);

    // Verify contract parameters
    console.log("\n🔍 VERIFYING CONTRACT SETUP...");
    
    const deployedCoreToken = await modernTensorAI.coreToken();
    const deployedBtcToken = await modernTensorAI.btcToken();
    const networkStats = await modernTensorAI.getNetworkStats();
    
    console.log(`✅ CORE Token: ${deployedCoreToken}`);
    console.log(`✅ BTC Token: ${deployedBtcToken}`);
    console.log(`✅ Network Stats: Miners=${networkStats.totalMiners}, Validators=${networkStats.totalValidators}`);

    // Save deployment info
    const deploymentInfo = {
        network: network.name,
        chainId: network.chainId,
        contract: {
            name: "ModernTensorAI_v2_Bittensor",
            address: modernTensorAI.address,
            transactionHash: modernTensorAI.deployTransaction.hash,
            blockNumber: receipt.blockNumber,
            gasUsed: receipt.gasUsed.toString()
        },
        tokens: {
            coreToken: coreTokenAddress,
            btcToken: btcTokenAddress
        },
        parameters: {
            minMinerStake: minMinerStake.toString(),
            minValidatorStake: minValidatorStake.toString()
        },
        deployer: {
            address: deployer.address,
            balance: balance.toString()
        },
        timestamp: new Date().toISOString()
    };

    // Write deployment info to file
    const fs = require('fs');
    const deploymentFile = `deployment_v2_${network.chainId}_${Date.now()}.json`;
    fs.writeFileSync(deploymentFile, JSON.stringify(deploymentInfo, null, 2));
    
    console.log(`\n📄 Deployment info saved to: ${deploymentFile}`);

    // Print integration commands
    console.log("\n🔧 INTEGRATION COMMANDS:");
    console.log("=" * 40);
    console.log("1. Update .env files:");
    console.log(`   CORE_CONTRACT_ADDRESS=${modernTensorAI.address}`);
    console.log(`   CORE_TOKEN_ADDRESS=${coreTokenAddress}`);
    console.log(`   BTC_TOKEN_ADDRESS=${btcTokenAddress}`);
    console.log("\n2. Test registration:");
    console.log(`   registerMiner(0, ${minMinerStake}, 0, "http://miner-api.example.com")`);
    console.log(`   registerValidator(0, ${minValidatorStake}, 0, "http://validator-api.example.com")`);

    console.log("\n3. Explorer URLs:");
    console.log(`   Contract: https://scan.test.btcs.network/address/${modernTensorAI.address}`);
    console.log(`   TX: https://scan.test.btcs.network/tx/${modernTensorAI.deployTransaction.hash}`);

    console.log("\n🎯 READY FOR METAGRAPH INTEGRATION!");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error("💥 Deployment failed:", error);
        process.exit(1);
    }); 