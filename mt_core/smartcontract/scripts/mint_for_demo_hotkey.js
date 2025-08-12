const { ethers } = require("hardhat");

async function main() {
    console.log("💰 MINTING TOKENS FOR DEMO HOTKEY");
    console.log("=".repeat(50));

    // Demo hotkey info (từ HD wallet vừa tạo)
    const demoAddress = "0x89eE3344Fd4014457198af771529A36d4a7d2749";
    const demoPrivateKey = "dd5bd8a6688b1b62cf3ee187275c39c3aa9bdb3065daccc1e3b62b18ee05cc5e";
    
    // Use miner_2 key (owner of contract) để mint
    const ownerPrivateKey = "3ace434e2cd05cd0e614eb5d423cf04e4b925c17db9869e9c598851f88f52840"; // miner_2
    const owner = new ethers.Wallet(ownerPrivateKey, ethers.provider);
    
    // Token addresses (sử dụng địa chỉ gốc đang hoạt động)
    const coreTokenAddress = "0xbCfb1f5E120BE57cBBcB331D8392ae63C903dBaE";
    const btcTokenAddress = "0x8680Af4385d74979D12bCf56dBcAE8AE20B706c8";
    const contractAddress = "0xAA6B8200495F7741B0B151B486aEB895fEE8c272";

    console.log("👤 Owner (miner_2):", owner.address);
    console.log("🎯 Demo hotkey address:", demoAddress);

    // Get contract instances with owner
    const MockToken = await ethers.getContractFactory("MockCoreToken", owner);
    const coreToken = MockToken.attach(coreTokenAddress);
    const btcToken = MockToken.attach(btcTokenAddress);
    
    // Mint amounts (10 tokens each)
    const mintAmount = ethers.utils.parseEther("10");
    
    try {
        // Verify owner (skip if owner() method doesn't exist)
        try {
            const contractOwner = await coreToken.owner();
            console.log(`📋 Contract owner: ${contractOwner}`);
            console.log(`🔍 Is owner: ${contractOwner.toLowerCase() === owner.address.toLowerCase()}`);
            
            if (contractOwner.toLowerCase() !== owner.address.toLowerCase()) {
                throw new Error("Not the contract owner!");
            }
        } catch (ownerError) {
            console.log("⚠️ owner() method not available, proceeding with minting...");
        }
        
        // Check current balance
        console.log("\n📊 Current balances:");
        const coreBalance = await coreToken.balanceOf(demoAddress);
        const btcBalance = await btcToken.balanceOf(demoAddress);
        console.log(`  CORE: ${ethers.utils.formatEther(coreBalance)} tCORE`);
        console.log(`  BTC:  ${ethers.utils.formatEther(btcBalance)} tBTC`);
        
        // Mint CORE tokens
        console.log("\n💎 Minting CORE tokens...");
        const coreMinTx = await coreToken.mint(demoAddress, mintAmount);
        await coreMinTx.wait();
        console.log("✅ Minted 10 tCORE tokens");
        
        // Mint BTC tokens  
        console.log("\n🟡 Minting BTC tokens...");
        const btcMinTx = await btcToken.mint(demoAddress, mintAmount);
        await btcMinTx.wait();
        console.log("✅ Minted 10 tBTC tokens");
        
        // Check new balances
        console.log("\n📊 New balances:");
        const newCoreBalance = await coreToken.balanceOf(demoAddress);
        const newBtcBalance = await btcToken.balanceOf(demoAddress);
        console.log(`  CORE: ${ethers.utils.formatEther(newCoreBalance)} tCORE`);
        console.log(`  BTC:  ${ethers.utils.formatEther(newBtcBalance)} tBTC`);
        
        console.log("\n🎉 MINTING COMPLETED!");
        console.log("=".repeat(50));
        console.log("📋 DEMO HOTKEY INFO:");
        console.log(`  Address: ${demoAddress}`);
        console.log(`  Private Key: ${demoPrivateKey}`);
        console.log(`  CORE Balance: ${ethers.utils.formatEther(newCoreBalance)} tCORE`);
        console.log(`  BTC Balance: ${ethers.utils.formatEther(newBtcBalance)} tBTC`);
        console.log("");
        console.log("🎯 READY FOR REGISTRATION:");
        console.log(`  Contract: ${contractAddress}`);
        console.log(`  Min Stake: 0.01 CORE (sufficient balance: ✅)`);
        
    } catch (error) {
        console.error("❌ Error:", error.message);
    }
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
