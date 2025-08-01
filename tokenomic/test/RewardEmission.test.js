const { expect } = require("chai");
const { ethers } = require("hardhat");
const { parseUnits } = ethers; // Ethers v6

describe("RewardEmission", function () {
  let token, rewardEmission, owner, addr1;

  const totalSupply = parseUnits("1000000000", 8); // 1 tỷ token (decimals = 8)
  const emissionIntervalSecs = 5 * 24 * 60 * 60; // 5 ngày
  const halvingIntervalSecs = 4 * 365 * 24 * 60 * 60; // 4 năm
  const periodsPerHalving = BigInt(halvingIntervalSecs / emissionIntervalSecs); // 292
  const initialReward = totalSupply / (2n * periodsPerHalving); // ≈ 171_232_876_712

  beforeEach(async function () {
    [owner, addr1] = await ethers.getSigners();

    const MTNSRTEST01Factory = await ethers.getContractFactory("MTNSRTEST01");
    token = await MTNSRTEST01Factory.deploy(totalSupply);

    const RewardEmissionFactory = await ethers.getContractFactory("RewardEmission");
    rewardEmission = await RewardEmissionFactory.deploy(
      token.getAddress(),
      totalSupply,
      emissionIntervalSecs,
      halvingIntervalSecs
    );
    await rewardEmission.waitForDeployment();

    // Cấp thêm token và approve
    await token.mint(await owner.getAddress(), totalSupply);
    await token.approve(await rewardEmission.getAddress(), totalSupply);
  });

  it("Should initialize vault and emit reward correctly", async function () {
    await rewardEmission.initializeVaultAndEpoch(totalSupply);
    expect(await token.balanceOf(await rewardEmission.getAddress())).to.equal(totalSupply);

    await ethers.provider.send("evm_increaseTime", [emissionIntervalSecs]);
    await ethers.provider.send("evm_mine");

    await rewardEmission.emitReward();
    const epochBalance = await rewardEmission.getEpochPoolBalance();

    // So sánh với initialReward
    expect(epochBalance).to.be.closeTo(initialReward, parseUnits("1", 8));
  });

  it("Should respect halving interval", async function () {
    await rewardEmission.initializeVaultAndEpoch(totalSupply);

    const emissions = Number(periodsPerHalving) + 1; // 293 emissions
    for (let i = 0; i < emissions; i++) {
      await ethers.provider.send("evm_increaseTime", [emissionIntervalSecs]);
      await ethers.provider.send("evm_mine");
      await rewardEmission.emitReward();
    }

    const epochBalance = await rewardEmission.getEpochPoolBalance();

    // Tính reward đúng theo stepwise halving
    let totalReward = 0n;
    for (let i = 0; i < emissions; i++) {
      const halvings = Math.floor(i / Number(periodsPerHalving));
      const shift = halvings > 63 ? 63 : halvings;
      const adjustedReward = initialReward >> BigInt(shift);
      totalReward += adjustedReward;
    }

    expect(epochBalance).to.be.closeTo(totalReward, parseUnits("1", 8));
  });


  it("Should allow owner to extract from epoch pool", async function () {
    await rewardEmission.initializeVaultAndEpoch(totalSupply);
    await ethers.provider.send("evm_increaseTime", [emissionIntervalSecs]);
    await ethers.provider.send("evm_mine");
    await rewardEmission.emitReward();

    const extractAmount = parseUnits("100", 8);
    await rewardEmission.extractFromEpochPool(await addr1.getAddress(), extractAmount);
    expect(await token.balanceOf(await addr1.getAddress())).to.equal(extractAmount);
  });
});
