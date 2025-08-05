const { ethers } = require("hardhat");
const fs = require('fs');
const path = require('path');

async function main() {
    console.log("🚀 REGISTERING ENTITIES ON NEW MODERNTENSOR CONTRACT");
    console.log("=" * 60);

    // New contract addresses
    const contractAddress = "0xAA6B8200495F7741B0B151B486aEB895fEE8c272";
    const coreTokenAddress = "0xbCfb1f5E120BE57cBBcB331D8392ae63C903dBaE";
    const btcTokenAddress = "0x8680Af4385d74979D12bCf56dBcAE8AE20B706c8";
    
    // Get contract instances
    const ModernTensor = await ethers.getContractFactory("ModernTensor");
    const modernTensor = await ModernTensor.attach(contractAddress);
    
    const ERC20 = await ethers.getContractAt("IERC20", coreTokenAddress);
    
    console.log("📍 Contract Address:", contractAddress);
    console.log("🪙  CORE Token:", coreTokenAddress);

    // Step 1: Create default subnet
    console.log("\n🏗️  STEP 1: Creating default subnet...");
    const [deployer] = await ethers.getSigners();
    
    try {
        const subnet0 = await modernTensor.getSubnetStatic(0);
        console.log("✅ Default subnet already exists:", subnet0.name);
    } catch (error) {
        console.log("⚠️  Creating default subnet...");
        const createTx = await modernTensor.createSubnet(
            "Default Subnet",
            "Default subnet for ModernTensor test2 network",
            1000, // max miners
            100,  // max validators
            ethers.utils.parseEther("0.01"), // min miner stake
            ethers.utils.parseEther("0.05")  // min validator stake
        );
        await createTx.wait();
        console.log("✅ Default subnet created!");
    }

    // Step 2: Register entities
    console.log("\n⚡ STEP 2: Registering entities...");
    
    // Path to entities folder
    const entitiesPath = path.join(__dirname, '../../../../subnet1_aptos/entities');
    const entityFiles = fs.readdirSync(entitiesPath).filter(f => f.endsWith('.json'));
    
    console.log(`📂 Found ${entityFiles.length} entity files:`, entityFiles);

    const results = {
        miners: [],
        validators: [],
        errors: []
    };

    // Process each entity
    for (const file of entityFiles) {
        try {
            console.log(`\n🔄 Processing ${file}...`);
            
            // Read entity data
            const entityData = JSON.parse(fs.readFileSync(path.join(entitiesPath, file)));
            
            const {
                name,
                type,
                address,
                private_key,
                stake_amount,
                api_endpoint
            } = entityData;

            console.log(`  📋 Name: ${name}`);
            console.log(`  🏷️  Type: ${type}`);
            console.log(`  📍 Address: ${address}`);
            console.log(`  💰 Stake: ${stake_amount} tCORE`);

            // Create wallet from private key
            const wallet = new ethers.Wallet(private_key, ethers.provider);
            const contractWithSigner = modernTensor.connect(wallet);
            const tokenWithSigner = ERC20.connect(wallet);

            // Convert stake amount to wei
            const stakeWei = ethers.utils.parseEther(stake_amount);
            
            // Check token balance
            const tokenBalance = await ERC20.balanceOf(address);
            console.log(`  💳 tCORE Balance: ${ethers.utils.formatEther(tokenBalance)}`);

            if (tokenBalance.lt(stakeWei)) {
                console.log(`  ❌ Insufficient token balance`);
                results.errors.push({
                    file,
                    error: "Insufficient token balance"
                });
                continue;
            }

            // Approve tokens
            console.log(`  ✅ Approving tokens...`);
            const approveTx = await tokenWithSigner.approve(contractAddress, stakeWei);
            await approveTx.wait();
            console.log(`  ✅ Approved ${stake_amount} tCORE`);

            // Register based on type
            let tx;
            if (type === 'miner') {
                console.log(`  ⛏️  Registering as MINER...`);
                
                tx = await contractWithSigner.registerMiner(
                    0, // subnet id (using default subnet 0)
                    stakeWei,
                    ethers.utils.parseEther("0"), // no BTC stake
                    api_endpoint,
                    {
                        gasLimit: 600000,
                        gasPrice: ethers.utils.parseUnits("20", "gwei")
                    }
                );
                
                results.miners.push({
                    name,
                    address,
                    txHash: tx.hash,
                    stake: stake_amount,
                    endpoint: api_endpoint
                });

            } else if (type === 'validator') {
                console.log(`  🔍 Registering as VALIDATOR...`);
                
                tx = await contractWithSigner.registerValidator(
                    0, // subnet id
                    stakeWei,
                    ethers.utils.parseEther("0"), // no BTC stake
                    api_endpoint,
                    {
                        gasLimit: 600000,
                        gasPrice: ethers.utils.parseUnits("20", "gwei")
                    }
                );
                
                results.validators.push({
                    name,
                    address,
                    txHash: tx.hash,
                    stake: stake_amount,
                    endpoint: api_endpoint
                });
            }

            // Wait for transaction
            console.log(`  ⏳ Transaction: ${tx.hash}`);
            const receipt = await tx.wait();
            console.log(`  ✅ Registration successful! Block: ${receipt.blockNumber}`);
            console.log(`  ⛽ Gas used: ${receipt.gasUsed.toString()}`);

        } catch (error) {
            console.log(`  ❌ Error: ${error.message}`);
            results.errors.push({
                file,
                error: error.message
            });
        }
    }

    // Step 3: Verify registrations
    console.log("\n🔍 STEP 3: Verifying registrations...");
    
    try {
        const networkStats = await modernTensor.getNetworkStats();
        console.log(`📊 Network Stats:`);
        console.log(`  🔹 Total Miners: ${networkStats[0].toString()}`);
        console.log(`  🔹 Total Validators: ${networkStats[1].toString()}`);
        console.log(`  🔹 Total Staked: ${ethers.utils.formatEther(networkStats[2])} tCORE`);
        
        const subnetMiners = await modernTensor.getSubnetMiners(0);
        const subnetValidators = await modernTensor.getSubnetValidators(0);
        console.log(`  🔹 Subnet 0 Miners: ${subnetMiners.length}`);
        console.log(`  🔹 Subnet 0 Validators: ${subnetValidators.length}`);

        // Test getSubnet function
        console.log(`\n🧪 Testing getSubnet function...`);
        const subnetInfo = await modernTensor.getSubnet(0);
        console.log(`  📋 Subnet Name: ${subnetInfo[0].name}`);
        console.log(`  ⛏️  Miners in subnet: ${subnetInfo[2].length}`);
        console.log(`  🔍 Validators in subnet: ${subnetInfo[3].length}`);

    } catch (error) {
        console.log(`❌ Error verifying: ${error.message}`);
    }

    // Print summary
    console.log("\n" + "=" * 60);
    console.log("📊 REGISTRATION SUMMARY");
    console.log("=" * 60);
    
    console.log(`\n⛏️  MINERS REGISTERED: ${results.miners.length}`);
    results.miners.forEach((miner, i) => {
        console.log(`  ${i + 1}. ${miner.name}`);
        console.log(`     📍 ${miner.address}`);
        console.log(`     💰 ${miner.stake} tCORE`);
        console.log(`     🧾 ${miner.txHash}`);
    });

    console.log(`\n🔍 VALIDATORS REGISTERED: ${results.validators.length}`);
    results.validators.forEach((validator, i) => {
        console.log(`  ${i + 1}. ${validator.name}`);
        console.log(`     📍 ${validator.address}`);
        console.log(`     💰 ${validator.stake} tCORE`);
        console.log(`     🧾 ${validator.txHash}`);
    });

    if (results.errors.length > 0) {
        console.log(`\n❌ ERRORS: ${results.errors.length}`);
        results.errors.forEach((error, i) => {
            console.log(`  ${i + 1}. ${error.file}: ${error.error}`);
        });
    }

    // Save results
    const resultPath = path.join(__dirname, '../deployments/registration_final_results.json');
    const finalResults = {
        contractAddress,
        coreTokenAddress,
        btcTokenAddress,
        networkStats: await modernTensor.getNetworkStats(),
        registrationResults: results,
        timestamp: new Date().toISOString()
    };
    
    fs.writeFileSync(resultPath, JSON.stringify(finalResults, null, 2));
    console.log(`\n💾 Results saved to: ${resultPath}`);

    console.log("\n🎉 ENTITY REGISTRATION COMPLETED!");
    console.log(`📍 Contract: ${contractAddress}`);
    console.log(`🌐 Network: Core Test2 (Chain ID: 1114)`);
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error("❌ Registration failed:", error);
        process.exit(1);
    });