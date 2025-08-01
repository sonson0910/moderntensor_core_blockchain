const hre = require("hardhat");
const { expect } = require("chai");

describe("Governance", function () {
  let token, governance, owner, addr1;

beforeEach(async function () {
  [owner, addr1] = await hre.ethers.getSigners();

  const Token = await hre.ethers.getContractFactory("MTNSRTEST01");
  token = await Token.deploy(hre.ethers.parseUnits("1000000", 8));
  await token.waitForDeployment();

  const Governance = await hre.ethers.getContractFactory("Governance");
  governance = await Governance.deploy(token.target);
  await governance.waitForDeployment();

  await token.connect(owner).mint(addr1.address, hre.ethers.parseUnits("1000", 8));
});


  it("Should allow token holder to propose", async function () {
    await governance.connect(addr1).propose();
    const nextId = await governance.nextProposalId();
    expect(nextId).to.equal(1);
  });

  it("Should allow token holder to vote", async function () {
    await governance.connect(addr1).propose();
    await governance.connect(addr1).vote(0);
    const proposal = await governance.proposals(0);
    expect(proposal.votes).to.equal(hre.ethers.parseUnits("1000", 8));
  });

  it("Should allow owner to execute proposal", async function () {
    await governance.connect(addr1).propose();
    await governance.connect(addr1).vote(0);
    await governance.connect(owner).executeProposal(0);
    const proposal = await governance.proposals(0);
    expect(proposal.executed).to.be.true;
  });
});
