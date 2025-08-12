const { ethers } = require("hardhat");

async function main() {
    console.log("🌐 CREATING SUBNET 0");
    console.log("====================");
    
    const contractAddress = "0xAA6B8200495F7741B0B151B486aEB895fEE8c272";
    
    // Use miner_2's private key (contract owner from deployment logs)
    const ownerPrivateKey = "3ace434e2cd05cd0e614eb5d423cf04e4b925c17db9869e9c598851f88f52840";
    const owner = new ethers.Wallet(ownerPrivateKey, ethers.provider);
    
    console.log(`👤 Owner Address: ${owner.address}`);
    console.log(`📍 Contract: ${contractAddress}`);
    
    try {
        // Load contract with owner
        const ModernTensor = await ethers.getContractFactory("ModernTensor");
        const contract = ModernTensor.attach(contractAddress).connect(owner);
        
        // Create subnet 1
        console.log("\n🚀 Creating subnet 1...");
        const createTx = await contract.createSubnet(
            1,                                    // net_uid
            ethers.utils.parseEther("0.01"),     // min_stake_miner (0.01 CORE)
            ethers.utils.parseEther("0.1"),      // min_stake_validator (0.1 CORE)
            100,                                 // max_miners
            10,                                  // max_validators
            true                                 // registration_open
        );
        
        console.log(`⏳ Transaction sent: ${createTx.hash}`);
        
        const receipt = await createTx.wait();
        
        if (receipt.status === 1) {
            console.log("✅ SUBNET 1 CREATED SUCCESSFULLY!");
            console.log(`📦 Block: ${receipt.blockNumber}`);
            console.log(`⛽ Gas used: ${receipt.gasUsed.toString()}`);
        } else {
            console.log("❌ SUBNET CREATION FAILED");
        }
        
    } catch (error) {
        console.error("❌ Error creating subnet:", error.message);
        
        if (error.message.includes("Subnet already exists")) {
            console.log("ℹ️  Subnet 1 already exists!");
        }
    }
}

main().catch((error) => {
    console.error("💥 Script failed:", error);
    process.exitCode = 1;
});
