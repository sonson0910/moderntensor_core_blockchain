const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Vesting", function () {
  let MTNSRTEST01, token, Vesting, vesting, owner, addr1;

  beforeEach(async function () {
    [owner, addr1] = await ethers.getSigners();
    const MTNSRTEST01Factory = await ethers.getContractFactory("MTNSRTEST01");
    token = await MTNSRTEST01Factory.deploy();
    await token.deployed();

    const VestingFactory = await ethers.getContractFactory("Vesting");
    vesting = await VestingFactory.deploy(token.address);
    await vesting.deployed();

    await token.mint(owner.address, ethers.utils.parseUnits("1000000", 8));
    await token.approve(vesting.address, ethers.utils.parseUnits("1000000", 8));
  });

  it("Should initialize vesting correctly", async function () {
    await vesting.initializeVesting(ethers.utils.parseUnits("1000000", 8));
    expect(await token.balanceOf(vesting.address)).to.equal(ethers.utils.parseUnits("1000000", 8));
  });

  it("Should setup and release vesting correctly", async function () {
    await vesting.initializeVesting(ethers.utils.parseUnits("1000000", 8));
    const startTime = Math.floor(Date.now() / 1000);
    await vesting.setupVesting(
      addr1.address,
      ethers.utils.parseUnits("1000", 8),
      startTime,
      30 * 24 * 60 * 60 // 30 days
    );

    // Fast-forward thời gian (Hardhat Network)
    await ethers.provider.send("evm_increaseTime", [15 * 24 * 60 * 60]); // 15 days
    await ethers.provider.send("evm_mine");

    await vesting.releaseVesting(addr1.address);
    const balance = await token.balanceOf(addr1.address);
    expect(balance).to.be.closeTo(ethers.utils.parseUnits("500", 8), ethers.utils.parseUnits("1", 8)); // ~50% released
  });

  it("Should prevent non-owner from initializing vesting", async function () {
    await expect(
      vesting.connect(addr1).initializeVesting(ethers.utils.parseUnits("1000", 8))
    ).to.be.revertedWith("Ownable: caller is not the owner");
  });
});