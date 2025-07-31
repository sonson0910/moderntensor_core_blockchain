const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Treasury", function () {
  let MTNSRTEST01, token, Treasury, treasury, owner, addr1;

  beforeEach(async function () {
    [owner, addr1] = await ethers.getSigners();
    const MTNSRTEST01Factory = await ethers.getContractFactory("MTNSRTEST01");
    token = await MTNSRTEST01Factory.deploy();
    await token.deployed();

    const TreasuryFactory = await ethers.getContractFactory("Treasury");
    treasury = await TreasuryFactory.deploy(token.address);
    await treasury.deployed();

    await token.mint(owner.address, ethers.utils.parseUnits("1000000", 8));
    await token.approve(treasury.address, ethers.utils.parseUnits("1000000", 8));
  });

  it("Should deposit tokens to treasury", async function () {
    await treasury.depositToTreasury(ethers.utils.parseUnits("1000000", 8));
    expect(await token.balanceOf(treasury.address)).to.equal(ethers.utils.parseUnits("1000000", 8));
  });

  it("Should allow owner to withdraw tokens", async function () {
    await treasury.depositToTreasury(ethers.utils.parseUnits("1000000", 8));
    await treasury.withdrawFromTreasury(addr1.address, ethers.utils.parseUnits("500000", 8));
    expect(await token.balanceOf(addr1.address)).to.equal(ethers.utils.parseUnits("500000", 8));
  });

  it("Should prevent non-owner from withdrawing", async function () {
    await treasury.depositToTreasury(ethers.utils.parseUnits("1000000", 8));
    await expect(
      treasury.connect(addr1).withdrawFromTreasury(addr1.address, ethers.utils.parseUnits("1000", 8))
    ).to.be.revertedWith("Ownable: caller is not the owner");
  });
});