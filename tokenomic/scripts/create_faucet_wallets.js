import { ethers } from "ethers";
import { appendFileSync, writeFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

async function createFaucetWallets() {
  console.log("Creating 10 faucet wallets...");

  const faucetWallets = Array.from({ length: 20 }, () => ethers.Wallet.createRandom());

  // Ghi thêm vào .env
  const envPath = join(__dirname, "../.env");
  const faucetEnvLines = faucetWallets
    .map((wallet, i) => `FAUCET_WALLET_${i + 1}=${wallet.privateKey}`)
    .join("\n");
  appendFileSync(envPath, `\n# Faucet wallets\n${faucetEnvLines}\n`);
  console.log("✅ Appended faucet wallet private keys to .env");

  // Ghi thêm vào wallets.txt
  const walletsPath = join(__dirname, "../wallets.txt");
  const faucetContent = faucetWallets
    .map((wallet, i) => {
      return [
        `Faucet Wallet ${i + 1}:`,
        `  Address: ${wallet.address}`,
        `  Private Key: ${wallet.privateKey}`,
        `  Mnemonic: ${wallet.mnemonic.phrase}`,
        `  -----------------------------------`,
      ].join("\n");
    })
    .join("\n");
  appendFileSync(walletsPath, `\nFaucet Wallets (for testnet CORE):\n\n${faucetContent}\n`);
  console.log("✅ Appended faucet wallet details to wallets.txt");

  console.log("\nInstructions:");
  console.log("1. Import these wallets into MetaMask using mnemonic or private key.");
  console.log("2. Visit https://scan.test2.btcs.network/faucet to claim 1 CORE2 per 24h.");
  console.log("3. Use `FAUCET_WALLET_X` private keys from .env for scripting transfers if needed.");
}

createFaucetWallets().catch((err) => {
  console.error("Error creating faucet wallets:", err);
  process.exitCode = 1;
});
