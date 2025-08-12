const { ethers } = require("hardhat");

async function main() {
    console.log("🔐 APPROVE TOKENS AND REGISTER MINER");
    console.log("=" * 50);

    // Demo hotkey info
    const demoAddress = "0x9cc8CB3Ce44F5A61beD045E0b15A491d510035e1";
    const demoPrivateKey = "a6d219c8f8b1b73441324d918412cf93e77af3833ebed94826ef844f4cf4b9a4";
    
    // Contract addresses
    const coreTokenAddress = "0xbCfb1f5E120BE57cBBcB331D8392ae63C903dBaE";
    const btcTokenAddress = "0x8680Af4385d74979D12bCf56dBcAE8AE20B706c8";
    const contractAddress = "0xAA6B8200495F7741B0B151B486aEB895fEE8c272";

    // Create wallet
    const wallet = new ethers.Wallet(demoPrivateKey, ethers.provider);
    console.log("👤 Demo wallet:", wallet.address);

    // Get contract instances
    const MockToken = await ethers.getContractFactory("MockCoreToken");
    const coreToken = MockToken.attach(coreTokenAddress).connect(wallet);
    const btcToken = MockToken.attach(btcTokenAddress).connect(wallet);
    
    const ModernTensor = await ethers.getContractFactory("ModernTensor");
    const modernTensor = ModernTensor.attach(contractAddress).connect(wallet);
    
    try {
        // Check balances
        const coreBalance = await coreToken.balanceOf(wallet.address);
        const btcBalance = await btcToken.balanceOf(wallet.address);
        console.log(`💰 CORE Balance: ${ethers.utils.formatEther(coreBalance)} tCORE`);
        console.log(`💰 BTC Balance: ${ethers.utils.formatEther(btcBalance)} tBTC`);
        
        // Stake amounts
        const coreStakeAmount = ethers.utils.parseEther("0.05"); // 0.05 CORE
        const btcStakeAmount = ethers.utils.parseEther("0"); // No BTC stake
        
        console.log(`📊 Stake amount: ${ethers.utils.formatEther(coreStakeAmount)} CORE`);
        
        // Check current allowance
        const currentAllowance = await coreToken.allowance(wallet.address, contractAddress);
        console.log(`🔍 Current allowance: ${ethers.utils.formatEther(currentAllowance)} CORE`);
        
        if (currentAllowance.lt(coreStakeAmount)) {
            // Approve tokens
            console.log("\n🔐 Approving CORE tokens...");
            const approveAmount = ethers.utils.parseEther("10"); // Approve more than needed
            const approveTx = await coreToken.approve(contractAddress, approveAmount);
            await approveTx.wait();
            console.log("✅ CORE tokens approved");
            
            // Verify approval
            const newAllowance = await coreToken.allowance(wallet.address, contractAddress);
            console.log(`✅ New allowance: ${ethers.utils.formatEther(newAllowance)} CORE`);
        } else {
            console.log("✅ Sufficient allowance already exists");
        }
        
        // Check if already registered
        try {
            const minerInfo = await modernTensor.miners(wallet.address);
            if (minerInfo.uid !== "0x0000000000000000000000000000000000000000000000000000000000000000") {
                console.log("⚠️ Miner already registered!");
                console.log(`   UID: ${minerInfo.uid}`);
                console.log(`   Stake: ${ethers.utils.formatEther(minerInfo.stake)} CORE`);
                return;
            }
        } catch (error) {
            // Miner not registered, continue
        }
        
        // Register miner
        console.log("\n⛏️ Registering miner...");
        console.log(`   Subnet ID: 0`);
        console.log(`   CORE Stake: ${ethers.utils.formatEther(coreStakeAmount)} CORE`);
        console.log(`   BTC Stake: ${ethers.utils.formatEther(btcStakeAmount)} BTC`);
        console.log(`   API Endpoint: http://localhost:8103`);
        
        const registerTx = await modernTensor.registerMiner(
            0, // subnet_id
            coreStakeAmount, // core_stake
            btcStakeAmount, // btc_stake  
            "http://localhost:8103" // api_endpoint
        );
        
        console.log(`⏳ Transaction sent: ${registerTx.hash}`);
        const receipt = await registerTx.wait();
        
        if (receipt.status === 1) {
            console.log("✅ MINER REGISTRATION SUCCESSFUL!");
            console.log(`   Block: ${receipt.blockNumber}`);
            console.log(`   Gas used: ${receipt.gasUsed.toString()}`);
            
            // Get miner info
            const minerInfo = await modernTensor.miners(wallet.address);
            console.log(`   Generated UID: ${minerInfo.uid}`);
            console.log(`   Stake: ${ethers.utils.formatEther(minerInfo.stake)} CORE`);
        } else {
            console.log("❌ Transaction failed");
        }
        
    } catch (error) {
        console.error("❌ Error:", error.message);
        if (error.message.includes("insufficient allowance")) {
            console.log("💡 Need to approve tokens first");
        } else if (error.message.includes("already registered")) {
            console.log("💡 Miner already registered");
        }
    }
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
