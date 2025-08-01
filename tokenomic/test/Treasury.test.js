const hre = require("hardhat");
const { expect } = require("chai");

describe("Treasury", function () {
  let token, treasury, owner, addr1;

  beforeEach(async function () {
    [owner, addr1] = await hre.ethers.getSigners();

    const Token = await hre.ethers.getContractFactory("MTNSRTEST01");
    token = await Token.deploy(hre.ethers.parseUnits("1000000", 8));
    await token.waitForDeployment();

    const tokenAddress = await token.getAddress(); // ✅ thay vì token.target

    const Treasury = await hre.ethers.getContractFactory("Treasury");
    treasury = await Treasury.deploy(tokenAddress);
    await treasury.waitForDeployment();

    await token.mint(owner.address, hre.ethers.parseUnits("1000000", 8));
    await token.approve(await treasury.getAddress(), hre.ethers.parseUnits("1000000", 8)); // ✅ không dùng .address
  });

  it("Should deposit tokens to treasury", async function () {
    await treasury.depositToTreasury(hre.ethers.parseUnits("1000000", 8));
    expect(await token.balanceOf(await treasury.getAddress())).to.equal(hre.ethers.parseUnits("1000000", 8));
    expect(await treasury.balance()).to.equal(hre.ethers.parseUnits("1000000", 8));
  });

  it("Should allow owner to withdraw tokens", async function () {
    await treasury.depositToTreasury(hre.ethers.parseUnits("1000000", 8));
    await treasury.withdrawFromTreasury(addr1.address, hre.ethers.parseUnits("500000", 8));
    expect(await token.balanceOf(addr1.address)).to.equal(hre.ethers.parseUnits("500000", 8));
    expect(await treasury.balance()).to.equal(hre.ethers.parseUnits("500000", 8));
  });

  it("Should prevent non-owner from withdrawing", async function () {
    await treasury.depositToTreasury(hre.ethers.parseUnits("1000000", 8));
    await expect(
      treasury.connect(addr1).withdrawFromTreasury(addr1.address, hre.ethers.parseUnits("1000", 8))
    ).to.be.revertedWith("Ownable: caller is not the owner");
  });
});
