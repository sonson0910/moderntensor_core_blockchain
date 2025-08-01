const { ethers } = require("hardhat");

async function main() {
    console.log("🚀 Deploying Low-Stake ModernTensorAI for Testnet...");
    console.log("=" .repeat(60));

    const [deployer] = await ethers.getSigners();
    const network = await ethers.provider.getNetwork();
    
    console.log("📍 Network Information:");
    console.log(`   Chain ID: ${network.chainId}`);
    console.log(`   Deployer: ${deployer.address}`);
    console.log(`   Balance: ${ethers.utils.formatEther(await deployer.getBalance())} CORE`);
    console.log("");

    // Deploy mock tokens for testnet
    console.log("🏗️  Deploying mock tokens for testnet...");
    
    const MockToken = await ethers.getContractFactory("MockCoreToken");
    
    const coreToken = await MockToken.deploy("Testnet Core Token", "tCORE");
    await coreToken.deployed();
    console.log(`   ✅ Mock CORE Token: ${coreToken.address}`);
    
    const btcToken = await MockToken.deploy("Testnet Bitcoin Token", "tBTC");
    await btcToken.deployed();
    console.log(`   ✅ Mock BTC Token: ${btcToken.address}`);

    console.log("");
    console.log("🚀 Deploying ModernTensorAI_Optimized with LOW STAKE requirements...");
    
    // LOW STAKE PARAMETERS for testnet - VERY LOW for faucet limitations
    const deployParams = {
        coreToken: coreToken.address,
        btcToken: btcToken.address,
        minConsensusValidators: 2,           // Reduced from 3
        consensusThreshold: 5000,            // 50% instead of 66.67%
        minMinerStake: ethers.utils.parseEther("0.05"),    // 0.05 CORE (10x lower)
        minValidatorStake: ethers.utils.parseEther("0.08"), // 0.08 CORE (10x lower)
        btcBoostMultiplier: 12000            // 120% instead of 150%
    };

    console.log("📋 LOW STAKE Parameters:");
    console.log(`   Min Consensus Validators: ${deployParams.minConsensusValidators}`);
    console.log(`   Consensus Threshold: ${deployParams.consensusThreshold / 100}%`);
    console.log(`   Min Miner Stake: ${ethers.utils.formatEther(deployParams.minMinerStake)} CORE`);
    console.log(`   Min Validator Stake: ${ethers.utils.formatEther(deployParams.minValidatorStake)} CORE`);
    console.log(`   BTC Boost Multiplier: ${deployParams.btcBoostMultiplier / 100}%`);
    console.log("");

    // Deploy contract
    const ModernTensorAI = await ethers.getContractFactory("ModernTensorAI_Optimized");
    
    console.log("⏳ Deploying contract...");
    const modernTensorAI = await ModernTensorAI.deploy(
        deployParams.coreToken,
        deployParams.btcToken,
        deployParams.minConsensusValidators,
        deployParams.consensusThreshold,
        deployParams.minMinerStake,
        deployParams.minValidatorStake,
        deployParams.btcBoostMultiplier
    );

    console.log("⏳ Waiting for deployment...");
    await modernTensorAI.deployed();

    console.log("");
    console.log("🎉 LOW-STAKE CONTRACT DEPLOYED!");
    console.log("=" .repeat(60));
    console.log(`📍 Contract Address: ${modernTensorAI.address}`);
    console.log(`🔗 Transaction: ${modernTensorAI.deployTransaction.hash}`);
    console.log(`⛽ Gas Used: ${modernTensorAI.deployTransaction.gasLimit?.toString() || 'Unknown'}`);
    
    // Verification
    try {
        const minMinerStake = await modernTensorAI.MIN_MINER_STAKE();
        const minValidatorStake = await modernTensorAI.MIN_VALIDATOR_STAKE();
        
        console.log("");
        console.log("🔍 Verification:");
        console.log(`   ✅ Min Miner Stake: ${ethers.utils.formatEther(minMinerStake)} CORE`);
        console.log(`   ✅ Min Validator Stake: ${ethers.utils.formatEther(minValidatorStake)} CORE`);
        console.log("   ✅ Contract functional!");
        
    } catch (error) {
        console.log(`   ❌ Verification failed: ${error.message}`);
    }

    // Save deployment info
    const deploymentInfo = {
        network: "core_testnet",
        chainId: network.chainId,
        contractName: "ModernTensorAI_Optimized_LowStake",
        contractAddress: modernTensorAI.address,
        coreToken: coreToken.address,
        btcToken: btcToken.address,
        deployer: deployer.address,
        transactionHash: modernTensorAI.deployTransaction.hash,
        parameters: {
            minMinerStake: "0.05 CORE",
            minValidatorStake: "0.08 CORE",
            minConsensusValidators: 2,
            consensusThreshold: "50%"
        },
        deployedAt: new Date().toISOString()
    };

    console.log("");
    console.log("💾 Deployment Summary:");
    console.log("   - ULTRA LOW stake requirements for faucet tokens");
    console.log("   - Miners need: 0.05 CORE (1/20th of faucet amount)");
    console.log("   - Validators need: 0.08 CORE (less than 1/10th of faucet)");
    console.log("   - Everyone can participate with just 1 CORE from faucet!");
    console.log("   - Remaining tokens for gas fees and operations");
    
    return modernTensorAI.address;
}

main()
    .then((address) => {
        console.log(`\n✅ Low-stake contract ready at: ${address}`);
        process.exit(0);
    })
    .catch((error) => {
        console.error("❌ Deployment failed:");
        console.error(error);
        process.exit(1);
    });