const { ethers } = require("hardhat");

async function main() {
    console.log("🔍 VERIFYING MINER REGISTRATION STATUS");
    console.log("=====================================");
    
    // Contract addresses
    const contractAddress = "0xAA6B8200495F7741B0B151B486aEB895fEE8c272";
    const demoHotkeyAddress = "0x9cc8CB3Ce44F5A61beD045E0b15A491d510035e1";
    
    try {
        // Load contract
        const ModernTensor = await ethers.getContractFactory("ModernTensor");
        const contract = ModernTensor.attach(contractAddress);
        
        console.log(`📍 Contract: ${contractAddress}`);
        console.log(`👤 Miner Address: ${demoHotkeyAddress}`);
        console.log("");
        
        // Check if miner is registered
        console.log("🔍 Checking registration status...");
        
        try {
            // Try to get miner info
            const minerInfo = await contract.minerInfo(demoHotkeyAddress);
            console.log("✅ MINER IS REGISTERED!");
            console.log("📊 Miner Info:", {
                uid: minerInfo.uid.toString(),
                subnetId: minerInfo.subnet_id.toString(),
                coreStake: ethers.utils.formatEther(minerInfo.core_stake),
                btcStake: ethers.utils.formatEther(minerInfo.btc_stake),
                apiEndpoint: minerInfo.api_endpoint,
                isActive: minerInfo.is_active
            });
        } catch (error) {
            if (error.message.includes("Miner not found")) {
                console.log("❌ MINER NOT REGISTERED");
                console.log("Reason: Miner not found in contract");
            } else {
                console.log("⚠️  Error checking miner info:", error.message);
            }
        }
        
        // Check subnet info
        console.log("\n🌐 Checking subnet 0 status...");
        try {
            const subnetStatic = await contract.subnetStatic(0);
            const subnetDynamic = await contract.subnetDynamic(0);
            
            console.log("📊 Subnet 0 Info:", {
                netUid: subnetStatic.net_uid.toString(),
                minStakeMiner: ethers.utils.formatEther(subnetStatic.min_stake_miner),
                registrationOpen: subnetDynamic.registration_open,
                minerCount: subnetDynamic.miner_count.toString(),
                validatorCount: subnetDynamic.validator_count.toString()
            });
        } catch (error) {
            console.log("⚠️  Error checking subnet info:", error.message);
        }
        
        // Check recent transactions
        console.log("\n📜 Checking recent registration transactions...");
        const registerTxHash = "0x0044a25e6c1f87716f764d2e14f6d9ed59e6ee6b9c4f56baddd5ab236700c721";
        const approveTxHash = "0x909b88a3e574e9171810d0cf34efcda13e842ec3313ff2055c220cc42533222d";
        
        const registerReceipt = await ethers.provider.getTransactionReceipt(registerTxHash);
        const approveReceipt = await ethers.provider.getTransactionReceipt(approveTxHash);
        
        console.log(`Approve TX (${approveTxHash.slice(0,10)}...): ${approveReceipt.status === 1 ? '✅ SUCCESS' : '❌ FAILED'}`);
        console.log(`Register TX (${registerTxHash.slice(0,10)}...): ${registerReceipt.status === 1 ? '✅ SUCCESS' : '❌ FAILED'}`);
        
        if (registerReceipt.status === 0) {
            console.log("\n🔍 ANALYZING FAILED REGISTRATION...");
            console.log("Gas used:", registerReceipt.gasUsed.toString());
            console.log("Gas limit:", registerReceipt.gasLimit?.toString() || "N/A");
            
            // Try to get revert reason
            try {
                const tx = await ethers.provider.getTransaction(registerTxHash);
                const result = await ethers.provider.call(tx, tx.blockNumber);
                console.log("Call result:", result);
            } catch (callError) {
                console.log("Revert reason:", callError.message);
            }
        }
        
    } catch (error) {
        console.error("❌ Error:", error.message);
    }
}

main().catch((error) => {
    console.error("💥 Script failed:", error);
    process.exitCode = 1;
});
