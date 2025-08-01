const { ethers } = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
    console.log("🚀 DEPLOYING ModernTensorAI v2.0 with UID Update Functions");
    console.log("=" * 60);

    try {
        // Use direct private key for deployment
        const PRIVATE_KEY = "3ac6e82cf34e51d376395af0338d0b1162c1d39b9d34614ed40186fd2367b33d";
        const deployer = new ethers.Wallet(PRIVATE_KEY, ethers.provider);
        const network = await ethers.provider.getNetwork();

        console.log(`🌐 Network: ${network.name} (Chain ID: ${network.chainId})`);
        console.log(`👤 Deployer: ${deployer.address}`);

        // Try to get balance
        try {
            const balance = await deployer.getBalance();
            console.log(`💰 Balance: ${ethers.utils.formatEther(balance)} CORE`);
        } catch (e) {
            console.log("⚠️ Could not get balance, but proceeding...");
        }

        // Deploy mock ERC20 token for testing
        console.log("\n📦 DEPLOYING MOCK ERC20 TOKEN...");
        const MockERC20 = await ethers.getContractFactory("MockERC20");
        const mockToken = await MockERC20.deploy(
            "Mock CORE Token",
            "MCORE",
            ethers.utils.parseEther("1000000") // 1M tokens
        );
        await mockToken.deployed();
        const coreTokenAddress = mockToken.address;
        console.log(`✅ Mock CORE Token deployed: ${coreTokenAddress}`);

        console.log("\n🏗️ DEPLOYING MODERNTENSORAI V2.0...");

        // Deploy ModernTensor contract
        const ModernTensor = await ethers.getContractFactory("ModernTensor");
        const modernTensor = await ModernTensor.deploy(coreTokenAddress);
        await modernTensor.deployed();

        console.log(`✅ ModernTensorAI v2.0 deployed to: ${modernTensor.address}`);

        // Create default subnet with zero minimum stakes for testing
        console.log("\n📊 CREATING DEFAULT SUBNET...");
        const createSubnetTx = await modernTensor.createSubnet(
            0, // subnet UID
            "ModernTensor Default Subnet",
            "Default subnet for ModernTensor AI training",
            100, // max miners
            10,  // max validators
            3600, // immunity period (1 hour)
            ethers.utils.parseEther("0"), // min miner stake (zero for testing)
            ethers.utils.parseEther("0"), // min validator stake (zero for testing)
            ethers.utils.parseEther("0")  // registration cost (zero for testing)
        );
        await createSubnetTx.wait();
        console.log("✅ Default subnet created successfully");

        // Mint tokens for all entities and approve contract
        console.log("\n💰 MINTING TOKENS FOR ENTITIES...");
        const entitiesDir = path.join(__dirname, "../../../../../subnet1_aptos/entities");
        const entityFiles = fs.readdirSync(entitiesDir).filter(file => file.endsWith('.json'));
        
        for (const entityFile of entityFiles) {
            const entityData = JSON.parse(fs.readFileSync(path.join(entitiesDir, entityFile), 'utf8'));
            
            // Mint 1000 tokens to each entity
            const mintTx = await mockToken.mint(entityData.address, ethers.utils.parseEther("1000"));
            await mintTx.wait();
            console.log(`✅ Minted 1000 MCORE to ${entityData.name} (${entityData.address})`);
        }

        console.log("\n🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!");
        console.log(`📋 Contract Address: ${modernTensor.address}`);
        console.log(`📋 Core Token: ${coreTokenAddress}`);
        console.log(`📋 Network: ${network.name} (${network.chainId})`);
        
        console.log("\n🔧 NEW UID UPDATE FUNCTIONS AVAILABLE:");
        console.log("• updateMinerUID(address, bytes32) - Admin can update miner UID");
        console.log("• updateValidatorUID(address, bytes32) - Admin can update validator UID");
        console.log("• updateMinerUIDSelf(bytes32) - Miners can update their own UID");
        console.log("• updateValidatorUIDSelf(bytes32) - Validators can update their own UID");

        // Save deployment info
        const deploymentInfo = {
            network: network.name,
            chainId: network.chainId,
            modernTensorAddress: modernTensor.address,
            coreTokenAddress: coreTokenAddress,
            deployerAddress: deployer.address,
            deploymentTime: new Date().toISOString(),
            features: [
                "UID Update Functions",
                "Miner Self-Update",
                "Validator Self-Update",
                "Admin Update Controls"
            ]
        };

        fs.writeFileSync(
            'deployment-info.json',
            JSON.stringify(deploymentInfo, null, 2)
        );
        console.log("\n💾 Deployment info saved to deployment-info.json");

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