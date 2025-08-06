const { ethers } = require("hardhat");
require("dotenv").config();

async function setup() {
  const [owner] = await ethers.getSigners();

  // Check environment variables
  const CONTRACT_ADDRESS = process.env.SOL_ADDRESS;
  const RPC_URL = process.env.RPC_URL;
  const TOKEN_ADDRESS = process.env.TOKEN_ADDRESS;
  const REWARD_EMISSION_ADDRESS = process.env.REWARD_EMISSION_ADDRESS;
  const REWARD_DISTRIBUTION_ADDRESS = process.env.REWARD_DISTRIBUTION_ADDRESS;

  if (!CONTRACT_ADDRESS || !ethers.isAddress(CONTRACT_ADDRESS)) {
    throw new Error(`❌ Invalid SOL_ADDRESS: ${CONTRACT_ADDRESS}`);
  }
  if (!RPC_URL) {
    throw new Error("❌ RPC_URL is not set in .env");
  }
  if (!TOKEN_ADDRESS || !ethers.isAddress(TOKEN_ADDRESS)) {
    throw new Error(`❌ Invalid TOKEN_ADDRESS: ${TOKEN_ADDRESS}`);
  }
  if (!REWARD_EMISSION_ADDRESS || !ethers.isAddress(REWARD_EMISSION_ADDRESS)) {
    throw new Error(`❌ Invalid REWARD_EMISSION_ADDRESS: ${REWARD_EMISSION_ADDRESS}`);
  }
  if (!REWARD_DISTRIBUTION_ADDRESS || !ethers.isAddress(REWARD_DISTRIBUTION_ADDRESS)) {
    throw new Error(`❌ Invalid REWARD_DISTRIBUTION_ADDRESS: ${REWARD_DISTRIBUTION_ADDRESS}`);
  }

  // Load contracts
  const token = await ethers.getContractAt("MTNSRTEST01", TOKEN_ADDRESS, owner);
  const rewardEmission = await ethers.getContractAt("RewardEmission", REWARD_EMISSION_ADDRESS, owner);
  const rewardDistribution = await ethers.getContractAt("RewardDistribution", REWARD_DISTRIBUTION_ADDRESS, owner);
  const ModernTensorABI = JSON.parse(require("fs").readFileSync("./abis/ModernTensor.json", "utf8")).abi;
  const modernTensor = new ethers.Contract(CONTRACT_ADDRESS, ModernTensorABI, owner);

 
  const code = await ethers.provider.getCode(CONTRACT_ADDRESS);
  if (code === "0x") {
    throw new Error("❌ Contract not found at SOL_ADDRESS");
  }

  // Check RewardEmission contract
  const rewardEmissionCode = await ethers.provider.getCode(REWARD_EMISSION_ADDRESS);
  if (rewardEmissionCode === "0x") {
    throw new Error(`❌ No contract found at REWARD_EMISSION_ADDRESS: ${REWARD_EMISSION_ADDRESS}`);
  }

  const rewardDistributionOwner = await rewardDistribution.owner();
  if (rewardDistributionOwner.toLowerCase() !== owner.address.toLowerCase()) {
    throw new Error(`❌ Account ${owner.address} is not the owner of RewardDistribution`);
  }

  // Check RewardEmission owner
  const rewardEmissionOwner = await rewardEmission.owner();
  if (rewardEmissionOwner.toLowerCase() !== owner.address.toLowerCase()) {
    throw new Error(`❌ Account ${owner.address} is not the owner of RewardEmission`);
  }



  // Check rewardDistributor
  const rewardDistributor = await rewardEmission.rewardDistributor();
  if (rewardDistributor === ethers.ZeroAddress) {
    console.log("⚠️ RewardDistributor not set, setting to REWARD_DISTRIBUTION_ADDRESS...");
    const tx = await rewardEmission.setRewardDistributor(REWARD_DISTRIBUTION_ADDRESS, { gasLimit: 100000 });
    await tx.wait();
  } else if (rewardDistributor.toLowerCase() !== REWARD_DISTRIBUTION_ADDRESS.toLowerCase()) {
    console.log("⚠️ RewardDistributor mismatch, updating to REWARD_DISTRIBUTION_ADDRESS...");
    const tx = await rewardEmission.setRewardDistributor(REWARD_DISTRIBUTION_ADDRESS, { gasLimit: 100000 });
    await tx.wait();
  }

  // Check RewardEmission address in RewardDistribution
  const rewardEmissionAddress = await rewardDistribution.rewardEmission();
  if (rewardEmissionAddress.toLowerCase() !== REWARD_EMISSION_ADDRESS.toLowerCase()) {
    const tx = await rewardDistribution.setRewardEmission(REWARD_EMISSION_ADDRESS, { gasLimit: 100000 });
    await tx.wait();
  }

  // Fetch subnet list
  let subnetIds = [];
  try {
    const rawSubnetIds = await modernTensor.getAllSubnetIds();
    subnetIds = rawSubnetIds.map(id => Number(id));
  } catch (error) {
    console.error("❌ Failed to fetch subnet list:", error.message);
    process.exit(1);
  }

  // Fetch and prepare subnet data
  const subnetData = [];
  const subnetAddresses = [];
  const weights = [];

  for (const id of subnetIds) {
    try {
      const [staticData, dynamicData, minerAddresses, validatorAddresses] = await modernTensor.getSubnet(id);
      if (!staticData || !dynamicData || !Array.isArray(minerAddresses) || !Array.isArray(validatorAddresses)) {
        throw new Error(`Invalid data structure for subnet ${id}`);
      }

      const incentiveRatio = dynamicData.scaled_incentive_ratio;
      subnetData.push({
        id: Number(id),
        address: staticData.owner_addr,
        name: staticData.name || "Unknown",
        minerAddresses: Array.from(minerAddresses),
        validatorAddresses: Array.from(validatorAddresses),
        scaledIncentiveRatio: ethers.formatUnits(incentiveRatio, 6),
      });
      subnetAddresses.push(staticData.owner_addr);
      weights.push(incentiveRatio);
    } catch (error) {
      console.error(`❌ Failed to fetch subnet info ${id}:`, error.message);
      continue;
    }
  }

  if (subnetAddresses.length === 0 || weights.length === 0 || subnetIds.length === 0) {
    throw new Error("❌ No valid subnets, weights, or subnet IDs available for configuration");
  }

  try {
    const tx = await rewardDistribution.setSubnets(subnetIds, subnetAddresses, weights, { gasLimit: 500000 });
    await tx.wait();
  } catch (error) {
    console.error("❌ Failed to configure subnets:", error.message);
    process.exit(1);
  }

  // Check subnets in contract
  const subnets = await rewardDistribution.getSubnets();

  // Validate subnet IDs
  subnetData.forEach(subnet => {
    const exists = subnets.some(s => s.subnetId.toString() === subnet.id.toString());
    if (!exists) {
      console.error(`❌ Subnet ID ${subnet.id} not found in contract subnets`);
    }
  });

  // Set participants for each subnet
  for (const subnet of subnetData) {
    const minerScores = await Promise.all(subnet.minerAddresses.map(async (addr) => {
      try {
        const miner = await modernTensor.getMinerInfo(addr);
        const score = Number(miner.scaled_last_performance) / 1_000_000;
        return Math.floor(score * 100) || Math.floor(Math.random() * 21) + 70;
      } catch (error) {
        console.error(`❌ Failed to fetch miner info ${addr}:`, error.message);
        return 50;
      }
    }));

    const validatorScores = await Promise.all(subnet.validatorAddresses.map(async (addr) => {
      try {
        const validator = await modernTensor.getValidatorInfo(addr);
        const score = Number(validator.scaled_last_performance) / 1_000_000;
        return Math.floor(score * 100) || Math.floor(Math.random() * 21) + 70;
      } catch (error) {
        console.error(`❌ Failed to fetch validator info ${addr}:`, error.message);
        return 50;
      }
    }));

    const validatorScoresBig = validatorScores.map(score => BigInt(score));
    const minerScoresBig = minerScores.map(score => BigInt(score));

    // Validate addresses and scores
    subnet.validatorAddresses.forEach(addr => {
      if (!ethers.isAddress(addr)) {
        console.error(`❌ Invalid validator address: ${addr}`);
      }
    });
    subnet.minerAddresses.forEach(addr => {
      if (!ethers.isAddress(addr)) {
        console.error(`❌ Invalid miner address: ${addr}`);
      }
    });
    validatorScoresBig.forEach((score, i) => {
      if (score <= 0) {
        console.warn(`⚠️ Validator ${subnet.validatorAddresses[i]} has score ${score}, defaulting to 50`);
        validatorScoresBig[i] = BigInt(50);
      }
    });
    minerScoresBig.forEach((score, i) => {
      if (score <= 0) {
        console.warn(`⚠️ Miner ${subnet.minerAddresses[i]} has score ${score}, defaulting to 50`);
        minerScoresBig[i] = BigInt(50);
      }
    });

    // Validate array lengths
    if (subnet.validatorAddresses.length !== validatorScoresBig.length) {
      console.error(`❌ Mismatch: validatorAddresses (${subnet.validatorAddresses.length}) and validatorScores (${validatorScoresBig.length}) for subnet ${subnet.id}`);
      continue;
    }
    if (subnet.minerAddresses.length !== minerScoresBig.length) {
      console.error(`❌ Mismatch: minerAddresses (${subnet.minerAddresses.length}) and minerScores (${minerScoresBig.length}) for subnet ${subnet.id}`);
      continue;
    }

    try {
      const subnets = await rewardDistribution.getSubnets();
      if (!subnets.some(s => s.subnetId.toString() === subnet.id.toString())) {
        throw new Error(`❌ Subnet ID ${subnet.id} not found in contract subnets`);
      }
      const tx = await rewardDistribution.setParticipants(
        subnet.id,
        subnet.validatorAddresses,
        validatorScoresBig,
        subnet.minerAddresses,
        minerScoresBig,
        { gasLimit: 500000 }
      );
      await tx.wait();
    } catch (error) {
      console.error(`❌ Failed to set participants for subnet ${subnet.id}:`, error.message);
      if (error.reason) console.error("Revert reason:", error.reason);
      continue;
    }
  }

  // Display subnet information before starting distribution loop
  console.log("\n📋 SUBNETS INFORMATION BEFORE DISTRIBUTION:");
  for (const subnet of subnets) {
    const subnetAddr = subnet.subnetAddress;
    const subnetId = subnet.subnetId;
    const weight = subnet.weight;
    const valList = await rewardDistribution.getValidators(subnetId);
    const minerList = await rewardDistribution.getMiners(subnetId);

    console.log(`📍 Subnet ${subnetId}`);
    console.log(`  Address: ${subnetAddr}`);
    console.log(`  Allocation Ratio: ${ethers.formatUnits(weight, 6)}`);

    console.log(`  Validators:`);
    for (const v of valList) {
      console.log(`    - Address: ${v.participantAddress}, performance: ${(Number(v.performanceScore)/100).toFixed(6)}`);
    }

    console.log(`  Miners:`);
    for (const m of minerList) {
      console.log(`    - Address: ${m.participantAddress}, performance: ${(Number(m.performanceScore)/100).toFixed(6)}`);
    }
    console.log("----");
  }

  return { token, rewardEmission, rewardDistribution, modernTensor };
}

async function loopDistribute({ token, rewardEmission, rewardDistribution }) {
  const subnets = await rewardDistribution.getSubnets();
  const numSubnets = subnets.length;
  const state = await rewardEmission.rewardState();
  const secondsPerPeriod = Number(state.secondsPerPeriod);

  while (true) {
    const loopStart = Date.now();
    let waitTime = secondsPerPeriod; // Khởi tạo waitTime mặc định

    try {
      // Check epoch timing
      const rewardState = await rewardEmission.rewardState();
      const lastEmissionTime = Number(rewardState.lastEmissionTime);
      const secondsPerPeriod = Number(rewardState.secondsPerPeriod);
      const currentBlock = await ethers.provider.getBlock("latest");
      const nextEmissionTime = lastEmissionTime + secondsPerPeriod;
      
      // Tính waitTime dựa trên thời gian còn lại của epoch
      waitTime = currentBlock.timestamp < nextEmissionTime 
        ? nextEmissionTime - currentBlock.timestamp 
        : 0;

      if (waitTime > 0) {
        
      } else {
        // Check community vault balance
        const emitTx = await rewardEmission.emitReward({ gasLimit: 500000 });
        await emitTx.wait();

        const emissionAmount = await rewardDistribution.getAvailableBalance();
        console.log("💰 Available balance:", ethers.formatUnits(emissionAmount, 8));

        const distributeTx = await rewardDistribution.distributeRewards(emissionAmount, { gasLimit: 500000 });
        await distributeTx.wait();
        console.log("🚀 Rewards distributed to all subnets and participants");

        console.log("\n📦 BALANCES AFTER DISTRIBUTION:");
        for (let i = 0; i < numSubnets; i++) {
          const subnetAddr = subnets[i].subnetAddress;
          const subnetId = subnets[i].subnetId;
          const weight = subnets[i].weight;
          const valList = await rewardDistribution.getValidators(subnetId);
          const minerList = await rewardDistribution.getMiners(subnetId);

          const subnetBal = await token.balanceOf(subnetAddr);
          console.log(`📤 Subnet ${subnetId} (${subnetAddr}): ${ethers.formatUnits(subnetBal, 8)} (allocation ratio: ${ethers.formatUnits(weight, 6)})`);

          for (const v of valList) {
            const bal = await token.balanceOf(v.participantAddress);
            console.log(`👷 Validator (${v.participantAddress}): ${ethers.formatUnits(bal, 8)} (performance: ${(Number(v.performanceScore) / 100).toFixed(6)})`);
          }

          for (const m of minerList) {
            const bal = await token.balanceOf(m.participantAddress);
            console.log(`⛏️ Miner (${m.participantAddress}): ${ethers.formatUnits(bal, 8)} (performance: ${(Number(m.performanceScore) / 100).toFixed(6)})`);
          }
          console.log("----");
        }
      }
    } catch (err) {
      // Handle specific errors
      if (err.message.includes("Not time for emission")) {
        try {
          const rewardState = await rewardEmission.rewardState();
          const currentBlock = await ethers.provider.getBlock("latest");
          waitTime = Number(rewardState.lastEmissionTime) + Number(rewardState.secondsPerPeriod) - currentBlock.timestamp;
        } catch (innerErr) {
          console.error("❌ Error while calculating wait time:", innerErr.message);
          waitTime = secondsPerPeriod; // Fallback to default wait time
        }
      } else {
        console.error("❌ Error in loop:", err.message);
        if (err.reason) console.error("Revert reason:", err.reason);
        waitTime = secondsPerPeriod; // Fallback to default wait time for other errors
      }
    }

    const loopDuration = (Date.now() - loopStart) / 1000;
    const minutes_show = Math.floor(secondsPerPeriod / 60);
    const seconds_show = secondsPerPeriod % 60;
    console.log(`⏱ Epoch duration: ${minutes_show} minute ${seconds_show} second`);
    console.log(`\n⏱️ Loop took ${loopDuration.toFixed(1)}s. Waiting ${waitTime.toFixed(1)}s before next round...\n`);

    if (waitTime > 0) {
      await new Promise((res) => {
        let secondsLeft = Math.floor(waitTime);
        const interval = setInterval(() => {
          process.stdout.write(`\r⏳ Countdown: ${secondsLeft}s remaining... `);
          secondsLeft--;
          if (secondsLeft < 0) {
            clearInterval(interval);
            process.stdout.write("\n");
            res();
          }
        }, 1000);
      });
    }
  }
}

async function main() {
  try {
    const contracts = await setup();
    await loopDistribute(contracts);
  } catch (err) {
    console.error("❌ Initialization error:", err.message);
    process.exitCode = 1;
  }
}

main();