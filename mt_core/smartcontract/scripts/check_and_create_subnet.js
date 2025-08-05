const { ethers } = require("hardhat");

async function main() {
    console.log("🔍 CHECKING AND CREATING SUBNET");
    console.log("=" * 40);

    // Contract address on test2
    const contractAddress = "0x9c5B5d1082FEF8766aA9Ef28a1237aC5ae607841";
    
    // Get deployer (admin)
    const [deployer] = await ethers.getSigners();
    console.log("👤 Using admin account:", deployer.address);
    
    // Get contract instance
    const ModernTensor = await ethers.getContractFactory("ModernTensor");
    const modernTensor = await ModernTensor.attach(contractAddress);
    
    console.log("📍 Contract Address:", contractAddress);

    try {
        // Check current state
        const nextSubnetId = await modernTensor.nextSubnetId();
        console.log("🔢 Next Subnet ID:", nextSubnetId.toString());
        
        // Try to get subnet 0
        try {
            const subnet0 = await modernTensor.getSubnetStatic(0);
            console.log("✅ Subnet 0 exists:");
            console.log("  📋 Name:", subnet0.name);
            console.log("  👤 Owner:", subnet0.owner_addr);
            console.log("  ⛏️  Max Miners:", subnet0.max_miners.toString());
            console.log("  🔍 Max Validators:", subnet0.max_validators.toString());
            console.log("  💰 Min Miner Stake:", ethers.utils.formatEther(subnet0.min_stake_miner), "CORE");
            console.log("  💰 Min Validator Stake:", ethers.utils.formatEther(subnet0.min_stake_validator), "CORE");
            
        } catch (error) {
            console.log("❌ Subnet 0 not found, creating...");
            
            // Create default subnet
            const tx = await modernTensor.createSubnet(
                "Default Subnet",
                "Default subnet for ModernTensor network",
                1000, // max miners
                100,  // max validators
                ethers.utils.parseEther("0.01"), // min miner stake
                ethers.utils.parseEther("0.05")  // min validator stake
            );
            
            console.log("⏳ Transaction hash:", tx.hash);
            const receipt = await tx.wait();
            console.log("✅ Subnet created! Block:", receipt.blockNumber);
            
            // Get the created subnet
            const subnet0 = await modernTensor.getSubnetStatic(0);
            console.log("📋 Created Subnet 0:");
            console.log("  📋 Name:", subnet0.name);
            console.log("  👤 Owner:", subnet0.owner_addr);
        }

        // Get all subnet IDs
        try {
            const allSubnets = await modernTensor.getAllSubnetIds();
            console.log("🌐 All Subnet IDs:", allSubnets.map(id => id.toString()));
        } catch (error) {
            console.log("❌ Error getting all subnets:", error.message);
        }

        // Test registration now
        console.log("\n🧪 Testing registration after subnet setup...");
        
        const testPrivateKey = "e9c03148c011d553d43b485d73b1407d24f1498a664f782dc0204e524855be4e";
        const testWallet = new ethers.Wallet(testPrivateKey, ethers.provider);
        const contractWithSigner = modernTensor.connect(testWallet);
        
        const stakeAmount = ethers.utils.parseEther("0.05");
        const btcStake = ethers.utils.parseEther("0");
        
        try {
            // Now simulate registration
            await contractWithSigner.callStatic.registerMiner(
                0, // subnet id
                stakeAmount,
                btcStake,
                "http://localhost:8101"
            );
            console.log("✅ Registration simulation successful!");
            
        } catch (error) {
            console.log("❌ Registration still failing:", error.message);
            
            if (error.message.includes("ERC20")) {
                console.log("💡 Issue is with ERC20 tokens. Need to:");
                console.log("  1. Deploy mock CORE token");
                console.log("  2. Mint tokens to test accounts");
                console.log("  3. Approve contract to spend tokens");
            }
        }

    } catch (error) {
        console.log("❌ Script failed:", error.message);
    }
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error("❌ Script failed:", error);
        process.exit(1);
    });