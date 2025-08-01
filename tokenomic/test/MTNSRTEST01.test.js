const hre = require("hardhat");
const { expect } = require("chai");

describe("MTNSRTEST01", function () {
  let token, owner, addr1, addr2;

  beforeEach(async function () {
    [owner, addr1, addr2] = await hre.ethers.getSigners();
    const Token = await hre.ethers.getContractFactory("MTNSRTEST01");
    token = await Token.deploy(hre.ethers.parseUnits("1000000", 8));
  });

  it("Should initialize with correct total supply and decimals", async function () {
    expect(await token.totalSupplyCap()).to.equal(hre.ethers.parseUnits("1000000", 8));
    expect(await token.decimals()).to.equal(8);
  });

  it("Should allow owner to mint tokens", async function () {
    await token.mint(addr1.address, hre.ethers.parseUnits("1000", 8));
    expect(await token.balanceOf(addr1.address)).to.equal(hre.ethers.parseUnits("1000", 8));
  });

  it("Should allow user to burn tokens", async function () {
    await token.mint(addr1.address, hre.ethers.parseUnits("1000", 8));
    await token.connect(addr1).burn(hre.ethers.parseUnits("500", 8));
    expect(await token.balanceOf(addr1.address)).to.equal(hre.ethers.parseUnits("500", 8));
  });

  it("Should allow owner to burn from account", async function () {
    await token.mint(addr1.address, hre.ethers.parseUnits("1000", 8));
    await token.connect(addr1).approve(owner.address, hre.ethers.parseUnits("1000", 8));
    await token.burnFrom(addr1.address, hre.ethers.parseUnits("500", 8));
    expect(await token.balanceOf(addr1.address)).to.equal(hre.ethers.parseUnits("500", 8));
  });

  it("Should allow owner to freeze/unfreeze account", async function () {
    await token.freezeAccount(addr1.address, true);
    expect(await token.frozenAccounts(addr1.address)).to.be.true;
    await expect(
      token.connect(addr1).transfer(addr2.address, hre.ethers.parseUnits("100", 8))
    ).to.be.revertedWith("Sender account is frozen");
    await token.freezeAccount(addr1.address, false);
    expect(await token.frozenAccounts(addr1.address)).to.be.false;
  });

  it("Should prevent non-owner from minting", async function () {
    await expect(
      token.connect(addr1).mint(addr2.address, hre.ethers.parseUnits("1000", 8))
    ).to.be.revertedWith("Ownable: caller is not the owner");
  });
});
