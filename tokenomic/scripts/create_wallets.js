import { ethers } from "ethers";
import { writeFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

async function createWallets() {
  console.log("Creating wallets, each with a unique mnemonic...");

  // Tạo 5 ví, mỗi ví từ một mnemonic riêng
  const walletCount = 5;
  const wallets = Array.from({ length: walletCount }, () => ethers.Wallet.createRandom());

  // Chuẩn bị nội dung cho file .env
  const envContent = [
    `# Owner wallet (for deployment and governance)`,
    `PRIVATE_KEY=${wallets[0].privateKey}`,
    `OWNER_ADDRESS=${wallets[0].address}`,
    `RPC_URL=https://rpc.test2.btcs.network`,
    `TOKEN_ADDRESS=to_be_updated`,
    `VESTING_ADDRESS=to_be_updated`,
    `REWARD_EMISSION_ADDRESS=to_be_updated`,
    `GOVERNANCE_ADDRESS=to_be_updated`,
    `TREASURY_ADDRESS=to_be_updated`,
    `TELEGRAM_BOT_TOKEN=your_telegram_bot_token`,
    `TELEGRAM_CHAT_ID=your_telegram_chat_id`,
    `RECIPIENT_ADDRESS_1=${wallets[1].address}`,
    `RECIPIENT_ADDRESS_2=${wallets[2].address}`,
    `TEST_ADDRESS_1=${wallets[3].address}`,
    `TEST_ADDRESS_2=${wallets[4].address}`,
  ].join("\n");

  // Ghi vào file .env
  const envPath = join(__dirname, "../.env");
  writeFileSync(envPath, envContent);
  console.log("Updated .env file with new wallet addresses and private key.");

  // Chuẩn bị nội dung cho file wallets.txt
  const walletsContent = wallets
    .map((wallet, index) => {
      const role = [
        "Owner (deployer and governance)",
        "Recipient 1 (vesting)",
        "Recipient 2 (vesting)",
        "Test Address 1 (governance/treasury)",
        "Test Address 2 (governance/treasury)",
      ][index];
      return [
        `Wallet ${index + 1} (${role}):`,
        `  Address: ${wallet.address}`,
        `  Private Key: ${wallet.privateKey}`,
        `  Mnemonic: ${wallet.mnemonic.phrase}`,
        `  -----------------------------------`,
      ].join("\n");
    })
    .join("\n");

  // Ghi vào file wallets.txt
  const walletsPath = join(__dirname, "../wallets.txt");
  writeFileSync(walletsPath, `WARNING: Keep this file secure and do not share it!\n\n${walletsContent}`);
  console.log("Saved wallet details to wallets.txt for importing into MetaMask.");

  // In ra thông tin ví
  console.log("\nGenerated Wallets:");
  wallets.forEach((wallet, index) => {
    const role = [
      "Owner (deployer and governance)",
      "Recipient 1 (vesting)",
      "Recipient 2 (vesting)",
      "Test Address 1 (governance/treasury)",
      "Test Address 2 (governance/treasury)",
    ][index];
    console.log(`Wallet ${index + 1} (${role}):`);
    console.log(`  Address: ${wallet.address}`);
    console.log(`  Private Key: ${wallet.privateKey}`);
    console.log(`  Mnemonic: ${wallet.mnemonic.phrase}`);
  });

  console.log("\nInstructions for MetaMask:");
  console.log("1. Open MetaMask, click 'Import Wallet' for each wallet.");
  console.log("2. Enter the mnemonic from wallets.txt for the desired wallet.");
  console.log("3. Add Core DAO Testnet (RPC: https://rpc.test2.btcs.network, Chain ID: 1114).");
  console.log("4. Fund addresses with CORE testnet tokens at 	https://scan.test2.btcs.network/faucet");
  console.log("4. Explore at 	https://scan.test2.btcs.network");
}

createWallets().catch((error) => {
  console.error("Error creating wallets:", error);
  process.exitCode = 1;
});
