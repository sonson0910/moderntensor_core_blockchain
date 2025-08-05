const { ethers } = require("hardhat");

async function main() {
    console.log("🚀 DEPLOYING MODERNTENSOR WITH MOCK TOKENS ON TEST2");
    console.log("=" * 60);

    // Get the deployer account
    const [deployer] = await ethers.getSigners();
    console.log("👤 Deploying with account:", deployer.address);
    
    // Get balance
    const balance = await deployer.provider.getBalance(deployer.address);
    console.log("💰 Account balance:", ethers.utils.formatEther(balance), "CORE");

    // Step 1: Deploy Mock Tokens
    console.log("\n🪙  STEP 1: Deploying Mock Tokens...");
    const MockToken = await ethers.getContractFactory("MockCoreToken");
    
    // Deploy CORE token
    const coreToken = await MockToken.deploy("Test CORE Token", "tCORE");
    await coreToken.deployed();
    console.log("✅ Mock CORE Token deployed:", coreToken.address);
    
    // Deploy BTC token
    const btcToken = await MockToken.deploy("Test BTC Token", "tBTC");
    await btcToken.deployed();
    console.log("✅ Mock BTC Token deployed:", btcToken.address);

    // Step 2: Deploy ModernTensor Contract
    console.log("\n🏗️  STEP 2: Deploying ModernTensor Contract...");
    
    const minMinerStake = ethers.utils.parseEther("0.01");    // 0.01 tCORE minimum for miners
    const minValidatorStake = ethers.utils.parseEther("0.05"); // 0.05 tCORE minimum for validators

    console.log("📋 Contract Parameters:");
    console.log("  🔹 CORE Token:", coreToken.address);
    console.log("  🔹 BTC Token:", btcToken.address);
    console.log("  🔹 Min Miner Stake:", ethers.utils.formatEther(minMinerStake), "tCORE");
    console.log("  🔹 Min Validator Stake:", ethers.utils.formatEther(minValidatorStake), "tCORE");

    // Get contract factory
    const ModernTensor = await ethers.getContractFactory("ModernTensor");

    // Deploy contract
    console.log("📤 Deploying ModernTensor contract...");
    const modernTensor = await ModernTensor.deploy(
        coreToken.address,
        btcToken.address,
        minMinerStake,
        minValidatorStake
    );

    // Wait for deployment
    console.log("⏳ Waiting for deployment confirmation...");
    await modernTensor.deployed();

    const contractAddress = modernTensor.address;
    console.log("✅ ModernTensor deployed to:", contractAddress);

    // Step 3: Verify deployment
    console.log("\n🔍 STEP 3: Verifying deployment...");
    
    try {
        // Check contract properties
        const contractCoreToken = await modernTensor.coreToken();
        const contractBtcToken = await modernTensor.btcToken();
        const currentEpoch = await modernTensor.currentEpoch();
        const nextSubnetId = await modernTensor.nextSubnetId();
        
        console.log("📊 Contract State:");
        console.log("  🔹 CORE Token:", contractCoreToken);
        console.log("  🔹 BTC Token:", contractBtcToken);
        console.log("  🔹 Current Epoch:", currentEpoch.toString());
        console.log("  🔹 Next Subnet ID:", nextSubnetId.toString());

        // Check default subnet (should be created by constructor)
        try {
            const subnet0 = await modernTensor.getSubnetStatic(0);
            console.log("  🔹 Default Subnet Name:", subnet0.name);
            console.log("  🔹 Default Subnet Owner:", subnet0.owner_addr);
        } catch (error) {
            console.log("  ⚠️  Default subnet not created, will create manually...");
        }

    } catch (error) {
        console.log("❌ Error verifying deployment:", error.message);
    }

    // Step 4: Mint tokens to test entities
    console.log("\n💰 STEP 4: Minting tokens to test entities...");
    
    const testEntities = [
        "0xd89fBAbb72190ed22F012ADFC693ad974bAD3005", // miner_1
        "0x16102CA8BEF74fb6214AF352989b664BF0e50498", // miner_2 (also deployer)
        "0x25F3D6316017FDF7A4f4e54003b29212a198768f", // validator_1
        "0x352516F491DFB3E6a55bFa9c58C551Ef10267dbB", // validator_2
        "0x0469C6644c07F6e860Af368Af8104F8D8829a78e"  // validator_3
    ];

    const mintAmount = ethers.utils.parseEther("10"); // 10 tokens each

    for (const address of testEntities) {
        await coreToken.mint(address, mintAmount);
        await btcToken.mint(address, mintAmount);
        console.log(`  ✅ Minted 10 tCORE + 10 tBTC to ${address}`);
    }

    // Step 5: Save deployment info
    console.log("\n💾 STEP 5: Saving deployment info...");
    
    const deploymentInfo = {
        contractAddress: contractAddress,
        contractName: "ModernTensor",
        network: "Core Test2",
        chainId: 1114,
        deployer: deployer.address,
        deploymentTime: new Date().toISOString(),
        tokens: {
            coreToken: coreToken.address,
            btcToken: btcToken.address
        },
        constructorArgs: {
            coreToken: coreToken.address,
            btcToken: btcToken.address,
            minMinerStake: minMinerStake.toString(),
            minValidatorStake: minValidatorStake.toString()
        },
        testEntities: testEntities
    };

    const fs = require('fs');
    const path = require('path');
    
    const deploymentPath = path.join(__dirname, '../deployments');
    if (!fs.existsSync(deploymentPath)) {
        fs.mkdirSync(deploymentPath, { recursive: true });
    }
    
    fs.writeFileSync(
        path.join(deploymentPath, 'moderntensor_test2_deployment.json'),
        JSON.stringify(deploymentInfo, null, 2)
    );

    console.log("\n🎉 DEPLOYMENT COMPLETED!");
    console.log("=" * 60);
    console.log("📋 SUMMARY:");
    console.log(`  📍 Contract Address: ${contractAddress}`);
    console.log(`  🪙  CORE Token: ${coreToken.address}`);
    console.log(`  🪙  BTC Token: ${btcToken.address}`);
    console.log(`  🌐 Network: Core Test2 (Chain ID: 1114)`);
    console.log(`  👤 Deployer: ${deployer.address}`);
    console.log(`  💾 Info saved to: deployments/moderntensor_test2_deployment.json`);
    
    console.log("\n🚀 Ready for entity registration!");
    
    return {
        contractAddress,
        coreToken: coreToken.address,
        btcToken: btcToken.address,
        deploymentInfo
    };
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error("❌ Deployment failed:", error);
        process.exit(1);
    });