import hardhat from "hardhat";
import * as dotenv from "dotenv";
dotenv.config();
const { ethers } = hardhat;
// trong tương lai cũng cần mở rộng ra
async function main() {
  const treasuryAddr = process.env.TREASURY_ADDRESS;
  const tokenAddr = process.env.TOKEN_ADDRESS;
  const [owner, recipient] = await ethers.getSigners();
  // sau này thay recipient bằng address của người nhận
  const Treasury = await ethers.getContractAt("Treasury", treasuryAddr);
  const Token = await ethers.getContractAt("MTNSRTEST01", tokenAddr);

  const depositAmount = ethers.parseUnits("5000", 8);
  await Token.mint(owner.address, depositAmount);
  await Token.approve(treasuryAddr, depositAmount);
  await Treasury.depositToTreasury(depositAmount);
  console.log("✅ Deposited", ethers.formatUnits(depositAmount, 8), "to Treasury");

  const treasuryBalance = await Treasury.balance();
  console.log("📦 Treasury contract balance:", ethers.formatUnits(treasuryBalance, 8));

  const withdrawAmount = ethers.parseUnits("1000", 8);
  await Treasury.withdrawFromTreasury(recipient.address, withdrawAmount);
  const updatedBalance = await Treasury.balance();
  console.log("✅ Withdrawn", ethers.formatUnits(withdrawAmount, 8), "to", recipient.address);
  console.log("📦 Updated Treasury balance:", ethers.formatUnits(updatedBalance, 8));

  const recipientBalance = await Token.balanceOf(recipient.address);
  console.log("👤 Recipient token balance:", ethers.formatUnits(recipientBalance, 8));
}

main().catch(console.error);
