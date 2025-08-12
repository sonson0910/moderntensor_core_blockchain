const { ethers } = require("hardhat");

async function main() {
    const contractAddress = "0xAA6B8200495F7741B0B151B486aEB895fEE8c272";
    const demoAddress = "0x9cc8CB3Ce44F5A61beD045E0b15A491d510035e1";
    
    console.log("🔍 CHECKING REGISTRATION STATUS");
    console.log("===============================");
    
    try {
        const ModernTensor = await ethers.getContractFactory("ModernTensor");
        const contract = ModernTensor.attach(contractAddress);
        
        console.log(`📍 Contract: ${contractAddress}`);
        console.log(`👤 Demo Address: ${demoAddress}`);
        console.log("");
        
        console.log("🔍 Checking if demo_hotkey is registered...");
        const minerInfo = await contract.getMinerInfo(demoAddress);
        
        // Check if miner exists (uid should not be zero)
        if (minerInfo.uid === "0x0000000000000000000000000000000000000000000000000000000000000000") {
            console.log("❌ DEMO_HOTKEY NOT REGISTERED");
            console.log("UID is zero - miner not found");
        } else {
            console.log("✅ DEMO_HOTKEY IS REGISTERED!");
            console.log("📊 Miner Info:", {
                uid: minerInfo.uid,
                subnetUid: minerInfo.subnet_uid.toString(),
                coreStake: ethers.utils.formatEther(minerInfo.stake),
                btcStake: ethers.utils.formatEther(minerInfo.bitcoin_stake),
                performance: minerInfo.scaled_last_performance.toString(),
                trustScore: minerInfo.scaled_trust_score.toString(),
                apiEndpoint: minerInfo.api_endpoint,
                status: minerInfo.status,
                owner: minerInfo.owner
            });
        }
        
    } catch (error) {
        console.log("⚠️  Error checking registration:", error.message);
        
        // If error contains specific messages, handle them
        if (error.message.includes("Miner not found")) {
            console.log("❌ DEMO_HOTKEY NOT REGISTERED");
        } else {
            console.log("💡 This might mean the miner is not registered yet");
        }
    }
    
    // Also check some existing miners for comparison
    console.log("\n🔍 Checking existing miners...");
    const existingAddresses = [
        "0xd89fBAbb72190ed22F012ADFC693ad974bAD3005", // miner_1
        "0x16102CA8BEF74fb6214AF352989b664BF0e50498", // miner_2
    ];
    
    for (const addr of existingAddresses) {
        try {
            const info = await contract.getMinerInfo(addr);
            if (info.uid !== "0x0000000000000000000000000000000000000000000000000000000000000000") {
                console.log(`✅ ${addr}: REGISTERED (UID: ${info.uid.slice(0,10)}...)`);
            }
        } catch (e) {
            console.log(`❌ ${addr}: NOT REGISTERED`);
        }
    }
}

main().catch((error) => {
    console.error("💥 Script failed:", error);
    process.exitCode = 1;
});
