const { ethers } = require("hardhat");
const fs = require('fs');
const path = require('path');

async function main() {
    console.log("🚀 REGISTERING ENTITIES ON MODERNTENSOR CONTRACT");
    console.log("=" * 60);

    // Contract address on test2
    const contractAddress = "0x9c5B5d1082FEF8766aA9Ef28a1237aC5ae607841";
    
    // Get contract instance
    const ModernTensor = await ethers.getContractFactory("ModernTensor");
    const modernTensor = await ModernTensor.attach(contractAddress);
    
    console.log("📍 Contract Address:", contractAddress);
    console.log("🌐 Network: CoreDAO Test2");

    // Path to entities folder
    const entitiesPath = path.join(__dirname, '../../../../subnet1_aptos/entities');
    
    // Read all entity files
    const entityFiles = fs.readdirSync(entitiesPath).filter(f => f.endsWith('.json'));
    console.log(`\n📂 Found ${entityFiles.length} entity files:`, entityFiles);

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
                api_endpoint,
                subnet_id = 0
            } = entityData;

            console.log(`  📋 Name: ${name}`);
            console.log(`  🏷️  Type: ${type}`);
            console.log(`  📍 Address: ${address}`);
            console.log(`  💰 Stake: ${stake_amount} CORE`);
            console.log(`  🌐 Endpoint: ${api_endpoint}`);

            // Create wallet from private key
            const wallet = new ethers.Wallet(private_key, ethers.provider);
            const contractWithSigner = modernTensor.connect(wallet);

            // Convert stake amount to wei
            const stakeWei = ethers.utils.parseEther(stake_amount);
            
            // Bitcoin stake (set to 0 for now)
            const btcStake = ethers.utils.parseEther("0");

            // Check current balance
            const balance = await wallet.getBalance();
            console.log(`  💳 Current Balance: ${ethers.utils.formatEther(balance)} CORE`);

            if (balance.lt(stakeWei)) {
                console.log(`  ⚠️  Insufficient balance for stake. Needed: ${stake_amount} CORE`);
                results.errors.push({
                    file,
                    error: "Insufficient balance",
                    needed: stake_amount,
                    available: ethers.utils.formatEther(balance)
                });
                continue;
            }

            // Register based on type
            let tx;
            if (type === 'miner') {
                console.log(`  ⛏️  Registering as MINER...`);
                
                // Call registerMiner
                tx = await contractWithSigner.registerMiner(
                    subnet_id,
                    stakeWei,
                    btcStake,
                    api_endpoint,
                    {
                        gasLimit: 500000,
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
                
                // Call registerValidator
                tx = await contractWithSigner.registerValidator(
                    subnet_id,
                    stakeWei,
                    btcStake,
                    api_endpoint,
                    {
                        gasLimit: 500000,
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
            console.log(`  ⏳ Transaction hash: ${tx.hash}`);
            const receipt = await tx.wait();
            console.log(`  ✅ Registration successful! Block: ${receipt.blockNumber}`);
            console.log(`  ⛽ Gas used: ${receipt.gasUsed.toString()}`);

        } catch (error) {
            console.log(`  ❌ Error registering ${file}:`, error.message);
            results.errors.push({
                file,
                error: error.message
            });
        }
    }

    // Print summary
    console.log("\n" + "=" * 60);
    console.log("📊 REGISTRATION SUMMARY");
    console.log("=" * 60);
    
    console.log(`\n⛏️  MINERS REGISTERED: ${results.miners.length}`);
    results.miners.forEach((miner, i) => {
        console.log(`  ${i + 1}. ${miner.name}`);
        console.log(`     📍 Address: ${miner.address}`);
        console.log(`     💰 Stake: ${miner.stake} CORE`);
        console.log(`     🧾 TX: ${miner.txHash}`);
    });

    console.log(`\n🔍 VALIDATORS REGISTERED: ${results.validators.length}`);
    results.validators.forEach((validator, i) => {
        console.log(`  ${i + 1}. ${validator.name}`);
        console.log(`     📍 Address: ${validator.address}`);
        console.log(`     💰 Stake: ${validator.stake} CORE`);
        console.log(`     🧾 TX: ${validator.txHash}`);
    });

    if (results.errors.length > 0) {
        console.log(`\n❌ ERRORS: ${results.errors.length}`);
        results.errors.forEach((error, i) => {
            console.log(`  ${i + 1}. ${error.file}: ${error.error}`);
        });
    }

    // Get network stats after registration
    console.log("\n🌐 NETWORK STATS AFTER REGISTRATION:");
    try {
        const networkStats = await modernTensor.getNetworkStats();
        console.log(`  🔹 Total Miners: ${networkStats[0].toString()}`);
        console.log(`  🔹 Total Validators: ${networkStats[1].toString()}`);
        console.log(`  🔹 Total Staked: ${ethers.utils.formatEther(networkStats[2])} CORE`);
        
        // Get subnet info
        const subnetMiners = await modernTensor.getSubnetMiners(0);
        const subnetValidators = await modernTensor.getSubnetValidators(0);
        console.log(`  🔹 Subnet 0 Miners: ${subnetMiners.length}`);
        console.log(`  🔹 Subnet 0 Validators: ${subnetValidators.length}`);

    } catch (error) {
        console.log(`  ❌ Error fetching network stats: ${error.message}`);
    }

    // Save results
    const resultPath = path.join(__dirname, '../deployments/registration_results.json');
    fs.writeFileSync(resultPath, JSON.stringify(results, null, 2));
    console.log(`\n💾 Results saved to: ${resultPath}`);

    console.log("\n🎉 ENTITY REGISTRATION COMPLETED!");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error("❌ Registration failed:", error);
        process.exit(1);
    });