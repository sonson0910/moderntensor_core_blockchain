const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Governance", function () {
  let MTNSRTEST01, token, Governance, governance, owner, addr1;

  beforeEach(async function () {
    [owner, addr1] = await ethers.getSigners();
    const MTNSRTEST01Factory = await ethers.getContractFactory("MTNSRTEST01");
    token = await MTNSRTEST01Factory.deploy();
    await token.deployed();

    const GovernanceFactory = await ethers.getContractFactory("Governance");
    governance = await GovernanceFactory.deploy(token.address);
    await governance.deployed();

    await token.mint(addr1.address, ethers.utils.parseUnits("1000", 8));
  });

  it("Should allow token holder to propose", async function () {
    await governance.connect(addr1).propose();
    const nextProposalId = await governance.nextProposalId();
    expect(nextProposalId).to.equal(1);
  });

  it("Should allow token holder to vote", async function () {
    await governance.connect(addr1).propose();
    await governance.connect(addr1).vote(0);
    const proposal = await governance.proposals(0);
    expect(proposal.votes).to.equal(ethers.utils.parseUnits("1000", 8));
  });

  it("Should allow owner to execute proposal", async function () {
    await governance.connect(addr1).propose();
    await governance.connect(addr1).vote(0);
    await governance.executeProposal(0);
    const proposal = await governance.proposals(0);
    expect(proposal.executed).to.be.true;
  });
});