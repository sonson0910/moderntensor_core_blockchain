const { ethers } = require("hardhat");

async function main() {
    console.log("🔧 FIXING REGISTRATION WITH CORRECT SUBNET ID");
    console.log("=" * 50);

    // Contract address on test2
    const contractAddress = "0x9c5B5d1082FEF8766aA9Ef28a1237aC5ae607841";
    
    // Get contract instance
    const ModernTensor = await ethers.getContractFactory("ModernTensor");
    const modernTensor = await ModernTensor.attach(contractAddress);
    
    console.log("📍 Contract Address:", contractAddress);

    try {
        // Check all subnets
        const nextSubnetId = await modernTensor.nextSubnetId();
        console.log("🔢 Next Subnet ID:", nextSubnetId.toString());
        
        let validSubnetId = null;
        
        // Check each possible subnet ID
        for (let i = 0; i < nextSubnetId.toNumber(); i++) {
            try {
                const subnet = await modernTensor.getSubnetStatic(i);
                console.log(`✅ Found Subnet ${i}:`);
                console.log(`  📋 Name: ${subnet.name}`);
                console.log(`  👤 Owner: ${subnet.owner_addr}`);
                console.log(`  💰 Min Miner Stake: ${ethers.utils.formatEther(subnet.min_stake_miner)} CORE`);
                console.log(`  💰 Min Validator Stake: ${ethers.utils.formatEther(subnet.min_stake_validator)} CORE`);
                validSubnetId = i;
                break;
            } catch (error) {
                console.log(`❌ Subnet ${i} not found`);
            }
        }

        if (validSubnetId === null) {
            console.log("❌ No valid subnet found!");
            return;
        }

        console.log(`\n🎯 Using Subnet ID: ${validSubnetId}`);

        // Deploy mock tokens first for test2 network
        console.log("\n🪙  Deploying mock tokens for test2...");
        
        const MockToken = await ethers.getContractFactory("MockCoreToken");
        
        // Deploy CORE token
        const coreToken = await MockToken.deploy("Test CORE Token", "tCORE");
        await coreToken.deployed();
        console.log("✅ Mock CORE Token deployed:", coreToken.address);
        
        // Deploy BTC token
        const btcToken = await MockToken.deploy("Test BTC Token", "tBTC");
        await btcToken.deployed();
        console.log("✅ Mock BTC Token deployed:", btcToken.address);

        // Test entity
        const testPrivateKey = "e9c03148c011d553d43b485d73b1407d24f1498a664f782dc0204e524855be4e";
        const testWallet = new ethers.Wallet(testPrivateKey, ethers.provider);
        
        console.log(`\n🧪 Testing with wallet: ${testWallet.address}`);
        
        // Mint tokens to test wallet
        const mintAmount = ethers.utils.parseEther("10");
        await coreToken.mint(testWallet.address, mintAmount);
        await btcToken.mint(testWallet.address, mintAmount);
        console.log("💰 Minted 10 tCORE and 10 tBTC to test wallet");
        
        // Check balances
        const coreBalance = await coreToken.balanceOf(testWallet.address);
        const btcBalance = await btcToken.balanceOf(testWallet.address);
        console.log(`💳 CORE Balance: ${ethers.utils.formatEther(coreBalance)} tCORE`);
        console.log(`💳 BTC Balance: ${ethers.utils.formatEther(btcBalance)} tBTC`);
        
        // Approve tokens
        const stakeAmount = ethers.utils.parseEther("0.05");
        const coreTokenWithSigner = coreToken.connect(testWallet);
        const approveTx = await coreTokenWithSigner.approve(contractAddress, mintAmount);
        await approveTx.wait();
        console.log("✅ Approved CORE tokens");
        
        // Test registration
        console.log("\n⛏️  Testing miner registration...");
        const contractWithSigner = modernTensor.connect(testWallet);
        
        try {
            const registerTx = await contractWithSigner.registerMiner(
                validSubnetId,
                stakeAmount,
                ethers.utils.parseEther("0"), // no BTC stake for now
                "http://localhost:8101",
                {
                    gasLimit: 500000,
                    gasPrice: ethers.utils.parseUnits("20", "gwei")
                }
            );
            
            console.log("⏳ Registration transaction:", registerTx.hash);
            const receipt = await registerTx.wait();
            console.log("✅ Miner registered successfully! Block:", receipt.blockNumber);
            
            // Check registration
            const minerInfo = await modernTensor.getMinerInfo(testWallet.address);
            console.log("📋 Miner Info:");
            console.log(`  🏷️  UID: ${minerInfo.uid}`);
            console.log(`  🌐 Subnet: ${minerInfo.subnet_uid}`);
            console.log(`  💰 Stake: ${ethers.utils.formatEther(minerInfo.stake)} CORE`);
            console.log(`  📍 Endpoint: ${minerInfo.api_endpoint}`);
            
        } catch (error) {
            console.log("❌ Registration failed:", error.message);
            
            // If still using wrong tokens, let's update the contract
            console.log("\n💡 The contract is using hardcoded token addresses from test network.");
            console.log("   For test2, we need to deploy a new contract with correct token addresses:");
            console.log(`   🪙  New CORE Token: ${coreToken.address}`);
            console.log(`   🪙  New BTC Token: ${btcToken.address}`);
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