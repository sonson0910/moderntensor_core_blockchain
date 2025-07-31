const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("RewardEmission", function () {
  let MTNSRTEST01, token, RewardEmission, rewardEmission, owner, addr1;

  beforeEach(async function () {
    [owner, addr1] = await ethers.getSigners();
    const MTNSRTEST01Factory = await ethers.getContractFactory("MTNSRTEST01");
    token = await MTNSRTEST01Factory.deploy();
    await token.deployed();

    const RewardEmissionFactory = await ethers.getContractFactory("RewardEmission");
    rewardEmission = await RewardEmissionFactory.deploy(token.address);
    await rewardEmission.deployed();

    await token.mint(owner.address, ethers.utils.parseUnits("1000000", 8));
    await token.approve(rewardEmission.address, ethers.utils.parseUnits("1000000", 8));
  });

  it("Should initialize vault and emit reward correctly", async function () {
    await rewardEmission.initializeVaultAndEpoch(ethers.utils.parseUnits("1000000", 8));
    expect(await token.balanceOf(rewardEmission.address)).to.equal(ethers.utils.parseUnits("1000000", 8));

    await rewardEmission.emitReward();
    const epochBalance = await rewardEmission.getEpochPoolBalance();
    expect(epochBalance).to.be.closeTo(ethers.utils.parseUnits("850340", 8), ethers.utils.parseUnits("1", 8));
  });

  it("Should respect halving interval", async function () {
    await rewardEmission.initializeVaultAndEpoch(ethers.utils.parseUnits("1000000", 8));
    await rewardEmission.emitReward();

    // Fast-forward 4 years
    await ethers.provider.send("evm_increaseTime", [4 * 365 * 24 * 60 * 60]);
    await ethers.provider.send("evm_mine");

    await rewardEmission.emitReward();
    const epochBalance = await rewardEmission.getEpochPoolBalance();
    expect(epochBalance).to.be.closeTo(ethers.utils.parseUnits("850340", 8).div(2), ethers.utils.parseUnits("1", 8)); // Halved
  });

  it("Should allow owner to extract from epoch pool", async function () {
    await rewardEmission.initializeVaultAndEpoch(ethers.utils.parseUnits("1000000", 8));
    await rewardEmission.emitReward();
    await rewardEmission.extractFromEpochPool(addr1.address, ethers.utils.parseUnits("10000", 8));
    expect(await token.balanceOf(addr1.address)).to.equal(ethers.utils.parseUnits("10000", 8));
  });
});