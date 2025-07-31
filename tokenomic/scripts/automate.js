require("dotenv").config();
const { ethers } = require("ethers");
const cron = require("node-cron");
const { Telegraf } = require("telegraf");

// ABI của các hợp đồng
const MTNSRTEST01_ABI = require("../artifacts/contracts/MTNSRTEST01.sol/MTNSRTEST01.json").abi;
const VESTING_ABI = require("../artifacts/contracts/Vesting.sol/Vesting.json").abi;
const REWARD_EMISSION_ABI = require("../artifacts/contracts/RewardEmission.sol/RewardEmission.json").abi;
const GOVERNANCE_ABI = require("../artifacts/contracts/Governance.sol/Governance.json").abi;
const TREASURY_ABI = require("../artifacts/contracts/Treasury.sol/Treasury.json").abi;

// Cấu hình từ .env
const provider = new ethers.providers.JsonRpcProvider(process.env.RPC_URL);
const wallet = new ethers.Wallet(process.env.PRIVATE_KEY, provider);
const tokenContract = new ethers.Contract(process.env.TOKEN_ADDRESS, MTNSRTEST01_ABI, wallet);
const vestingContract = new ethers.Contract(process.env.VESTING_ADDRESS, VESTING_ABI, wallet);
const rewardEmissionContract = new ethers.Contract(process.env.REWARD_EMISSION_ADDRESS, REWARD_EMISSION_ABI, wallet);
const governanceContract = new ethers.Contract(process.env.GOVERNANCE_ADDRESS, GOVERNANCE_ABI, wallet);
const treasuryContract = new ethers.Contract(process.env.TREASURY_ADDRESS, TREASURY_ABI, wallet);
const bot = new Telegraf(process.env.TELEGRAM_BOT_TOKEN);

// Danh sách người nhận vesting (hardcode hoặc lấy từ nguồn khác)
const VESTING_RECIPIENTS = [process.env.RECIPIENT_ADDRESS_1, process.env.RECIPIENT_ADDRESS_2]; // Thêm vào .env

// Tự động phát hành phần thưởng (mỗi 5 ngày)
async function emitReward() {
  try {
    console.log("Đang kiểm tra phát hành phần thưởng...");
    const vaultBalance = await rewardEmissionContract.communityVaultBalance();
    if (vaultBalance.lt(ethers.utils.parseUnits("850340", 8))) {
      await bot.telegram.sendMessage(process.env.TELEGRAM_CHAT_ID, "Lỗi: Số dư vault không đủ để phát hành!");
      return;
    }

    const lastEmissionTime = await rewardEmissionContract.rewardState().lastEmissionTime;
    const secondsPerPeriod = await rewardEmissionContract.rewardState().secondsPerPeriod;
    const currentTime = Math.floor(Date.now() / 1000);
    if (currentTime < lastEmissionTime.add(secondsPerPeriod).toNumber()) {
      await bot.telegram.sendMessage(process.env.TELEGRAM_CHAT_ID, "Chưa đến thời gian phát hành!");
      return;
    }

    const tx = await rewardEmissionContract.emitReward();
    await tx.wait();
    const emissionCount = await rewardEmissionContract.getEmissionCount();
    await bot.telegram.sendMessage(
      process.env.TELEGRAM_CHAT_ID,
      `Phát hành phần thưởng thành công! Số lần: ${emissionCount}`
    );
  } catch (error) {
    await bot.telegram.sendMessage(process.env.TELEGRAM_CHAT_ID, `Lỗi phát hành phần thưởng: ${error.message}`);
  }
}

// Tự động kiểm tra và giải phóng vesting
async function releaseVesting() {
  try {
    console.log("Đang kiểm tra vesting...");
    for (const recipient of VESTING_RECIPIENTS) {
      const schedule = await vestingContract.schedules(recipient);
      const { amount, released, startTime, duration } = schedule;

      // Kiểm tra xem có token nào để giải phóng không
      if (amount.eq(0) || released.gte(amount)) {
        console.log(`Không có token để giải phóng cho ${recipient}`);
        continue;
      }

      // Kiểm tra thời gian giải phóng
      const currentTime = Math.floor(Date.now() / 1000);
      const vestedAmount = amount
        .mul(Math.min(currentTime - startTime.toNumber(), duration.toNumber()))
        .div(duration);
      if (vestedAmount.lte(released)) {
        console.log(`Chưa đến thời gian giải phóng cho ${recipient}`);
        continue;
      }

      const tx = await vestingContract.releaseVesting(recipient);
      await tx.wait();
      const newReleased = await vestingContract.schedules(recipient).released;
      await bot.telegram.sendMessage(
        process.env.TELEGRAM_CHAT_ID,
        `Đã giải phóng token vesting cho ${recipient}. Số lượng giải phóng: ${ethers.utils.formatUnits(
          newReleased.sub(released),
          8
        )} MTNSRTEST01`
      );
    }
  } catch (error) {
    await bot.telegram.sendMessage(process.env.TELEGRAM_CHAT_ID, `Lỗi giải phóng vesting: ${error.message}`);
  }
}

// Tùy chọn: Tự động tạo đề xuất (nếu cần)
async function createProposal() {
  try {
    console.log("Đang kiểm tra tạo đề xuất...");
    const balance = await tokenContract.balanceOf(wallet.address);
    if (balance.lt(ethers.utils.parseUnits("1000", 8))) {
      await bot.telegram.sendMessage(process.env.TELEGRAM_CHAT_ID, "Lỗi: Số dư token không đủ để tạo đề xuất!");
      return;
    }

    const tx = await governanceContract.propose();
    await tx.wait();
    const nextProposalId = await governanceContract.nextProposalId();
    await bot.telegram.sendMessage(
      process.env.TELEGRAM_CHAT_ID,
      `Đã tạo đề xuất mới. ID: ${nextProposalId.sub(1)}`
    );
  } catch (error) {
    await bot.telegram.sendMessage(process.env.TELEGRAM_CHAT_ID, `Lỗi tạo đề xuất: ${error.message}`);
  }
}

// Tùy chọn: Tự động rút token từ kho bạc (nếu cần)
async function withdrawFromTreasury(recipient, amount) {
  try {
    console.log("Đang kiểm tra rút token từ kho bạc...");
    const treasuryBalance = await treasuryContract.balance();
    if (treasuryBalance.lt(ethers.utils.parseUnits(amount, 8))) {
      await bot.telegram.sendMessage(process.env.TELEGRAM_CHAT_ID, "Lỗi: Số dư kho bạc không đủ!");
      return;
    }

    const tx = await treasuryContract.withdrawFromTreasury(recipient, ethers.utils.parseUnits(amount, 8));
    await tx.wait();
    await bot.telegram.sendMessage(
      process.env.TELEGRAM_CHAT_ID,
      `Đã rút ${amount} MTNSRTEST01 từ kho bạc cho ${recipient}`
    );
  } catch (error) {
    await bot.telegram.sendMessage(process.env.TELEGRAM_CHAT_ID, `Lỗi rút token từ kho bạc: ${error.message}`);
  }
}

// Kiểm tra trạng thái ban đầu
async function checkInitialStatus() {
  console.log("=== Trạng thái ban đầu ===");
  const tokenBalance = await tokenContract.balanceOf(wallet.address);
  console.log("Số dư ví:", ethers.utils.formatUnits(tokenBalance, 8), "MTNSRTEST01");

  const treasuryBalance = await treasuryContract.balance();
  console.log("Số dư kho bạc:", ethers.utils.formatUnits(treasuryBalance, 8), "MTNSRTEST01");

  const epochBalance = await rewardEmissionContract.getEpochPoolBalance();
  console.log("Số dư epoch pool:", ethers.utils.formatUnits(epochBalance, 8), "MTNSRTEST01");

  const emissionCount = await rewardEmissionContract.getEmissionCount();
  console.log("Số lần phát hành:", emissionCount.toString());

  const nextProposalId = await governanceContract.nextProposalId();
  console.log("ID đề xuất tiếp theo:", nextProposalId.toString());

  await bot.telegram.sendMessage(
    process.env.TELEGRAM_CHAT_ID,
    `Script khởi động. Số dư ví: ${ethers.utils.formatUnits(tokenBalance, 8)} MTNSRTEST01, Số dư kho bạc: ${ethers.utils.formatUnits(
      treasuryBalance,
      8
    )} MTNSRTEST01, Số dư epoch pool: ${ethers.utils.formatUnits(epochBalance, 8)} MTNSRTEST01`
  );
}

// Lên lịch chạy hàng ngày (kiểm tra vesting và emitReward)
cron.schedule("0 0 * * *", async () => {
  console.log("Chạy tự động hóa hàng ngày...");
  await emitReward();
  await releaseVesting();
  // Tùy chọn: Bật các hàm khác nếu cần
  // await createProposal();
  // await withdrawFromTreasury("0xRECIPIENT_ADDRESS", "1000");
});

// Chạy kiểm tra trạng thái ban đầu
checkInitialStatus().catch((error) => {
  console.error("Lỗi khởi tạo:", error);
});

// Giữ tiến trình chạy
console.log("Script tự động hóa đang chạy...");