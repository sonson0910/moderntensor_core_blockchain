const hre = require("hardhat");
const { expect } = require("chai");

describe("Vesting", function () {
  let token, vesting, owner, addr1;

  beforeEach(async function () {
    [owner, addr1] = await hre.ethers.getSigners();

    const Token = await hre.ethers.getContractFactory("MTNSRTEST01");
    token = await Token.deploy(hre.ethers.parseUnits("1000000", 8));
    await token.waitForDeployment();

    const tokenAddress = await token.getAddress();

    const Vesting = await hre.ethers.getContractFactory("Vesting");
    vesting = await Vesting.deploy(tokenAddress);
    await vesting.waitForDeployment();

    const vestingAddress = await vesting.getAddress();

    await token.mint(owner.address, hre.ethers.parseUnits("1000000", 8));
    await token.approve(vestingAddress, hre.ethers.parseUnits("1000000", 8));
    await vesting.initializeVesting(hre.ethers.parseUnits("1000000", 8));
  });

  it("Should initialize vesting correctly", async function () {
    const vestingAddress = await vesting.getAddress();
    const balance = await token.balanceOf(vestingAddress);
    expect(balance).to.equal(hre.ethers.parseUnits("1000000", 8));
  });

  it("Should setup and release vesting correctly", async function () {
    const block = await hre.ethers.provider.getBlock("latest");
    const currentTimestamp = block.timestamp;
    const start = currentTimestamp + 3600; // Start after 1 hour
    const duration = 30 * 24 * 60 * 60; // 30 days

    await vesting.setupVesting(addr1.address, hre.ethers.parseUnits("1000", 8), start, duration);

    // Simulate time passing (15 days)
    await hre.network.provider.send("evm_increaseTime", [15 * 24 * 60 * 60]);
    await hre.network.provider.send("evm_mine");

    await vesting.releaseVesting(addr1.address);
    const balance = await token.balanceOf(addr1.address);
    expect(balance).to.be.closeTo(hre.ethers.parseUnits("500", 8), hre.ethers.parseUnits("2", 8)); // Cho phép sai số ±200
  });

  it("Should prevent non-owner from initializing vesting again", async function () {
    await expect(
      vesting.connect(addr1).initializeVesting(hre.ethers.parseUnits("1000", 8))
    ).to.be.revertedWith("Ownable: caller is not the owner");
  });
});
