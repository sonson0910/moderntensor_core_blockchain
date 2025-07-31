const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("MTNSRTEST01", function () {
  let MTNSRTEST01, token, owner, addr1, addr2;

  beforeEach(async function () {
    [owner, addr1, addr2] = await ethers.getSigners();
    const MTNSRTEST01Factory = await ethers.getContractFactory("MTNSRTEST01");
    token = await MTNSRTEST01Factory.deploy();
    await token.deployed();
  });

  it("Should initialize with correct total supply and decimals", async function () {
    expect(await token.totalSupplyCap()).to.equal(ethers.utils.parseUnits("1000000000", 8));
    expect(await token.decimals()).to.equal(8);
  });

  it("Should allow owner to mint tokens", async function () {
    await token.mint(addr1.address, ethers.utils.parseUnits("1000", 8));
    expect(await token.balanceOf(addr1.address)).to.equal(ethers.utils.parseUnits("1000", 8));
  });

  it("Should allow user to burn tokens", async function () {
    await token.mint(addr1.address, ethers.utils.parseUnits("1000", 8));
    await token.connect(addr1).burn(ethers.utils.parseUnits("500", 8));
    expect(await token.balanceOf(addr1.address)).to.equal(ethers.utils.parseUnits("500", 8));
  });

  it("Should allow owner to freeze/unfreeze account", async function () {
    await token.freezeAccount(addr1.address, true);
    expect(await token.frozenAccounts(addr1.address)).to.be.true;
    await expect(token.connect(addr1).transfer(addr2.address, ethers.utils.parseUnits("100", 8))).to.be.revertedWith(
      "Account is frozen"
    );
    await token.freezeAccount(addr1.address, false);
    expect(await token.frozenAccounts(addr1.address)).to.be.false;
  });

  it("Should prevent non-owner from minting", async function () {
    await expect(token.connect(addr1).mint(addr2.address, ethers.utils.parseUnits("1000", 8))).to.be.revertedWith(
      "Ownable: caller is not the owner"
    );
  });
});