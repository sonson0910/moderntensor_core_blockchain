const { ethers } = require("hardhat");

async function main() {
    console.log("🔍 Verifying ModernTensorAI_Optimized on Core Testnet...");
    console.log("=" .repeat(60));

    // Contract deployment info
    const contractAddress = "0x56C2F2d0914DF10CE048e07EF1eCbac09AF80cd2";
    const coreTokenAddress = "0xEe46b1863b638667F50FAcf1db81eD4074991310";
    const btcTokenAddress = "0xA92f0E66Ca8CeffBcd6f09bE2a8aA489c1604A0c";
    
    // Constructor arguments
    const constructorArgs = [
        coreTokenAddress,                              // coreToken
        btcTokenAddress,                               // btcToken  
        3,                                            // minConsensusValidators
        6667,                                         // consensusThreshold (66.67%)
        ethers.utils.parseEther("100").toString(),    // minMinerStake (100 tokens)
        ethers.utils.parseEther("1000").toString(),   // minValidatorStake (1000 tokens)
        15000                                         // btcBoostMultiplier (150%)
    ];

    console.log("📋 Contract Information:");
    console.log(`   Address: ${contractAddress}`);
    console.log(`   CORE Token: ${coreTokenAddress}`);
    console.log(`   BTC Token: ${btcTokenAddress}`);
    console.log("");

    console.log("🔧 Constructor Arguments:");
    constructorArgs.forEach((arg, index) => {
        console.log(`   [${index}]: ${arg}`);
    });
    console.log("");

    try {
        console.log("⏳ Starting contract verification...");
        
        // Run hardhat verify
        await hre.run("verify:verify", {
            address: contractAddress,
            constructorArguments: constructorArgs,
        });

        console.log("✅ Contract verification successful!");
        console.log(`🔗 View verified contract: https://scan.test.btcs.network/address/${contractAddress}`);
        
    } catch (error) {
        if (error.message.includes("Already Verified")) {
            console.log("✅ Contract is already verified!");
            console.log(`🔗 View contract: https://scan.test.btcs.network/address/${contractAddress}`);
        } else {
            console.error("❌ Verification failed:");
            console.error(error.message);
            
            console.log("");
            console.log("🔧 Manual Verification Command:");
            console.log(`npx hardhat verify --network core_testnet ${contractAddress} ${constructorArgs.map(arg => `"${arg}"`).join(' ')}`);
        }
    }

    console.log("");
    console.log("📊 Contract Features:");
    console.log("   ✅ Bitcoin SPV Verification");
    console.log("   ✅ AI Model Validation");
    console.log("   ✅ Gas Optimized Operations");
    console.log("   ✅ Role-based Access Control");
    console.log("   ✅ Emergency Pause Mechanism");
    console.log("");
    
    console.log("🎯 Next Steps:");
    console.log("   1. Interact with verified contract");
    console.log("   2. Register first miners and validators");
    console.log("   3. Create AI training subnets");
    console.log("   4. Test consensus mechanisms");
    console.log("   5. Deploy to mainnet when ready");
}

main()
    .then(() => {
        console.log("");
        console.log("🚀 Verification process completed!");
        process.exit(0);
    })
    .catch((error) => {
        console.error("❌ Verification failed:");
        console.error(error);
        process.exit(1);
    }); 