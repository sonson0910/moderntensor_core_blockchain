const hre = require("hardhat");
const { ethers } = hre;
require("dotenv").config();

async function setup() {
  const [owner] = await ethers.getSigners();
  console.log("👤 Using account:", owner.address);

  const token = await ethers.getContractAt("MTNSRTEST01", process.env.TOKEN_ADDRESS);
  const rewardEmission = await ethers.getContractAt("RewardEmission", process.env.REWARD_EMISSION_ADDRESS);
  const rewardDistribution = await ethers.getContractAt("RewardDistribution", process.env.REWARD_DISTRIBUTION_ADDRESS);

  const subnet1 = process.env.TEST_ADDRESS_1;
  const subnet2 = process.env.TEST_ADDRESS_2;

  const validator1 = process.env.RECIPIENT_ADDRESS_1;
  const validator2 = process.env.RECIPIENT_ADDRESS_2;
  const miner1 = process.env.RECIPIENT_ADDRESS_3;
  const miner2 = process.env.RECIPIENT_ADDRESS_4;

  const validator3 = process.env.RECIPIENT_ADDRESS_5;
  const validator4 = process.env.RECIPIENT_ADDRESS_6;
  const miner3 = process.env.RECIPIENT_ADDRESS_7;
  const miner4 = process.env.RECIPIENT_ADDRESS_8;

  await rewardDistribution.setSubnets([subnet1, subnet2], [50, 50]);
  console.log("✅ Subnets configured:", subnet1, subnet2);

  await rewardDistribution.setParticipants(
    0,
    [validator1, validator2],
    [50, 30],
    [miner1, miner2],
    [40, 20]
  );
  console.log("✅ Subnet 0 participants configured");

  await rewardDistribution.setParticipants(
    1,
    [validator3, validator4],
    [60, 40],
    [miner3, miner4],
    [70, 30]
  );
  console.log("✅ Subnet 1 participants configured");

  return {
    token,
    rewardEmission,
    rewardDistribution,
  };
}

async function loopDistribute({ token, rewardEmission, rewardDistribution }) {
  const subnets = await rewardDistribution.getSubnets();
  const numSubnets = subnets.length;

  const state = await rewardEmission.rewardState();
  const secondsPerPeriod = Number(state.secondsPerPeriod);

  while (true) {
    const loopStart = Date.now();

    try {
      await rewardEmission.emitReward();
      console.log("✅ Reward emitted");

      const emissionAmount = await rewardDistribution.getAvailableBalance();
      console.log("💰 Available balance:", ethers.formatUnits(emissionAmount, 8));

      await rewardDistribution.distributeRewards(emissionAmount);
      console.log("🚀 Rewards distributed to all subnets and participants");

      console.log("\n📦 BALANCES AFTER DISTRIBUTION:");
      for (let i = 0; i < numSubnets; i++) {
        const subnetAddr = subnets[i].subnetAddress;
        const valList = await rewardDistribution.getValidators(i);
        const minerList = await rewardDistribution.getMiners(i);

        const subnetBal = await token.balanceOf(subnetAddr);
        console.log(`📤 Subnet ${i} (${subnetAddr}): ${ethers.formatUnits(subnetBal, 8)}`);

        for (const v of valList) {
          const bal = await token.balanceOf(v.participantAddress);
          console.log(`👷 Validator (${v.participantAddress}): ${ethers.formatUnits(bal, 8)}`);
        }

        for (const m of minerList) {
          const bal = await token.balanceOf(m.participantAddress);
          console.log(`⛏️ Miner (${m.participantAddress}): ${ethers.formatUnits(bal, 8)}`);
        }

        console.log("----");
      }

    } catch (err) {
      console.error("❌ Error in loop:", err);
    }

    const loopEnd = Date.now();
    const loopDuration = (loopEnd - loopStart) / 1000;
    const waitTime = Math.max(0, secondsPerPeriod - loopDuration);

    console.log(`\n⏱️ Loop took ${loopDuration.toFixed(1)}s. Waiting ${waitTime.toFixed(1)}s before next round...\n`);

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

async function main() {
  const contracts = await setup();
  await loopDistribute(contracts);
}

main().catch((err) => {
  console.error("❌ Initialization error:", err);
  process.exitCode = 1;
});
