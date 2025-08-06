import hardhat from "hardhat";
import { appendFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const { ethers } = hardhat;
const hre = hardhat;
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log("Deploying contracts with account:", deployer.address);

  // Check native token balance (ETH on Hardhat, CORE on CoreDAO Testnet)
  const nativeBalance = await ethers.provider.getBalance(deployer.address);
  console.log("Native token balance:", ethers.formatEther(nativeBalance), "CORE/ETH");

  // Token parameters
  const totalSupply = ethers.parseUnits("1000000000", 8); // 1 billion tokens
  const totalRewardEmission = ethers.parseUnits("1000000", 8); // 1 million tokens
  const vestingAmount = ethers.parseUnits("1000000", 8); // 1 million tokens
  const treasuryAmount = ethers.parseUnits("2000000", 8); // 2 million tokens
  const totalVestingAmount = ethers.parseUnits("8000", 8); // 8000 tokens
  const duration = 60 * 60 * 24 * 7; // 7 days
  const currentBlock = await ethers.provider.getBlock("latest");
  const currentTimestamp = currentBlock.timestamp;
  const startTime = currentTimestamp + 300; // Starts 5 minutes from current block
  console.log("Current block timestamp:", currentTimestamp, "Start time:", startTime);

  // Deploy MTNSRTEST01 token
  const TokenFactory = await ethers.getContractFactory("MTNSRTEST01");
  const token = await TokenFactory.deploy(totalSupply);
  await token.waitForDeployment();
  console.log("MTNSRTEST01 deployed at:", token.target);

  // Deploy Governance
  const GovernanceFactory = await ethers.getContractFactory("Governance");
  const governance = await GovernanceFactory.deploy(token.target);
  await governance.waitForDeployment();
  console.log("Governance deployed at:", governance.target);

  // Deploy Treasury
  const TreasuryFactory = await ethers.getContractFactory("Treasury");
  const treasury = await TreasuryFactory.deploy(token.target);
  await treasury.waitForDeployment();
  console.log("Treasury deployed at:", treasury.target);

  // Deploy Vesting
  const VestingFactory = await ethers.getContractFactory("Vesting");
  const vesting = await VestingFactory.deploy(token.target);
  await vesting.waitForDeployment();
  console.log("Vesting deployed at:", vesting.target);

  // Deploy RewardEmission
  const EmissionFactory = await ethers.getContractFactory("RewardEmission");
  const rewardEmission = await EmissionFactory.deploy(
    token.target,
    totalRewardEmission,
    210,
    420
  );
  await rewardEmission.waitForDeployment();
  console.log("RewardEmission deployed at:", rewardEmission.target);

  // Deploy RewardDistribution
  const DistributorFactory = await ethers.getContractFactory("RewardDistribution");
  const rewardDistribution = await DistributorFactory.deploy(token.target);
  await rewardDistribution.waitForDeployment();
  console.log("RewardDistribution deployed at:", rewardDistribution.target);

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
  appendFileSync(envPath, envData);

  // Mint tokens to deployer
  const mintTx = await token.mint(deployer.address, totalSupply);
  await mintTx.wait();
  console.log("✅ Minted", ethers.formatUnits(totalSupply, 8), "tokens to deployer");

  // Check deployer's token balance
  const deployerTokenBalance = await token.balanceOf(deployer.address);
  console.log("Deployer's MTNSRTEST01 balance:", ethers.formatUnits(deployerTokenBalance, 8));

  // Approve and deposit tokens to Vesting
  try {
    const approveVestingTx = await token.approve(vesting.target, vestingAmount, { gasLimit: 300000 });
    await approveVestingTx.wait();
    console.log("✅ Approved", ethers.formatUnits(vestingAmount, 8), "tokens for Vesting, tx:", approveVestingTx.hash);

    const vestingAllowance = await token.allowance(deployer.address, vesting.target);
    console.log("Vesting allowance:", ethers.formatUnits(vestingAllowance, 8));
    if (vestingAllowance < vestingAmount) {
      throw new Error("❌ Not enough allowance for Vesting");
    }

    const initVestingTx = await vesting.initializeVesting(vestingAmount, { gasLimit: 300000 });
    await initVestingTx.wait();
    console.log("✅ Deposited", ethers.formatUnits(vestingAmount, 8), "tokens into Vesting, tx:", initVestingTx.hash);
  } catch (err) {
    console.error("❌ Error depositing to Vesting:", err.message);
    throw err;
  }

  // Approve and deposit tokens to Treasury
  try {
    const approveTreasuryTx = await token.approve(treasury.target, treasuryAmount, { gasLimit: 300000 });
    await approveTreasuryTx.wait();
    console.log("✅ Approved", ethers.formatUnits(treasuryAmount, 8), "tokens for Treasury, tx:", approveTreasuryTx.hash);

    const treasuryAllowance = await token.allowance(deployer.address, treasury.target);
    console.log("Treasury allowance:", ethers.formatUnits(treasuryAllowance, 8));
    if (treasuryAllowance < treasuryAmount) {
      throw new Error("❌ Not enough allowance for Treasury");
    }

    const depositTreasuryTx = await treasury.depositToTreasury(treasuryAmount, { gasLimit: 300000 });
    await depositTreasuryTx.wait();
    console.log("✅ Deposited", ethers.formatUnits(treasuryAmount, 8), "tokens into Treasury, tx:", depositTreasuryTx.hash);
  } catch (err) {
    console.error("❌ Error depositing to Treasury:", err.message);
    throw err;
  }

  // Check Vesting and Treasury balances
  const vestingBalance = await token.balanceOf(vesting.target);
  console.log("Vesting contract balance:", ethers.formatUnits(vestingBalance, 8), "MTNSRTEST01");
  const treasuryBalance = await token.balanceOf(treasury.target);
  console.log("Treasury contract balance:", ethers.formatUnits(treasuryBalance, 8), "MTNSRTEST01");

  // Setup vesting schedule
  const recipient_address1 = process.env.RECIPIENT_ADDRESS_1;
  const recipient_address2 = process.env.RECIPIENT_ADDRESS_2;

  if (!recipient_address1 || !ethers.isAddress(recipient_address1)) {
    throw new Error(`❌ Invalid or unset RECIPIENT_ADDRESS_1: ${recipient_address1}`);
  }
  if (!recipient_address2 || !ethers.isAddress(recipient_address2)) {
    throw new Error(`❌ Invalid or unset RECIPIENT_ADDRESS_2: ${recipient_address2}`);
  }

  // Setup vesting for recipient 1
  try {
    const hasVesting1 = await vesting.hasVesting(recipient_address1);
    console.log(`hasVesting[${recipient_address1}]:`, hasVesting1);
    if (hasVesting1) {
      throw new Error(`❌ Address ${recipient_address1} already has a vesting schedule`);
    }

    console.log("Setting vesting for:", recipient_address1);
    console.log("Input for setupVesting:", {
      recipient: recipient_address1,
      amount: ethers.formatUnits(totalVestingAmount, 8),
      startTime,
      duration,
      currentBlockTimestamp: currentTimestamp,
    });
    const tx1 = await vesting.setupVesting(recipient_address1, totalVestingAmount, startTime, duration, { gasLimit: 1000000 });
    await tx1.wait();
    console.log("✅ Vesting schedule set for:", recipient_address1, "Tx:", tx1.hash);
  } catch (err) {
    console.error("❌ Error setting vesting for recipient1:", err.message);
    throw err;
  }

  // Setup vesting for recipient 2
  try {
    const hasVesting2 = await vesting.hasVesting(recipient_address2);
    console.log(`hasVesting[${recipient_address2}]:`, hasVesting2);
    if (hasVesting2) {
      throw new Error(`❌ Address ${recipient_address2} already has a vesting schedule`);
    }

    console.log("Setting vesting for:", recipient_address2);
    console.log("Input for setupVesting:", {
      recipient: recipient_address2,
      amount: ethers.formatUnits(totalVestingAmount, 8),
      startTime,
      duration,
      currentBlockTimestamp: currentTimestamp,
    });
    const tx2 = await vesting.setupVesting(recipient_address2, totalVestingAmount, startTime, duration, { gasLimit: 1000000 });
    await tx2.wait();
    console.log("✅ Vesting schedule set for:", recipient_address2, "Tx:", tx2.hash);
  } catch (err) {
    console.error("❌ Error setting vesting for recipient2:", err.message);
    throw err;
  }

  // Get all recipients
  const recipients = await vesting.getAllRecipients();
  console.log("✅ List of vesting recipients:", recipients);

  // Link RewardEmission and RewardDistribution
  try {
    const setDistributorTx = await rewardEmission.setRewardDistributor(rewardDistribution.target, { gasLimit: 300000 });
    await setDistributorTx.wait();
    const setEmissionTx = await rewardDistribution.setRewardEmission(rewardEmission.target, { gasLimit: 300000 });
    await setEmissionTx.wait();
    console.log("✅ Linked RewardEmission and RewardDistribution");
  } catch (err) {
    console.error("❌ Error linking RewardEmission and RewardDistribution:", err.message);
    throw err;
  }

  // Approve and initialize vault
  try {
    const approveEmissionTx = await token.approve(rewardEmission.target, totalRewardEmission, { gasLimit: 300000 });
    await approveEmissionTx.wait();
    console.log("✅ Approved", ethers.formatUnits(totalRewardEmission, 8), "tokens for RewardEmission, tx:", approveEmissionTx.hash);

    const initVaultTx = await rewardEmission.initializeVaultAndEpoch(totalRewardEmission, { gasLimit: 300000 });
    await initVaultTx.wait();
    console.log("✅ Vault initialized with", ethers.formatUnits(totalRewardEmission, 8), "tokens, tx:", initVaultTx.hash);
  } catch (err) {
    console.error("❌ Error initializing vault:", err.message);
    throw err;
  }

  // Display final token balances
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
    console.log(`- ${name}: ${ethers.formatUnits(balance, 8)} MTNSRTEST01`);
  }
}

main().catch((error) => {
  console.error("❌ Error:", error);
  process.exitCode = 1;
});
