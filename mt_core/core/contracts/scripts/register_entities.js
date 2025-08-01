const { ethers } = require("hardhat");
const fs = require("fs");
const path = require("path");

// New contract address
const CONTRACT_ADDRESS = "0x5f96BEA61E4ad2222c4B575fD6FFdCEd4DC04358";

// Entities directory
const ENTITIES_DIR = path.join(__dirname, "../../../../../subnet1_aptos/entities");

async function registerEntity(entityFile, contract) {
    console.log(`\n📝 Registering ${entityFile}...`);
    
    // Read entity data
    const entityPath = path.join(ENTITIES_DIR, entityFile);
    const entityData = JSON.parse(fs.readFileSync(entityPath, 'utf8'));
    
    // Create wallet for this entity
    const wallet = new ethers.Wallet(entityData.private_key, ethers.provider);
    
    // Connect contract with entity's wallet
    const contractWithSigner = contract.connect(wallet);
    
    console.log(`  Address: ${entityData.address}`);
    console.log(`  Type: ${entityData.type}`);
    console.log(`  Stake Amount: ${entityData.stake_amount} CORE`);
    
    try {
        let tx;
        const stakeAmount = ethers.utils.parseEther("0"); // Use 0 for testing
        const uid = ethers.utils.keccak256(ethers.utils.toUtf8Bytes(entityData.name));
        
        // Get token contract and approve spending
        const tokenAddress = await contract.coreToken();
        const Token = await ethers.getContractFactory("MockERC20");
        const tokenContract = Token.attach(tokenAddress);
        const tokenWithSigner = tokenContract.connect(wallet);
        
        // Approve contract to spend tokens
        const approveTx = await tokenWithSigner.approve(contract.address, ethers.utils.parseEther("1000"));
        await approveTx.wait();
        console.log(`  ✅ Approved token spending`);
        
        if (entityData.type === "miner") {
            // Register as miner
            // function registerMiner(bytes32 uid, uint64 subnetUid, uint256 stakeAmount, string calldata apiEndpoint)
            tx = await contractWithSigner.registerMiner(
                uid,
0, // Use subnet 0 (default subnet)
                stakeAmount,
                entityData.api_endpoint || "http://localhost:8000"
            );
            console.log(`  ⛏️ Miner registration tx: ${tx.hash}`);
            
        } else if (entityData.type === "validator") {
            // Register as validator
            // function registerValidator(bytes32 uid, uint64 subnetUid, uint256 stakeAmount, string calldata apiEndpoint)
            tx = await contractWithSigner.registerValidator(
                uid,
0, // Use subnet 0 (default subnet)
                stakeAmount,
                entityData.api_endpoint || "http://localhost:8001"
            );
            console.log(`  ✅ Validator registration tx: ${tx.hash}`);
        }
        
        // Wait for transaction
        const receipt = await tx.wait();
        console.log(`  ✅ Registration confirmed in block ${receipt.blockNumber}`);
        
        return {
            success: true,
            entity: entityData.name,
            type: entityData.type,
            address: entityData.address,
            txHash: tx.hash,
            blockNumber: receipt.blockNumber
        };
        
    } catch (error) {
        console.log(`  ❌ Registration failed: ${error.message}`);
        return {
            success: false,
            entity: entityData.name,
            type: entityData.type,
            address: entityData.address,
            error: error.message
        };
    }
}

async function main() {
    console.log("🚀 RE-REGISTERING ALL ENTITIES");
    console.log("===============================================");
    console.log(`📋 Contract Address: ${CONTRACT_ADDRESS}`);
    
    try {
        // Get contract
        const ModernTensor = await ethers.getContractFactory("ModernTensor");
        const contract = ModernTensor.attach(CONTRACT_ADDRESS);
        
        const network = await ethers.provider.getNetwork();
        console.log(`🌐 Network: ${network.name} (Chain ID: ${network.chainId})`);
        
        // Read all entity files
        const entityFiles = fs.readdirSync(ENTITIES_DIR)
            .filter(file => file.endsWith('.json'))
            .sort(); // Process in order
            
        console.log(`📁 Found ${entityFiles.length} entities to register`);
        
        const results = [];
        
        // Register each entity
        for (const entityFile of entityFiles) {
            const result = await registerEntity(entityFile, contract);
            results.push(result);
            
            // Wait a bit between registrations
            await new Promise(resolve => setTimeout(resolve, 2000));
        }
        
        console.log("\n🎉 REGISTRATION SUMMARY");
        console.log("===============================================");
        
        const successful = results.filter(r => r.success);
        const failed = results.filter(r => !r.success);
        
        console.log(`✅ Successful: ${successful.length}`);
        console.log(`❌ Failed: ${failed.length}`);
        
        if (successful.length > 0) {
            console.log("\n✅ SUCCESSFUL REGISTRATIONS:");
            successful.forEach(r => {
                console.log(`  • ${r.entity} (${r.type}) - ${r.address}`);
                console.log(`    Tx: ${r.txHash} | Block: ${r.blockNumber}`);
            });
        }
        
        if (failed.length > 0) {
            console.log("\n❌ FAILED REGISTRATIONS:");
            failed.forEach(r => {
                console.log(`  • ${r.entity} (${r.type}) - ${r.address}`);
                console.log(`    Error: ${r.error}`);
            });
        }
        
        // Save results
        const registrationReport = {
            contractAddress: CONTRACT_ADDRESS,
            network: network.name,
            chainId: network.chainId,
            timestamp: new Date().toISOString(),
            totalEntities: entityFiles.length,
            successful: successful.length,
            failed: failed.length,
            results: results
        };
        
        fs.writeFileSync(
            'registration-report.json',
            JSON.stringify(registrationReport, null, 2)
        );
        console.log("\n💾 Registration report saved to registration-report.json");
        
    } catch (error) {
        console.error("💥 Registration process failed:", error.message);
        process.exit(1);
    }
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });