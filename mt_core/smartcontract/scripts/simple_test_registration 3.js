const { ethers } = require("hardhat");

async function main() {
    console.log("🔍 SIMPLE TEST REGISTRATION");
    console.log("=" * 40);

    const contractAddress = "0xAA6B8200495F7741B0B151B486aEB895fEE8c272";
    const coreTokenAddress = "0xbCfb1f5E120BE57cBBcB331D8392ae63C903dBaE";
    
    const ModernTensor = await ethers.getContractFactory("ModernTensor");
    const modernTensor = await ModernTensor.attach(contractAddress);
    
    const ERC20 = await ethers.getContractAt("IERC20", coreTokenAddress);
    
    console.log("📍 Contract:", contractAddress);
    console.log("🪙  Token:", coreTokenAddress);

    // Check all possible subnets
    const nextSubnetId = await modernTensor.nextSubnetId();
    console.log("🔢 Next Subnet ID:", nextSubnetId.toString());
    
    let validSubnetId = null;
    
    for (let i = 0; i < nextSubnetId.toNumber(); i++) {
        try {
            const subnet = await modernTensor.getSubnetStatic(i);
            console.log(`✅ Found Subnet ${i}:`);
            console.log(`  📋 Name: ${subnet.name}`);
            console.log(`  👤 Owner: ${subnet.owner_addr}`);
            console.log(`  💰 Min Miner: ${ethers.utils.formatEther(subnet.min_stake_miner)} tCORE`);
            console.log(`  💰 Min Validator: ${ethers.utils.formatEther(subnet.min_stake_validator)} tCORE`);
            validSubnetId = i;
        } catch (error) {
            console.log(`❌ Subnet ${i} not found:`, error.message);
        }
    }

    if (validSubnetId === null) {
        console.log("❌ No valid subnet found! Exiting...");
        return;
    }

    console.log(`\n🎯 Using Subnet ID: ${validSubnetId}`);

    // Test with one simple registration
    const testPrivateKey = "e9c03148c011d553d43b485d73b1407d24f1498a664f782dc0204e524855be4e";
    const testWallet = new ethers.Wallet(testPrivateKey, ethers.provider);
    const testAddress = testWallet.address;
    
    console.log(`\n🧪 Test Address: ${testAddress}`);
    
    // Check balances
    const nativeBalance = await testWallet.getBalance();
    const tokenBalance = await ERC20.balanceOf(testAddress);
    console.log(`💳 Native: ${ethers.utils.formatEther(nativeBalance)} CORE`);
    console.log(`💳 Token: ${ethers.utils.formatEther(tokenBalance)} tCORE`);
    
    // Check if already registered
    try {
        const minerInfo = await modernTensor.getMinerInfo(testAddress);
        if (minerInfo.uid !== "0x0000000000000000000000000000000000000000000000000000000000000000") {
            console.log("⚠️  Already registered as miner!");
            console.log(`  🏷️  UID: ${minerInfo.uid}`);
            console.log(`  🌐 Subnet: ${minerInfo.subnet_uid}`);
            console.log(`  💰 Stake: ${ethers.utils.formatEther(minerInfo.stake)}`);
            return;
        }
    } catch (error) {
        console.log("📝 Not registered yet");
    }
    
    // Try simple registration
    const stakeAmount = ethers.utils.parseEther("0.05");
    const contractWithSigner = modernTensor.connect(testWallet);
    const tokenWithSigner = ERC20.connect(testWallet);
    
    console.log(`\n🔄 Attempting registration...`);
    console.log(`  💰 Stake Amount: ${ethers.utils.formatEther(stakeAmount)} tCORE`);
    console.log(`  🌐 Subnet ID: ${validSubnetId}`);
    
    try {
        // First approve
        console.log("1️⃣ Approving tokens...");
        const approveTx = await tokenWithSigner.approve(contractAddress, stakeAmount);
        await approveTx.wait();
        console.log("✅ Tokens approved");
        
        // Check allowance
        const allowance = await ERC20.allowance(testAddress, contractAddress);
        console.log(`✅ Allowance: ${ethers.utils.formatEther(allowance)} tCORE`);
        
        // Try registration
        console.log("2️⃣ Registering miner...");
        const registerTx = await contractWithSigner.registerMiner(
            validSubnetId,
            stakeAmount,
            ethers.utils.parseEther("0"), // no BTC
            "http://localhost:8101",
            {
                gasLimit: 800000
            }
        );
        
        console.log(`⏳ Transaction: ${registerTx.hash}`);
        const receipt = await registerTx.wait();
        
        if (receipt.status === 1) {
            console.log("🎉 Registration successful!");
            console.log(`📦 Block: ${receipt.blockNumber}`);
            console.log(`⛽ Gas used: ${receipt.gasUsed.toString()}`);
            
            // Verify registration
            const minerInfo = await modernTensor.getMinerInfo(testAddress);
            console.log("📋 Miner Info:");
            console.log(`  🏷️  UID: ${minerInfo.uid}`);
            console.log(`  🌐 Subnet: ${minerInfo.subnet_uid}`);
            console.log(`  💰 Stake: ${ethers.utils.formatEther(minerInfo.stake)} tCORE`);
            
        } else {
            console.log("❌ Transaction failed");
        }
        
    } catch (error) {
        console.log("❌ Registration failed:", error.message);
        
        // Try to get more specific error
        if (error.data) {
            console.log("📋 Error data:", error.data);
        }
        
        // Check if it's a revert with reason
        if (error.reason) {
            console.log("📋 Revert reason:", error.reason);
        }
    }
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error("❌ Test failed:", error);
        process.exit(1);
    });