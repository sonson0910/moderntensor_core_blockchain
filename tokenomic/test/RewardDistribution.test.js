const { expect } = require("chai");
const hre = require("hardhat");

describe("RewardEmission and RewardDistribution Integration", function () {
  let token, rewardEmission, rewardDistribution;
  let owner, subnet1, subnet2, validator1, validator2, miner1, miner2;
  let snapshotId;

  beforeEach(async () => {
    snapshotId = await hre.ethers.provider.send("evm_snapshot");

    [owner, subnet1, subnet2, validator1, validator2, miner1, miner2] = await hre.ethers.getSigners();

    const Token = await hre.ethers.getContractFactory("MTNSRTEST01");
    token = await Token.deploy(hre.ethers.parseUnits("1000000", 8));
    await token.waitForDeployment();

    const RewardEmission = await hre.ethers.getContractFactory("RewardEmission");
    rewardEmission = await RewardEmission.deploy(
      token.target,
      hre.ethers.parseUnits("1000000", 8),
      60,   // secondsPerPeriod
      600   // secondsPerHalving
    );
    await rewardEmission.waitForDeployment();

    const RewardDistribution = await hre.ethers.getContractFactory("RewardDistribution");
    rewardDistribution = await RewardDistribution.deploy(token.target);
    await rewardDistribution.waitForDeployment();

    await rewardEmission.setRewardDistributor(rewardDistribution.target);
    await rewardDistribution.setRewardEmission(rewardEmission.target);

    const supply = hre.ethers.parseUnits("1000000", 8);
    await token.mint(owner.address, supply);
    await token.approve(rewardEmission.target, supply);
    await rewardEmission.initializeVaultAndEpoch(supply);
  });

  afterEach(async () => {
    await hre.ethers.provider.send("evm_revert", [snapshotId]);
  });

  it("should emit and distribute reward properly", async () => {
    await rewardDistribution.setSubnets([subnet1.address, subnet2.address], [50, 50]);

    await rewardDistribution.setParticipants(
      0,
      [validator1.address, validator2.address],
      [50, 30],
      [miner1.address, miner2.address],
      [40, 20]
    );

    await hre.ethers.provider.send("evm_increaseTime", [60]);
    await hre.ethers.provider.send("evm_mine");

    await rewardEmission.emitReward();

    const emissionAmount = await rewardDistribution.getAvailableBalance();
    const expectedEmission = hre.ethers.parseUnits("50000", 8);
    expect(emissionAmount).to.equal(expectedEmission);

    await rewardDistribution.distributeRewards(0, emissionAmount);

    const subnetReward = emissionAmount / 2n;
    const subnetShare = subnetReward * 18n / 100n;
    const validatorPool = subnetReward * 41n / 100n;
    const minerPool = subnetReward * 41n / 100n;

    const expectedValidator1 = validatorPool * 50n / 80n;
    const expectedValidator2 = validatorPool * 30n / 80n;
    const expectedMiner1 = minerPool * 40n / 60n;
    const expectedMiner2 = minerPool * 20n / 60n;

    const tolerance = 1n;

    const checkClose = async (actual, expected) => {
      const diff = actual > expected ? actual - expected : expected - actual;
      expect(diff).to.be.lte(tolerance);
    };

    await checkClose(await token.balanceOf(subnet1.address), subnetShare);
    await checkClose(await token.balanceOf(validator1.address), expectedValidator1);
    await checkClose(await token.balanceOf(validator2.address), expectedValidator2);
    await checkClose(await token.balanceOf(miner1.address), expectedMiner1);
    await checkClose(await token.balanceOf(miner2.address), expectedMiner2);
  });
});
