const { ethers } = require("hardhat");

async function main() {
    console.log("🚀 DEPLOYING MODERNTENSOR CONTRACT");
    console.log("=" * 50);

    // Get the deployer account
    const [deployer] = await ethers.getSigners();
    console.log("👤 Deploying with account:", deployer.address);
    
    // Get balance
    const balance = await deployer.provider.getBalance(deployer.address);
    console.log("💰 Account balance:", ethers.utils.formatEther(balance), "CORE");

    // Contract constructor parameters
    const coreTokenAddress = "0x7B74e4868c8C500D6143CEa53a5d2F94e94c7637"; // Core testnet CORE token
    const btcTokenAddress = "0x44Ed1441D79FfCb76b7D6644dBa930309E0E6F31";  // Core testnet BTC token
    const minMinerStake = ethers.utils.parseEther("0.01");    // 0.01 CORE minimum for miners
    const minValidatorStake = ethers.utils.parseEther("0.05"); // 0.05 CORE minimum for validators

    console.log("📋 Contract Parameters:");
    console.log("  🔹 CORE Token:", coreTokenAddress);
    console.log("  🔹 BTC Token:", btcTokenAddress);
    console.log("  🔹 Min Miner Stake:", ethers.utils.formatEther(minMinerStake), "CORE");
    console.log("  🔹 Min Validator Stake:", ethers.utils.formatEther(minValidatorStake), "CORE");

    // Get contract factory
    console.log("\n🔧 Getting ModernTensor contract factory...");
    const ModernTensor = await ethers.getContractFactory("ModernTensor");

    // Deploy contract
    console.log("📤 Deploying ModernTensor contract...");
    const modernTensor = await ModernTensor.deploy(
        coreTokenAddress,
        btcTokenAddress,
        minMinerStake,
        minValidatorStake
    );

    // Wait for deployment
    console.log("⏳ Waiting for deployment confirmation...");
    await modernTensor.deployed();

    const contractAddress = modernTensor.address;
    console.log("✅ ModernTensor deployed to:", contractAddress);

    // Verify deployment
    console.log("\n🔍 Verifying deployment...");
    
    try {
        // Check contract properties
        const coreToken = await modernTensor.coreToken();
        const btcToken = await modernTensor.btcToken();
        const currentEpoch = await modernTensor.currentEpoch();
        const nextSubnetId = await modernTensor.nextSubnetId();
        
        console.log("📊 Contract State:");
        console.log("  🔹 CORE Token:", coreToken);
        console.log("  🔹 BTC Token:", btcToken);
        console.log("  🔹 Current Epoch:", currentEpoch.toString());
        console.log("  🔹 Next Subnet ID:", nextSubnetId.toString());

        // Check network stats
        const networkStats = await modernTensor.getNetworkStats();
        console.log("  🔹 Total Miners:", networkStats[0].toString());
        console.log("  🔹 Total Validators:", networkStats[1].toString());
        console.log("  🔹 Total Staked:", ethers.utils.formatEther(networkStats[2]), "CORE");
        console.log("  🔹 Total Rewards:", ethers.utils.formatEther(networkStats[3]), "CORE");

        // Check default subnet
        const subnetMiners = await modernTensor.getSubnetMiners(0);
        const subnetValidators = await modernTensor.getSubnetValidators(0);
        console.log("  🔹 Default Subnet Miners:", subnetMiners.length);
        console.log("  🔹 Default Subnet Validators:", subnetValidators.length);

    } catch (error) {
        console.error("❌ Error verifying deployment:", error.message);
    }

    // Get deployment transaction details
    const deployTx = modernTensor.deployTransaction;
    if (deployTx) {
        console.log("\n📋 Deployment Transaction:");
        console.log("  🔹 Hash:", deployTx.hash);
        console.log("  🔹 Gas Limit:", deployTx.gasLimit.toString());
        console.log("  🔹 Gas Price:", ethers.utils.formatUnits(deployTx.gasPrice, "gwei"), "gwei");
        
        // Wait for receipt
        const receipt = await deployTx.wait();
        console.log("  🔹 Gas Used:", receipt.gasUsed.toString());
        console.log("  🔹 Block Number:", receipt.blockNumber);
        console.log("  🔹 Status:", receipt.status === 1 ? "✅ Success" : "❌ Failed");
    }

    console.log("\n🎉 MODERNTENSOR DEPLOYMENT COMPLETED!");
    console.log("=" * 50);
    console.log("📋 SUMMARY:");
    console.log(`  📍 Contract Address: ${contractAddress}`);
    console.log(`  🔗 Explorer: https://scan.test.btcs.network/address/${contractAddress}`);
    console.log(`  🌐 Network: Core Testnet`);
    console.log(`  👤 Deployer: ${deployer.address}`);
    
    // Save deployment info
    const deploymentInfo = {
        contractAddress: contractAddress,
        contractName: "ModernTensor",
        network: "Core Testnet",
        deployer: deployer.address,
        deploymentTime: new Date().toISOString(),
        transactionHash: deployTx?.hash,
        blockNumber: deployTx ? (await deployTx.wait()).blockNumber : null,
        constructorArgs: {
            coreToken: coreTokenAddress,
            btcToken: btcTokenAddress,
            minMinerStake: minMinerStake.toString(),
            minValidatorStake: minValidatorStake.toString()
        }
    };

    // Write deployment info to file
    const fs = require('fs');
    const path = require('path');
    
    const deploymentPath = path.join(__dirname, '../deployments');
    if (!fs.existsSync(deploymentPath)) {
        fs.mkdirSync(deploymentPath, { recursive: true });
    }
    
    fs.writeFileSync(
        path.join(deploymentPath, 'moderntensor_deployment.json'),
        JSON.stringify(deploymentInfo, null, 2)
    );
    
    console.log("💾 Deployment info saved to deployments/moderntensor_deployment.json");
    
    return {
        contractAddress,
        deploymentInfo
    };
}

// We recommend this pattern to be able to use async/await everywhere
// and properly handle errors.
main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error("❌ Deployment failed:", error);
        process.exit(1);
    });