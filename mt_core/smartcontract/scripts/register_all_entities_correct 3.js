const { ethers } = require("hardhat");
const fs = require('fs');
const path = require('path');

async function main() {
    console.log("🚀 REGISTERING ALL ENTITIES WITH CORRECT SUBNET ID");
    console.log("=" * 60);

    const contractAddress = "0xAA6B8200495F7741B0B151B486aEB895fEE8c272";
    const coreTokenAddress = "0xbCfb1f5E120BE57cBBcB331D8392ae63C903dBaE";
    const subnetId = 1; // CORRECT SUBNET ID
    
    const ModernTensor = await ethers.getContractFactory("ModernTensor");
    const modernTensor = await ModernTensor.attach(contractAddress);
    
    const ERC20 = await ethers.getContractAt("IERC20", coreTokenAddress);
    
    console.log("📍 Contract:", contractAddress);
    console.log("🪙  CORE Token:", coreTokenAddress);
    console.log("🌐 Subnet ID:", subnetId);

    // Read entities
    const entitiesPath = path.join(__dirname, '../../../../subnet1_aptos/entities');
    const entityFiles = fs.readdirSync(entitiesPath).filter(f => f.endsWith('.json'));
    
    console.log(`\n📂 Found ${entityFiles.length} entities:`, entityFiles);

    const results = {
        success: [],
        skipped: [],
        failed: []
    };

    // Process each entity
    for (const file of entityFiles) {
        try {
            console.log(`\n🔄 Processing ${file}...`);
            
            const entityData = JSON.parse(fs.readFileSync(path.join(entitiesPath, file)));
            const { name, type, address, private_key, stake_amount, api_endpoint } = entityData;

            console.log(`  📋 ${name} (${type})`);
            console.log(`  📍 ${address}`);
            console.log(`  💰 ${stake_amount} tCORE`);

            // Check if already registered
            try {
                if (type === 'miner') {
                    const minerInfo = await modernTensor.getMinerInfo(address);
                    if (minerInfo.uid !== "0x0000000000000000000000000000000000000000000000000000000000000000") {
                        console.log(`  ⚠️  Already registered as miner!`);
                        console.log(`    🏷️  UID: ${minerInfo.uid}`);
                        console.log(`    🌐 Subnet: ${minerInfo.subnet_uid}`);
                        results.skipped.push({ name, address, type, reason: "already_registered" });
                        continue;
                    }
                } else {
                    const validatorInfo = await modernTensor.getValidatorInfo(address);
                    if (validatorInfo.uid !== "0x0000000000000000000000000000000000000000000000000000000000000000") {
                        console.log(`  ⚠️  Already registered as validator!`);
                        console.log(`    🏷️  UID: ${validatorInfo.uid}`);
                        console.log(`    🌐 Subnet: ${validatorInfo.subnet_uid}`);
                        results.skipped.push({ name, address, type, reason: "already_registered" });
                        continue;
                    }
                }
            } catch (error) {
                // Not registered yet, continue
            }

            // Setup wallet and contracts
            const wallet = new ethers.Wallet(private_key, ethers.provider);
            const contractWithSigner = modernTensor.connect(wallet);
            const tokenWithSigner = ERC20.connect(wallet);

            const stakeWei = ethers.utils.parseEther(stake_amount);

            // Check token balance
            const tokenBalance = await ERC20.balanceOf(address);
            if (tokenBalance.lt(stakeWei)) {
                console.log(`  ❌ Insufficient token balance`);
                results.failed.push({ name, address, type, error: "insufficient_balance" });
                continue;
            }

            // Approve tokens
            console.log(`  ✅ Approving ${stake_amount} tCORE...`);
            const approveTx = await tokenWithSigner.approve(contractAddress, stakeWei);
            await approveTx.wait();

            // Register
            let tx;
            if (type === 'miner') {
                console.log(`  ⛏️  Registering as MINER...`);
                tx = await contractWithSigner.registerMiner(
                    subnetId,
                    stakeWei,
                    ethers.utils.parseEther("0"), // no BTC
                    api_endpoint,
                    { gasLimit: 600000 }
                );
            } else {
                console.log(`  🔍 Registering as VALIDATOR...`);
                tx = await contractWithSigner.registerValidator(
                    subnetId,
                    stakeWei,
                    ethers.utils.parseEther("0"), // no BTC
                    api_endpoint,
                    { gasLimit: 600000 }
                );
            }

            console.log(`  ⏳ Transaction: ${tx.hash}`);
            const receipt = await tx.wait();

            if (receipt.status === 1) {
                console.log(`  🎉 SUCCESS! Block: ${receipt.blockNumber}`);
                console.log(`  ⛽ Gas used: ${receipt.gasUsed.toString()}`);
                
                results.success.push({
                    name,
                    address,
                    type,
                    txHash: tx.hash,
                    blockNumber: receipt.blockNumber,
                    gasUsed: receipt.gasUsed.toString(),
                    stake: stake_amount
                });
            } else {
                console.log(`  ❌ Transaction failed`);
                results.failed.push({ name, address, type, error: "transaction_failed" });
            }

        } catch (error) {
            console.log(`  ❌ Error: ${error.message}`);
            results.failed.push({ 
                name: entityData?.name || file, 
                address: entityData?.address || "unknown", 
                type: entityData?.type || "unknown",
                error: error.message 
            });
        }
    }

    // Final verification
    console.log("\n🔍 FINAL VERIFICATION");
    console.log("=" * 40);
    
    try {
        const networkStats = await modernTensor.getNetworkStats();
        console.log(`📊 Network Stats:`);
        console.log(`  🔹 Total Miners: ${networkStats[0].toString()}`);
        console.log(`  🔹 Total Validators: ${networkStats[1].toString()}`);
        console.log(`  🔹 Total Staked: ${ethers.utils.formatEther(networkStats[2])} tCORE`);
        
        const subnetMiners = await modernTensor.getSubnetMiners(subnetId);
        const subnetValidators = await modernTensor.getSubnetValidators(subnetId);
        console.log(`  🔹 Subnet ${subnetId} Miners: ${subnetMiners.length}`);
        console.log(`  🔹 Subnet ${subnetId} Validators: ${subnetValidators.length}`);

        // Test getSubnet function
        const subnetInfo = await modernTensor.getSubnet(subnetId);
        console.log(`\n🧪 getSubnet(${subnetId}) Test:`);
        console.log(`  📋 Name: ${subnetInfo[0].name}`);
        console.log(`  👤 Owner: ${subnetInfo[0].owner_addr}`);
        console.log(`  ⛏️  Miners: ${subnetInfo[2].length}`);
        console.log(`  🔍 Validators: ${subnetInfo[3].length}`);

    } catch (error) {
        console.log(`❌ Verification error: ${error.message}`);
    }

    // Print final summary
    console.log("\n" + "=" * 60);
    console.log("📊 FINAL REGISTRATION SUMMARY");
    console.log("=" * 60);
    
    console.log(`\n✅ SUCCESSFUL REGISTRATIONS: ${results.success.length}`);
    results.success.forEach((entity, i) => {
        console.log(`  ${i + 1}. ${entity.name} (${entity.type})`);
        console.log(`     📍 ${entity.address}`);
        console.log(`     💰 ${entity.stake} tCORE`);
        console.log(`     🧾 ${entity.txHash}`);
    });

    console.log(`\n⚠️  SKIPPED: ${results.skipped.length}`);
    results.skipped.forEach((entity, i) => {
        console.log(`  ${i + 1}. ${entity.name} (${entity.type}): ${entity.reason}`);
    });

    console.log(`\n❌ FAILED: ${results.failed.length}`);
    results.failed.forEach((entity, i) => {
        console.log(`  ${i + 1}. ${entity.name} (${entity.type}): ${entity.error}`);
    });

    // Save results
    const finalResults = {
        contractAddress,
        coreTokenAddress,
        subnetId,
        timestamp: new Date().toISOString(),
        results
    };
    
    const resultPath = path.join(__dirname, '../deployments/final_registration_results.json');
    fs.writeFileSync(resultPath, JSON.stringify(finalResults, null, 2));
    console.log(`\n💾 Results saved to: ${resultPath}`);

    console.log("\n🎉 REGISTRATION PROCESS COMPLETED!");
    console.log(`📍 Contract: ${contractAddress}`);
    console.log(`🌐 Network: Core Test2 (Chain ID: 1114)`);
    console.log(`🎯 Subnet: ${subnetId}`);
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error("❌ Process failed:", error);
        process.exit(1);
    });