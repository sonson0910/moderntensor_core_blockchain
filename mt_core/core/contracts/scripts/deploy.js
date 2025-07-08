const { ethers, upgrades } = require("hardhat");

async function main() {
  console.log("🚀 Deploying ModernTensor to Core blockchain...");
  
  // Get the contract factory
  const ModernTensor = await ethers.getContractFactory("ModernTensor");
  
  // Core token address - need to update with actual address
  const CORE_TOKEN_ADDRESS = process.env.CORE_TOKEN_ADDRESS || "0x40375C92d9FAf44d2f9db9Bd9ba41a3317a2404f"; // CORE token on Core testnet
  
  console.log("📋 Deployment parameters:");
  console.log("- Core Token Address:", CORE_TOKEN_ADDRESS);
  console.log("- Network:", hre.network.name);
  
  // Deploy the contract
  console.log("⏳ Deploying contract...");
  const modernTensor = await ModernTensor.deploy(CORE_TOKEN_ADDRESS);
  
  // Wait for deployment
  await modernTensor.deployed();
  
  console.log("✅ ModernTensor deployed to:", modernTensor.address);
  
  // Initialize with first subnet
  console.log("⏳ Creating default subnet...");
  const createSubnetTx = await modernTensor.createSubnet(
    1, // subnet ID
    "Default AI Training Subnet",
    "Default subnet for AI model training on Core blockchain",
    1000, // max miners
    100, // max validators
    86400, // immunity period (24 hours)
    ethers.utils.parseEther("10"), // min miner stake (10 CORE)
    ethers.utils.parseEther("50"), // min validator stake (50 CORE)
    ethers.utils.parseEther("1") // registration cost (1 CORE)
  );
  
  await createSubnetTx.wait();
  console.log("✅ Default subnet created");
  
  // Verify staking tiers
  console.log("📊 Verifying staking tiers...");
  const tiers = await modernTensor.getStakingTiers();
  console.log("Staking tiers:", tiers.map(tier => ({
    name: tier.name,
    minCoreRatio: tier.minCoreRatio.toString(),
    multiplier: tier.multiplier.toString()
  })));
  
  console.log("\n🎉 Deployment completed successfully!");
  console.log("📝 Contract Address:", modernTensor.address);
  console.log("🔗 Network:", hre.network.name);
  console.log("⛽ Gas Used:", (await modernTensor.deployTransaction.wait()).gasUsed.toString());
  
  // Save deployment info
  const deploymentInfo = {
    address: modernTensor.address,
    network: hre.network.name,
    blockNumber: modernTensor.deployTransaction.blockNumber,
    transactionHash: modernTensor.deployTransaction.hash,
    coreTokenAddress: CORE_TOKEN_ADDRESS,
    timestamp: new Date().toISOString()
  };
  
  const fs = require("fs");
  const path = require("path");
  
  // Create deployments directory if it doesn't exist
  const deploymentsDir = path.join(__dirname, "../deployments");
  if (!fs.existsSync(deploymentsDir)) {
    fs.mkdirSync(deploymentsDir, { recursive: true });
  }
  
  // Save deployment info
  fs.writeFileSync(
    path.join(deploymentsDir, `${hre.network.name}-deployment.json`),
    JSON.stringify(deploymentInfo, null, 2)
  );
  
  console.log("📄 Deployment info saved to deployments/" + hre.network.name + "-deployment.json");
  
  // Instructions for next steps
  console.log("\n📋 Next steps:");
  console.log("1. Verify the contract on Core scan (if on mainnet)");
  console.log("2. Update SDK configuration with contract address");
  console.log("3. Test miner and validator registration");
  console.log("4. Set up Bitcoin staking integration");
  
  if (hre.network.name !== "hardhat") {
    console.log("\n🔍 To verify the contract, run:");
    console.log(`npx hardhat verify --network ${hre.network.name} ${modernTensor.address} "${CORE_TOKEN_ADDRESS}"`);
  }
  
  return {
    modernTensor,
    deploymentInfo
  };
}

// We recommend this pattern to be able to use async/await everywhere
// and properly handle errors.
main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("❌ Deployment failed:", error);
    process.exit(1);
  }); 