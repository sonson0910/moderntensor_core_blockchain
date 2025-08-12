const { ethers } = require("hardhat");

async function main() {
    console.log("🌐 CREATING SUBNET 0 - EMERGENCY FIX");
    console.log("====================================");
    
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
        
        // Try alternative method: directly call internal _createSubnet via createSubnet
        console.log("\n🚀 Creating subnet 0 with proper parameters...");
        
        // Use createSubnet method with correct parameters
        const createTx = await contract.createSubnet(
            "Default Subnet",                    // name
            "Default subnet for ModernTensor",   // description  
            1000,                               // maxMiners (uint32)
            100,                                // maxValidators (uint32)
            ethers.utils.parseEther("0.01"),    // minStakeMiner
            ethers.utils.parseEther("0.1")      // minStakeValidator
        );
        
        console.log(`⏳ Transaction sent: ${createTx.hash}`);
        
        const receipt = await createTx.wait();
        
        if (receipt.status === 1) {
            console.log("✅ SUBNET CREATED SUCCESSFULLY!");
            console.log(`📦 Block: ${receipt.blockNumber}`);
            console.log(`⛽ Gas used: ${receipt.gasUsed.toString()}`);
            
            // Check the events to see which subnet ID was created
            const events = receipt.events?.filter(x => x.event === 'SubnetCreated');
            if (events && events.length > 0) {
                console.log(`🎯 Subnet ID created: ${events[0].args.subnetId.toString()}`);
            }
            
        } else {
            console.log("❌ SUBNET CREATION FAILED");
        }
        
    } catch (error) {
        console.error("❌ Error creating subnet:", error.message);
        
        if (error.message.includes("Subnet already exists")) {
            console.log("ℹ️  Subnet might already exist! Let's check...");
            
            // Try to read subnet 0 data
            try {
                const staticData = await contract.getSubnetStatic(0);
                console.log("✅ Subnet 0 exists:", {
                    name: staticData.name,
                    owner: staticData.owner_addr,
                    created: new Date(staticData.creation_time.toNumber() * 1000).toISOString()
                });
            } catch (readError) {
                console.log("❌ Could not read subnet 0:", readError.message);
            }
        }
    }
}

main().catch((error) => {
    console.error("💥 Script failed:", error);
    process.exitCode = 1;
});
