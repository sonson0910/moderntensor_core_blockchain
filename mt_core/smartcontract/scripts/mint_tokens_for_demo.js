const { ethers } = require("hardhat");

async function main() {
    console.log("💰 MINTING TOKENS FOR DEMO ACCOUNT");
    console.log("=" * 50);

    // Use existing entity (miner_1 from entities folder)
    const demoAddress = "0xd89fBAbb72190ed22F012ADFC693ad974bAD3005";
    const demoPrivateKey = "e9c03148c011d553d43b485d73b1407d24f1498a664f782dc0204e524855be4e";
    
    // Token addresses from deployment
    const coreTokenAddress = "0xbCfb1f5E120BE57cBBcB331D8392ae63C903dBaE";
    const btcTokenAddress = "0x8680Af4385d74979D12bCf56dBcAE8AE20B706c8";
    const contractAddress = "0xAA6B8200495F7741B0B151B486aEB895fEE8c272";

    // Get deployer (owner of tokens who can mint) - use deployer from deployment
    const deployerPrivateKey = "a07b6e0db803f9a21ffd1001c76b0aa0b313aaba8faab8c771af47301c4452b4";
    const deployer = new ethers.Wallet(deployerPrivateKey, ethers.provider);
    console.log("👤 Deployer (token owner):", deployer.address);
    console.log("🎯 Demo address:", demoAddress);

    // Get contract instances with connected deployer
    const MockToken = await ethers.getContractFactory("MockCoreToken", deployer);
    const coreToken = MockToken.attach(coreTokenAddress);
    const btcToken = MockToken.attach(btcTokenAddress);
    
    // Mint amounts (10 tokens each)
    const mintAmount = ethers.utils.parseEther("10");
    
    try {
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
        console.log("=" * 50);
        console.log("📋 NEXT STEPS:");
        console.log("1. Use private key to create wallet for registration");
        console.log("2. Approve contract to spend tokens");
        console.log("3. Register as miner with ModernTensor contract");
        console.log("");
        console.log("🔑 Miner_1 Account Info (from entities folder):");
        console.log(`  Address: ${demoAddress}`);
        console.log(`  Private Key: ${demoPrivateKey}`);
        console.log(`  CORE Token: ${coreTokenAddress}`);
        console.log(`  BTC Token: ${btcTokenAddress}`);
        console.log(`  Contract: ${contractAddress}`);
        
    } catch (error) {
        console.error("❌ Error:", error.message);
        if (error.message.includes("caller is not the owner")) {
            console.log("💡 Only the token owner can mint tokens");
            console.log("💡 Make sure you're using the deployer account");
        }
    }
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
