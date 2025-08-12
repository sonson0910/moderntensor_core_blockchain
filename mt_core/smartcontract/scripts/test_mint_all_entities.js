const { ethers } = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
    console.log("🧪 TESTING MINT FOR ALL ENTITIES");
    console.log("=" * 60);

    // Token addresses from deployment
    const coreTokenAddress = "0xbCfb1f5E120BE57cBBcB331D8392ae63C903dBaE";
    const btcTokenAddress = "0x8680Af4385d74979D12bCf56dBcAE8AE20B706c8";
    
    // Get possible deployer accounts (try multiple)
    const deployerKeys = [
        "a07b6e0db803f9a21ffd1001c76b0aa0b313aaba8faab8c771af47301c4452b4", // Original deployer
        "e9c03148c011d553d43b485d73b1407d24f1498a664f782dc0204e524855be4e", // miner_1 key
        "3ace434e2cd05cd0e614eb5d423cf04e4b925c17db9869e9c598851f88f52840", // miner_2 key
    ];
    
    // Load all entities
    const entitiesDir = path.join(__dirname, "../../../../subnet1_aptos/entities");
    const entityFiles = fs.readdirSync(entitiesDir).filter(f => f.endsWith('.json'));
    
    console.log(`📁 Found ${entityFiles.length} entity files`);
    
    // Load entities data
    const entities = [];
    for (const file of entityFiles) {
        const entityPath = path.join(entitiesDir, file);
        const entityData = JSON.parse(fs.readFileSync(entityPath, 'utf8'));
        entities.push({ ...entityData, file });
    }
    
    console.log("\n📋 Entities to test:");
    entities.forEach(entity => {
        console.log(`  • ${entity.name}: ${entity.address}`);
    });
    
    // Try each deployer key
    for (let i = 0; i < deployerKeys.length; i++) {
        const deployerKey = deployerKeys[i];
        const deployer = new ethers.Wallet(deployerKey, ethers.provider);
        
        console.log(`\n🔑 Testing with deployer ${i + 1}: ${deployer.address}`);
        
        try {
            // Get contract instances
            const MockToken = await ethers.getContractFactory("MockCoreToken", deployer);
            const coreToken = MockToken.attach(coreTokenAddress);
            const btcToken = MockToken.attach(btcTokenAddress);
            
            // Check if this deployer is the owner
            try {
                const owner = await coreToken.owner();
                console.log(`  📋 Contract owner: ${owner}`);
                console.log(`  🔍 Is deployer owner: ${owner.toLowerCase() === deployer.address.toLowerCase()}`);
                
                if (owner.toLowerCase() !== deployer.address.toLowerCase()) {
                    console.log(`  ❌ Not the owner, skipping...`);
                    continue;
                }
            } catch (error) {
                console.log(`  ❌ Cannot check owner: ${error.message}`);
                continue;
            }
            
            console.log(`  ✅ Found contract owner! Testing mint...`);
            
            // Test mint for each entity
            const mintAmount = ethers.utils.parseEther("5"); // 5 tokens
            
            for (const entity of entities) {
                console.log(`\n    🎯 Testing mint for ${entity.name} (${entity.address}):`);
                
                try {
                    // Check current balance
                    const currentBalance = await coreToken.balanceOf(entity.address);
                    console.log(`      💰 Current CORE balance: ${ethers.utils.formatEther(currentBalance)}`);
                    
                    // Try to mint
                    console.log(`      ⏳ Minting 5 CORE tokens...`);
                    const mintTx = await coreToken.mint(entity.address, mintAmount);
                    await mintTx.wait();
                    
                    // Check new balance
                    const newBalance = await coreToken.balanceOf(entity.address);
                    console.log(`      ✅ New CORE balance: ${ethers.utils.formatEther(newBalance)}`);
                    console.log(`      📈 Gained: ${ethers.utils.formatEther(newBalance.sub(currentBalance))} CORE`);
                    
                } catch (error) {
                    console.log(`      ❌ Mint failed: ${error.message}`);
                }
            }
            
            // If we got here, this deployer worked - no need to try others
            console.log(`\n🎉 Successfully minted with deployer: ${deployer.address}`);
            break;
            
        } catch (error) {
            console.log(`  ❌ Failed with deployer ${i + 1}: ${error.message}`);
        }
    }
    
    console.log("\n📊 Final balances check:");
    
    // Final balance check with any deployer (just for reading)
    const reader = new ethers.Wallet(deployerKeys[0], ethers.provider);
    const MockToken = await ethers.getContractFactory("MockCoreToken", reader);
    const coreToken = MockToken.attach(coreTokenAddress);
    
    for (const entity of entities) {
        try {
            const balance = await coreToken.balanceOf(entity.address);
            console.log(`  ${entity.name}: ${ethers.utils.formatEther(balance)} CORE (${entity.address})`);
        } catch (error) {
            console.log(`  ${entity.name}: Error reading balance`);
        }
    }
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
