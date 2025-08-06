// scripts/send-tcore.js
import pkg from 'hardhat';
const { ethers } = pkg;

async function main() {
  // 👉 Thay bằng private key của ví phụ (đã xin được tCORE)
  const senderPrivateKey = process.env.PrivateKeySenCore;

  // 👉 Địa chỉ ví chính của bạn (đích đến)
  const receiverAddress = process.env.ReceiptCore;

  // Kết nối mạng testnet của Core (có thể dùng RPC public)
  const provider = new ethers.JsonRpcProvider("https://rpc.test2.btcs.network");

  // Tạo wallet từ private key
  const wallet = new ethers.Wallet(senderPrivateKey, provider);

  // Số lượng muốn chuyển: ví dụ 0.1 tCORE
  const amount = ethers.parseEther("0.95");

  const tx = await wallet.sendTransaction({
    to: receiverAddress,
    value: amount,
  });

  console.log("Đang gửi... TX hash:", tx.hash);

  const receipt = await tx.wait();
  console.log("✅ Gửi thành công:", receipt.transactionHash);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
