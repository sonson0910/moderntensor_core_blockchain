const hre = require("hardhat");
require("dotenv").config();

// Script off-chain để gọi emitReward và distributeRewards
async function main() {
  const [owner] = await hre.ethers.getSigners();
  console.log("👤 Running with account:", owner.address);

  // Lấy hợp đồng
  const token = await hre.ethers.getContractAt("MTNSRTEST01", process.env.TOKEN_ADDRESS);
  const rewardEmission = await hre.ethers.getContractAt("RewardEmission", process.env.REWARD_EMISSION_ADDRESS);
  const rewardDistribution = await hre.ethers.getContractAt("RewardDistribution", process.env.REWARD_DISTRIBUTION_ADDRESS);

  // Thiết lập subnet và participants
  const subnet1 = process.env.TEST_ADDRESS_1;
  const subnet2 = process.env.TEST_ADDRESS_2;
  const validator1 = process.env.RECIPIENT_ADDRESS_1;
  const validator2 = process.env.RECIPIENT_ADDRESS_2;
  const miner1 = process.env.RECIPIENT_ADDRESS_1;
  const miner2 = process.env.RECIPIENT_ADDRESS_2;

  await rewardDistribution.setSubnets([subnet1, subnet2], [50, 50]);
  console.log("✅ Set subnets:", subnet1, subnet2);

  await rewardDistribution.setParticipants(
    0,
    [validator1, validator2],
    [50, 30],
    [miner1, miner2],
    [40, 20]
  );
  console.log("✅ Set participants for subnet 0");

  // Lấy trạng thái hiện tại
  const state = await rewardEmission.rewardState();
  const lastEmissionTime = Number(state.lastEmissionTime);
  const secondsPerPeriod = Number(state.secondsPerPeriod);
  const totalEmitted = Number(state.totalDistributed);

  const now = Math.floor(Date.now() / 1000);
  const nextEmissionTime = lastEmissionTime + secondsPerPeriod;
  const timeLeft = nextEmissionTime - now;

  console.log("\n📊 THÔNG TIN TRẠNG THÁI:");
  console.log("⏱ Last Emission Time      :", lastEmissionTime, new Date(lastEmissionTime * 1000).toLocaleString());
  console.log("⏳ Seconds Per Period      :", secondsPerPeriod);
  console.log("🕐 Current Time (now)      :", now, new Date(now * 1000).toLocaleString());
  console.log("⏭ Next Emission Time      :", nextEmissionTime, new Date(nextEmissionTime * 1000).toLocaleString());
  console.log("⏳ Time Left Until Emit    :", timeLeft > 0 ? `${timeLeft}s (~${(timeLeft / 60).toFixed(1)} phút)` : "Đã đến thời điểm");
  console.log("💰 Total Emitted           :", totalEmitted);

  // Nếu chưa đến thời điểm emit
  if (now < nextEmissionTime) {
    console.log("\n❌ Chưa đến thời điểm emit reward. Hãy thử lại sau.");
    return;
  }

  // Gọi emitReward
  await rewardEmission.emitReward();
  console.log("\n✅ Emitted reward");

  // Lấy availableBalance và phân phối
  const emissionAmount = await rewardDistribution.getAvailableBalance();
  console.log("💸 Available Balance to distribute:", emissionAmount.toString());

  await rewardDistribution.distributeRewards(0, emissionAmount);
  console.log("✅ Distributed rewards:", emissionAmount.toString());

  // Kiểm tra số dư
  const subnetBal = await token.balanceOf(subnet1);
  const val1Bal = await token.balanceOf(validator1);
  const val2Bal = await token.balanceOf(validator2);
  const miner1Bal = await token.balanceOf(miner1);
  const miner2Bal = await token.balanceOf(miner2);

  console.log("\n📦 SỐ DƯ SAU PHÂN PHỐI:");
  console.log("📤 Subnet 1 balance        :", subnetBal.toString());
  console.log("👷 Validator 1 balance     :", val1Bal.toString());
  console.log("👷 Validator 2 balance     :", val2Bal.toString());
  console.log("⛏️ Miner 1 balance         :", miner1Bal.toString());
  console.log("⛏️ Miner 2 balance         :", miner2Bal.toString());
}

main().catch((error) => {
  console.error("❌ Lỗi:", error);
  process.exitCode = 1;
});
