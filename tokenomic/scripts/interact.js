const { ethers } = require("ethers");

// Cấu hình mạng Core DAO
const RPC_URL = "https://rpc.coredao.org"; // Kiểm tra tại coredao.org
const provider = new ethers.providers.JsonRpcProvider(RPC_URL);

// Địa chỉ hợp đồng (thay bằng địa chỉ thực sau khi triển khai)
const TOKEN_ADDRESS = "YOUR_MINSRTEST01_ADDRESS";
const VESTING_ADDRESS = "YOUR_VESTING_ADDRESS";
const REWARD_EMISSION_ADDRESS = "YOUR_REWARD_EMISSION_ADDRESS";
const GOVERNANCE_ADDRESS = "YOUR_GOVERNANCE_ADDRESS";
const TREASURY_ADDRESS = "YOUR_TREASURY_ADDRESS";

// ABI của các hợp đồng (trích xuất từ artifacts hoặc Hardhat)
const MTNSRTEST01_ABI = [
  "function mint(address to, uint256 amount) external",
  "function burn(uint256 amount) external",
  "function burnFrom(address account, uint256 amount) external",
  "function freezeAccount(address account, bool freeze) external",
  "function balanceOf(address account) view returns (uint256)",
  "function totalSupplyCap() view returns (uint256)",
  "function frozenAccounts(address account) view returns (bool)"
];
const VESTING_ABI = [
  "function initializeVesting(uint256 depositAmount) external",
  "function setupVesting(address recipient, uint256 totalAmount, uint256 startTime, uint256 duration) external",
  "function releaseVesting(address recipient) external",
  "function topUpVesting(uint256 amount) external",
  "function schedules(address recipient) view returns (address, uint256, uint256, uint256, uint256)"
];
const REWARD_EMISSION_ABI = [
  "function initializeVaultAndEpoch(uint256 depositAmount) external",
  "function topUpVault(uint256 amount) external",
  "function emitReward() external",
  "function extractFromEpochPool(address recipient, uint256 amount) external",
  "function updateEmissionParams(uint256 newTotalSupply, uint256 newHalvingInterval) external",
  "function getEpochPoolBalance() view returns (uint256)",
  "function getEmissionCount() view returns (uint256)"
];
const GOVERNANCE_ABI = [
  "function initializeGovernance() external",
  "function propose() external",
  "function vote(uint256 proposalId) external",
  "function executeProposal(uint256 proposalId) external",
  "function proposals(uint256 proposalId) view returns (address, uint256, bool)",
  "function nextProposalId() view returns (uint256)"
];
const TREASURY_ABI = [
  "function initializeTreasury() external",
  "function depositToTreasury(uint256 amount) external",
  "function withdrawFromTreasury(address recipient, uint256 amount) external",
  "function balance() view returns (uint256)"
];

// Khởi tạo ví (thay YOUR_PRIVATE_KEY bằng private key của bạn)
const PRIVATE_KEY = "YOUR_PRIVATE_KEY";
const wallet = new ethers.Wallet(PRIVATE_KEY, provider);

// Khởi tạo instance hợp đồng
const tokenContract = new ethers.Contract(TOKEN_ADDRESS, MTNSRTEST01_ABI, wallet);
const vestingContract = new ethers.Contract(VESTING_ADDRESS, VESTING_ABI, wallet);
const rewardEmissionContract = new ethers.Contract(REWARD_EMISSION_ADDRESS, REWARD_EMISSION_ABI, wallet);
const governanceContract = new ethers.Contract(GOVERNANCE_ADDRESS, GOVERNANCE_ABI, wallet);
const treasuryContract = new ethers.Contract(TREASURY_ADDRESS, TREASURY_ABI, wallet);

async function main() {
  // 1. Tương tác với MTNSRTEST01
  console.log("=== MTNSRTEST01 ===");
  // Kiểm tra số dư của ví
  const balance = await tokenContract.balanceOf(wallet.address);
  console.log("Balance:", ethers.utils.formatUnits(balance, 8), "MTNSRTEST01");
  // Mint token (chỉ owner)
  await tokenContract.mint(wallet.address, ethers.utils.parseUnits("1000", 8));
  console.log("Minted 1000 MTNSRTEST01");
  // Burn token
  await tokenContract.burn(ethers.utils.parseUnits("100", 8));
  console.log("Burned 100 MTNSRTEST01");
  // Freeze tài khoản
  await tokenContract.freezeAccount("0xSOME_ADDRESS", true);
  console.log("Froze account 0xSOME_ADDRESS");

  // 2. Tương tác với Vesting
  console.log("\n=== Vesting ===");
  // Khởi tạo vesting
  await vestingContract.initializeVesting(ethers.utils.parseUnits("1000000", 8));
  console.log("Initialized vesting with 1M tokens");
  // Thiết lập lịch vesting
  const startTime = Math.floor(Date.now() / 1000) + 3600; // 1 giờ sau
  await vestingContract.setupVesting(
    "0xRECIPIENT_ADDRESS",
    ethers.utils.parseUnits("500000", 8),
    startTime,
    30 * 24 * 60 * 60 // 30 ngày
  );
  console.log("Set up vesting for 0xRECIPIENT_ADDRESS");
  // Giải phóng token
  await vestingContract.releaseVesting("0xRECIPIENT_ADDRESS");
  console.log("Released vested tokens");

  // 3. Tương tác với RewardEmission
  console.log("\n=== RewardEmission ===");
  // Khởi tạo vault
  await rewardEmissionContract.initializeVaultAndEpoch(ethers.utils.parseUnits("1000000", 8));
  console.log("Initialized vault with 1M tokens");
  // Phát hành phần thưởng
  await rewardEmissionContract.emitReward();
  console.log("Emitted reward");
  // Rút từ epoch pool
  await rewardEmissionContract.extractFromEpochPool("0xRECIPIENT_ADDRESS", ethers.utils.parseUnits("10000", 8));
  console.log("Extracted 10K tokens from epoch pool");
  // Kiểm tra số dư epoch pool
  const epochBalance = await rewardEmissionContract.getEpochPoolBalance();
  console.log("Epoch pool balance:", ethers.utils.formatUnits(epochBalance, 8));

  // 4. Tương tác với Governance
  console.log("\n=== Governance ===");
  // Tạo đề xuất
  await governanceContract.propose();
  console.log("Created proposal");
  // Bỏ phiếu
  await governanceContract.vote(0);
  console.log("Voted for proposal 0");
  // Thực thi đề xuất
  await governanceContract.executeProposal(0);
  console.log("Executed proposal 0");
  // Kiểm tra proposal
  const proposal = await governanceContract.proposals(0);
  console.log("Proposal 0:", proposal);

  // 5. Tương tác với Treasury
  console.log("\n=== Treasury ===");
  // Gửi token vào kho bạc
  await treasuryContract.depositToTreasury(ethers.utils.parseUnits("100000", 8));
  console.log("Deposited 100K tokens to treasury");
  // Rút token
  await treasuryContract.withdrawFromTreasury("0xRECIPIENT_ADDRESS", ethers.utils.parseUnits("50000", 8));
  console.log("Withdrew 50K tokens to 0xRECIPIENT_ADDRESS");
  // Kiểm tra số dư kho bạc
  const treasuryBalance = await treasuryContract.balance();
  console.log("Treasury balance:", ethers.utils.formatUnits(treasuryBalance, 8));
}

main().catch((error) => {
  console.error("Error:", error);
  process.exitCode = 1;
});