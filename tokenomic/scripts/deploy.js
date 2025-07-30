const { ethers } = require("hardhat");

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log("Deploying with account:", deployer.address);

  // Deploy MTNSRTEST01
  const MTNSRTEST01 = await ethers.getContractFactory("MTNSRTEST01");
  const token = await MTNSRTEST01.deploy(ethers.utils.parseUnits("1000000000", 8)); // 1B tokens, 8 decimals
  await token.deployed();
  console.log("MTNSRTEST01 deployed to:", token.address);

  // Deploy Vesting
  const Vesting = await ethers.getContractFactory("Vesting");
  const vesting = await Vesting.deploy(token.address);
  await vesting.deployed();
  console.log("Vesting deployed to:", vesting.address);

  // Deploy RewardEmission
  const RewardEmission = await ethers.getContractFactory("RewardEmission");
  const rewardEmission = await RewardEmission.deploy(
    token.address,
    ethers.utils.parseUnits("1000000000", 8), // totalSupply
    5 * 24 * 60 * 60, // 5 days per period
    4 * 365 * 24 * 60 * 60 // 4 years per halving
  );
  await rewardEmission.deployed();
  console.log("RewardEmission deployed to:", rewardEmission.address);

  // Deploy Governance
  const Governance = await ethers.getContractFactory("Governance");
  const governance = await Governance.deploy(token.address);
  await governance.deployed();
  console.log("Governance deployed to:", governance.address);

  // Deploy Treasury
  const Treasury = await ethers.getContractFactory("Treasury");
  const treasury = await Treasury.deploy(token.address);
  await treasury.deployed();
  console.log("Treasury deployed to:", treasury.address);

  // Transfer tokens to Vesting, RewardEmission, and Treasury
  await token.transfer(vesting.address, ethers.utils.parseUnits("400000000", 8));
  await token.transfer(rewardEmission.address, ethers.utils.parseUnits("400000000", 8));
  await token.transfer(treasury.address, ethers.utils.parseUnits("200000000", 8));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});