const { expect } = require("chai");
const hre = require("hardhat");
require("dotenv").config();

describe("RewardEmission", function () {
  let token, rewardEmission, rewardDistribution, owner, addr1;
  const totalSupply = hre.ethers.parseUnits("1000000", 8); // 1M token
  const totalSupplyBigInt = BigInt(totalSupply);
  const emissionIntervalSecs = 60; // 60 giây
  const halvingIntervalSecs = 600; // 600 giây
  const periodsPerHalving = BigInt(halvingIntervalSecs / emissionIntervalSecs); // 10
  const initialReward = totalSupplyBigInt / (2n * periodsPerHalving); // 50000 * 10^8

  beforeEach(async function () {
    [owner, addr1] = await hre.ethers.getSigners();

    // Deploy MTNSRTEST01
    const TokenFactory = await hre.ethers.getContractFactory("MTNSRTEST01");
    token = await TokenFactory.deploy(totalSupply);
    await token.waitForDeployment();

    // Mint và approve token
    await token.mint(owner.address, totalSupply);
    await token.approve(owner.address, totalSupply);

    // Deploy RewardEmission
    const RewardEmissionFactory = await hre.ethers.getContractFactory("RewardEmission");
    rewardEmission = await RewardEmissionFactory.deploy(
      token.target,
      totalSupply,
      emissionIntervalSecs,
      halvingIntervalSecs
    );
    await rewardEmission.waitForDeployment();

    // Deploy RewardDistribution
    const RewardDistributionFactory = await hre.ethers.getContractFactory("RewardDistribution");
    rewardDistribution = await RewardDistributionFactory.deploy(token.target);
    await rewardDistribution.waitForDeployment();

    // Link emission -> distributor
    await rewardEmission.setRewardDistributor(rewardDistribution.target);
    await rewardDistribution.setRewardEmission(rewardEmission.target);

    // Approve token cho RewardEmission
    await token.approve(rewardEmission.target, totalSupply);
  });

  it("Should initialize vault and emit reward correctly", async function () {
    // Khởi tạo vault
    await rewardEmission.initializeVaultAndEpoch(totalSupply);
    expect(await token.balanceOf(rewardEmission.target)).to.equal(totalSupply);

    // Chờ interval
    await hre.ethers.provider.send("evm_increaseTime", [emissionIntervalSecs]);
    await hre.ethers.provider.send("evm_mine");

    // Gọi emitReward
    await rewardEmission.emitReward();

    // Kiểm tra số dư chuyển sang distributor
    const distributorBalance = await token.balanceOf(rewardDistribution.target);
    expect(distributorBalance).to.be.closeTo(initialReward, hre.ethers.parseUnits("1", 8));

    // Kiểm tra availableBalance trong RewardDistribution
    const availableBalance = await rewardDistribution.getAvailableBalance();
    expect(availableBalance).to.be.closeTo(initialReward, hre.ethers.parseUnits("1", 8));
  });

  it("Should respect halving schedule", async function () {
    // Khởi tạo vault
    await rewardEmission.initializeVaultAndEpoch(totalSupply);

    // Thực hiện nhiều lần emission để kiểm tra halving
    const emissions = Number(periodsPerHalving) + 1; // 11 lần
    let expectedTotal = 0n;

    for (let i = 0; i < emissions; i++) {
      await hre.ethers.provider.send("evm_increaseTime", [emissionIntervalSecs]);
      await hre.ethers.provider.send("evm_mine");

      await rewardEmission.emitReward();

      const halvings = Math.floor(i / Number(periodsPerHalving));
      const shift = halvings > 63 ? 63 : halvings;
      const reward = initialReward / BigInt(2 ** shift);
      expectedTotal += reward;
    }

    // Kiểm tra số dư trong distributor
    const distributorBalance = await token.balanceOf(rewardDistribution.target);
    expect(distributorBalance).to.be.closeTo(expectedTotal, hre.ethers.parseUnits("1", 8));

    // Kiểm tra availableBalance trong RewardDistribution
    const availableBalance = await rewardDistribution.getAvailableBalance();
    expect(availableBalance).to.be.closeTo(expectedTotal, hre.ethers.parseUnits("1", 8));
  });
});