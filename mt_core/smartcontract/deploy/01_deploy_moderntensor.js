const { ethers } = require("hardhat");

module.exports = async ({ getNamedAccounts, deployments }) => {
  const { deploy, log } = deployments;
  const { deployer } = await getNamedAccounts();
  const chainId = await ethers.provider.getNetwork().then(n => n.chainId);

  log("----------------------------------------------------");
  log(`Deploying ModernTensor to chainId: ${chainId}`);
  log("----------------------------------------------------");

  // Deploy mock CORE token for testing on hardhat network
  let coreTokenAddress;
  if (chainId === 31337) {
    // Deploy mock CORE token
    const mockCoreToken = await deploy("MockCoreToken", {
      from: deployer,
      args: ["Core Token", "CORE"],
      log: true,
    });
    coreTokenAddress = mockCoreToken.address;
    log(`Mock CORE token deployed at: ${coreTokenAddress}`);
  } else {
    // Use real CORE token addresses
    if (chainId === 1115) {
      // Core Testnet
      coreTokenAddress = "0x2F7E209E0F7B8F0C2B7e8D8C5D5A5B5C5D5E5F5A"; // Example testnet CORE address
    } else if (chainId === 1116) {
      // Core Mainnet
      coreTokenAddress = "0x40375C92d9FAf44d2f9db9Bd9ba41a3317a2404f"; // Example mainnet CORE address
    } else {
      throw new Error(`Unsupported chain ID: ${chainId}`);
    }
    log(`Using existing CORE token at: ${coreTokenAddress}`);
  }

  // Deploy ModernTensor contract
  const modernTensor = await deploy("ModernTensor", {
    from: deployer,
    args: [coreTokenAddress],
    log: true,
    waitConfirmations: chainId === 31337 ? 1 : 5,
  });

  log(`ModernTensor deployed at: ${modernTensor.address}`);
  log("----------------------------------------------------");

  // Create default subnet if on local network
  if (chainId === 31337) {
    const contract = await ethers.getContractAt("ModernTensor", modernTensor.address);
    
    try {
      const tx = await contract.createSubnet("Default AI Training Subnet");
      await tx.wait();
      log("Default subnet created successfully");
    } catch (error) {
      log(`Error creating default subnet: ${error.message}`);
    }
  }

  // Log deployment info
  log("----------------------------------------------------");
  log("Deployment Summary:");
  log(`Network: ${chainId === 31337 ? "Hardhat" : chainId === 1115 ? "Core Testnet" : "Core Mainnet"}`);
  log(`ModernTensor: ${modernTensor.address}`);
  log(`CORE Token: ${coreTokenAddress}`);
  log(`Deployer: ${deployer}`);
  log("----------------------------------------------------");
};

module.exports.tags = ["all", "moderntensor"]; 