import hardhat from "hardhat";
import { writeFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const { ethers } = hardhat;
const hre = hardhat;
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log("Deploying contracts with account:", deployer.address);

  // Token parameters
  const totalSupply = hre.ethers.parseUnits("1000000000", 8);
  const totalRewardEmission = hre.ethers.parseUnits("1000000", 8);

  // Deploy MTNSRTEST01 token
  const TokenFactory = await hre.ethers.getContractFactory("MTNSRTEST01");
  const token = await TokenFactory.deploy(totalSupply);
  await token.waitForDeployment();
  console.log("MTNSRTEST01 deployed to:", token.target);

  // Deploy Governance
  const GovernanceFactory = await hre.ethers.getContractFactory("Governance");
  const governance = await GovernanceFactory.deploy(token.target);
  await governance.waitForDeployment();
  console.log("Governance deployed to:", governance.target);

  // Deploy Treasury
  const TreasuryFactory = await hre.ethers.getContractFactory("Treasury");
  const treasury = await TreasuryFactory.deploy(token.target);
  await treasury.waitForDeployment();
  console.log("Treasury deployed to:", treasury.target);

  // Deploy Vesting
  const VestingFactory = await hre.ethers.getContractFactory("Vesting");
  const vesting = await VestingFactory.deploy(token.target);
  await vesting.waitForDeployment();
  console.log("Vesting deployed to:", vesting.target);

  // Deploy RewardEmission
  const EmissionFactory = await hre.ethers.getContractFactory("RewardEmission");
  const rewardEmission = await EmissionFactory.deploy(
    token.target,
    totalRewardEmission,
    60,   // secondsPerPeriod
    240   // secondsPerHalving
  );
  await rewardEmission.waitForDeployment();
  console.log("RewardEmission deployed to:", rewardEmission.target);

  // Deploy RewardDistribution
  const DistributorFactory = await hre.ethers.getContractFactory("RewardDistribution");
  const rewardDistribution = await DistributorFactory.deploy(token.target);
  await rewardDistribution.waitForDeployment();
  console.log("RewardDistribution deployed to:", rewardDistribution.target);

  // Save addresses to .env
  const envPath = join(__dirname, "../.env");
  const envData = `
TOKEN_ADDRESS=${token.target}
REWARD_EMISSION_ADDRESS=${rewardEmission.target}
REWARD_DISTRIBUTION_ADDRESS=${rewardDistribution.target}
GOVERNANCE_ADDRESS=${governance.target}
TREASURY_ADDRESS=${treasury.target}
VESTING_ADDRESS=${vesting.target}
`;
  writeFileSync(envPath, envData, { flag: "a" });
  console.log("Contract addresses saved to .env");

  // Mint token to deployer
  await token.mint(deployer.address, totalSupply);

  // Approve + fund vesting & treasury
  const vestingAmount = hre.ethers.parseUnits("100000", 8);
  const treasuryAmount = hre.ethers.parseUnits("200000", 8);

  await token.approve(vesting.target, vestingAmount);
  await vesting.initializeVesting(vestingAmount);

  await token.approve(treasury.target, treasuryAmount);
  await treasury.depositToTreasury(treasuryAmount);
  console.log("✅ Vesting and Treasury funded");

  // Setup vesting schedule
  const totalVestingAmount = ethers.parseUnits("8000", 8);
  const duration = 60 * 60 * 24 * 7; // 7 days
  const startTime = Math.floor(Date.now() / 1000) + 60; // starts in 1 min

  const recipient_address1 = process.env.RECIPIENT_ADDRESS_1;
  const recipient_address2 = process.env.RECIPIENT_ADDRESS_2;

  await vesting.setupVesting(recipient_address1, totalVestingAmount, startTime, duration);
  console.log("✅ Vesting schedule created for:", recipient_address1);

  await vesting.setupVesting(recipient_address2, totalVestingAmount, startTime, duration);
  console.log("✅ Vesting schedule created for:", recipient_address2);

  // Link reward emission & distribution
  await rewardEmission.setRewardDistributor(rewardDistribution.target);
  await rewardDistribution.setRewardEmission(rewardEmission.target);
  console.log("✅ Linked RewardEmission and RewardDistribution");

  // Approve and initialize vault
  await token.approve(rewardEmission.target, totalRewardEmission);
  await rewardEmission.initializeVaultAndEpoch(totalRewardEmission);
  console.log("✅ Vault initialized with", totalRewardEmission.toString(), "tokens");

  // Show token balances
  const addressesToCheck = {
    Deployer: deployer.address,
    RewardEmission: rewardEmission.target,
    RewardDistribution: rewardDistribution.target,
    Treasury: treasury.target,
    Vesting: vesting.target,
    Governance: governance.target,
  };

  console.log("\n📊 Token balances after deployment:");
  for (const [name, addr] of Object.entries(addressesToCheck)) {
    const balance = await token.balanceOf(addr);
    console.log(`- ${name}: ${hre.ethers.formatUnits(balance, 8)} MTNSRTEST01`);
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
