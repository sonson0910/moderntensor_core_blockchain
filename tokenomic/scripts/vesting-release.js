import hardhat from "hardhat";
import * as dotenv from "dotenv";
dotenv.config();
const { ethers } = hardhat;

async function main() {
  const vestingAddr = process.env.VESTING_ADDRESS;
  const tokenAddr = process.env.TOKEN_ADDRESS;

  if (!vestingAddr || !tokenAddr) {
    throw new Error("❌ VESTING_ADDRESS or TOKEN_ADDRESS not set in .env");
  }

  const [owner] = await ethers.getSigners();
  const Vesting = await ethers.getContractAt("Vesting", vestingAddr);
  const Token = await ethers.getContractAt("MTNSRTEST01", tokenAddr);

  const recipients = await Vesting.getAllRecipients();
  console.log("📦 Found recipients:", recipients.length);

  const vestingTokenBalance = await Token.balanceOf(vestingAddr);
  console.log("🏦 Vesting Contract Token Balance:", ethers.formatUnits(vestingTokenBalance, 8));

  for (const addr of recipients) {
    const schedule = await Vesting.schedules(addr);
    const now = Math.floor(Date.now() / 1000);

    const startTime = Number(schedule.startTime);
    const duration = Number(schedule.duration);
    const total = schedule.totalAmount;
    const released = schedule.releasedAmount;
    const endTime = startTime + duration;

    const elapsed = Math.max(0, now - startTime);
    const vested = (elapsed >= duration)
      ? total
      : total * BigInt(elapsed) / BigInt(duration);

    const toRelease = vested - released;
    const remaining = total - released;

    console.log(`\n👤 Address: ${addr}`);
    console.log(`   ⏰ Start: ${new Date(startTime * 1000).toISOString()}`);
    console.log(`   🛑 End:   ${new Date(endTime * 1000).toISOString()}`);
    console.log(`   ⌛ Elapsed: ${elapsed}s`);
    console.log(`   📊 Total:      ${ethers.formatUnits(total, 8)}`);
    console.log(`   ✅ Released:   ${ethers.formatUnits(released, 8)}`);
    console.log(`   🟢 Can Release:${ethers.formatUnits(toRelease, 8)}`);
    console.log(`   🔴 Remaining:  ${ethers.formatUnits(remaining, 8)}`);

    if (now < startTime) {
      const wait = startTime - now;
      console.log(`   ⏳ Vesting not started. Wait ${wait}s`);
      continue;
    }

    if (toRelease > 0n) {
      try {
        const tx = await Vesting.releaseVesting(addr);
        await tx.wait();

        const newBalance = await Token.balanceOf(addr);
        console.log(`   ✅ Tokens released. New balance: ${ethers.formatUnits(newBalance, 8)}`);
      } catch (err) {
        console.log(`   ❌ Release failed: ${err.message}`);
      }
    } else {
      console.log("   ⚠️ Nothing to release now.");
    }
  }
}

main().catch((err) => {
  console.error("❌ Error:", err);
  process.exit(1);
});
