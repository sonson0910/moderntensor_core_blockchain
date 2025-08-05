const { ethers } = require("hardhat");

async function main() {
    console.log("🔍 DEBUG REGISTRATION ISSUES");
    console.log("=" * 50);

    // Contract address on test2
    const contractAddress = "0x9c5B5d1082FEF8766aA9Ef28a1237aC5ae607841";
    
    // Get contract instance
    const ModernTensor = await ethers.getContractFactory("ModernTensor");
    const modernTensor = await ModernTensor.attach(contractAddress);
    
    console.log("📍 Contract Address:", contractAddress);

    try {
        // Check contract basic info
        const coreToken = await modernTensor.coreToken();
        const btcToken = await modernTensor.btcToken();
        
        console.log("🪙  CORE Token Address:", coreToken);
        console.log("🪙  BTC Token Address:", btcToken);

        // Get minimum stakes
        const subnetStatic = await modernTensor.getSubnetStatic(0);
        console.log("💰 Min Miner Stake:", ethers.utils.formatEther(subnetStatic.min_stake_miner), "CORE");
        console.log("💰 Min Validator Stake:", ethers.utils.formatEther(subnetStatic.min_stake_validator), "CORE");

        // Test with one entity
        const testPrivateKey = "e9c03148c011d553d43b485d73b1407d24f1498a664f782dc0204e524855be4e";
        const testWallet = new ethers.Wallet(testPrivateKey, ethers.provider);
        
        console.log(`\n🔍 Testing with wallet: ${testWallet.address}`);
        
        // Check balance
        const balance = await testWallet.getBalance();
        console.log("💳 Native Balance:", ethers.utils.formatEther(balance), "CORE");
        
        // Try to get CORE token contract
        console.log("\n🪙  Checking CORE token...");
        try {
            // Try standard ERC20 interface
            const coreTokenContract = await ethers.getContractAt("IERC20", coreToken);
            const tokenBalance = await coreTokenContract.balanceOf(testWallet.address);
            console.log("💰 CORE Token Balance:", ethers.utils.formatEther(tokenBalance), "CORE");
            
            // Check allowance
            const allowance = await coreTokenContract.allowance(testWallet.address, contractAddress);
            console.log("✅ Current Allowance:", ethers.utils.formatEther(allowance), "CORE");
            
        } catch (error) {
            console.log("❌ Error checking CORE token:", error.message);
        }

        // Check if we need to use native CORE instead of ERC20
        console.log("\n🔍 Testing contract call simulation...");
        
        const stakeAmount = ethers.utils.parseEther("0.05");
        const btcStake = ethers.utils.parseEther("0");
        
        try {
            // Simulate the call to see detailed error
            const contractWithSigner = modernTensor.connect(testWallet);
            await contractWithSigner.callStatic.registerMiner(
                0, // subnet id
                stakeAmount,
                btcStake,
                "http://localhost:8101"
            );
            console.log("✅ Simulation successful - no errors found");
            
        } catch (error) {
            console.log("❌ Simulation failed:", error.message);
            
            // Try to decode the error
            if (error.data) {
                console.log("📋 Error data:", error.data);
            }
            
            // Common issues to check
            console.log("\n🔍 Checking common issues:");
            
            // 1. Check if tokens need to be native CORE
            console.log("1. Checking if using native CORE for staking...");
            
            // 2. Try with value (native CORE)
            try {
                await contractWithSigner.callStatic.registerMiner(
                    0,
                    stakeAmount,
                    btcStake,
                    "http://localhost:8101",
                    { value: stakeAmount }
                );
                console.log("✅ Native CORE staking might work!");
            } catch (err) {
                console.log("❌ Native CORE staking also failed:", err.message);
            }
        }

        // Check if we need different token addresses for test2
        console.log("\n🌐 Test2 Network Token Information:");
        console.log("Current CORE Token:", coreToken);
        console.log("Current BTC Token:", btcToken);
        console.log("⚠️  These tokens might not exist on test2 network");
        console.log("💡 Consider deploying mock tokens for test2");

    } catch (error) {
        console.log("❌ Debug failed:", error.message);
    }
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error("❌ Debug script failed:", error);
        process.exit(1);
    });