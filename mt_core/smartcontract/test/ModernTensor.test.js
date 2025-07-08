const { expect } = require("chai");
const { ethers } = require("hardhat");
const { parseEther } = ethers.utils;

describe("ModernTensor", function () {
  let modernTensor;
  let coreToken;
  let owner;
  let miner1;
  let miner2;
  let validator1;
  let validator2;

  beforeEach(async function () {
    [owner, miner1, miner2, validator1, validator2] = await ethers.getSigners();

    // Deploy mock CORE token
    const MockCoreToken = await ethers.getContractFactory("MockCoreToken");
    coreToken = await MockCoreToken.deploy("Core Token", "CORE");
    await coreToken.deployed();

    // Deploy ModernTensor contract
    const ModernTensor = await ethers.getContractFactory("ModernTensor");
    modernTensor = await ModernTensor.deploy(coreToken.address);
    await modernTensor.deployed();

    // Distribute tokens to test accounts
    await coreToken.transfer(miner1.address, parseEther("10000"));
    await coreToken.transfer(miner2.address, parseEther("10000"));
    await coreToken.transfer(validator1.address, parseEther("10000"));
    await coreToken.transfer(validator2.address, parseEther("10000"));
  });

  describe("Deployment", function () {
    it("Should set the right owner", async function () {
      expect(await modernTensor.owner()).to.equal(owner.address);
    });

    it("Should set the CORE token address", async function () {
      expect(await modernTensor.coreToken()).to.equal(coreToken.address);
    });

    it("Should initialize with correct constants", async function () {
      expect(await modernTensor.MIN_MINER_STAKE()).to.equal(parseEther("100"));
      expect(await modernTensor.MIN_VALIDATOR_STAKE()).to.equal(parseEther("1000"));
      expect(await modernTensor.BASE_MULTIPLIER()).to.equal(10000);
      expect(await modernTensor.BOOST_MULTIPLIER()).to.equal(12500);
    });
  });

  describe("Subnet Management", function () {
    it("Should create a subnet", async function () {
      const tx = await modernTensor.createSubnet("Test Subnet");
      await tx.wait();

      const subnet = await modernTensor.getSubnetInfo(1);
      expect(subnet.name).to.equal("Test Subnet");
      expect(subnet.owner).to.equal(owner.address);
      expect(subnet.isActive).to.be.true;
    });

    it("Should emit SubnetCreated event", async function () {
      await expect(modernTensor.createSubnet("Test Subnet"))
        .to.emit(modernTensor, "SubnetCreated")
        .withArgs(1, "Test Subnet", owner.address);
    });
  });

  describe("Miner Registration", function () {
    let subnetId;

    beforeEach(async function () {
      const tx = await modernTensor.createSubnet("Test Subnet");
      await tx.wait();
      subnetId = 1;
    });

    it("Should register a miner", async function () {
      const stakeAmount = parseEther("100");
      const uid = ethers.utils.formatBytes32String("miner1");
      
      // Approve tokens
      await coreToken.connect(miner1).approve(modernTensor.address, stakeAmount);
      
      // Register miner
      await modernTensor.connect(miner1).registerMiner(
        uid,
        subnetId,
        stakeAmount,
        "http://miner1.example.com"
      );

      const minerInfo = await modernTensor.getMinerInfo(miner1.address);
      expect(minerInfo.uid).to.equal(uid);
      expect(minerInfo.stake).to.equal(stakeAmount);
      expect(minerInfo.owner).to.equal(miner1.address);
      expect(minerInfo.status).to.equal(1); // ACTIVE
    });

    it("Should emit MinerRegistered event", async function () {
      const stakeAmount = parseEther("100");
      const uid = ethers.utils.formatBytes32String("miner1");
      
      await coreToken.connect(miner1).approve(modernTensor.address, stakeAmount);
      
      await expect(modernTensor.connect(miner1).registerMiner(
        uid,
        subnetId,
        stakeAmount,
        "http://miner1.example.com"
      ))
        .to.emit(modernTensor, "MinerRegistered")
        .withArgs(miner1.address, uid, subnetId, stakeAmount, "http://miner1.example.com");
    });

    it("Should fail if stake is below minimum", async function () {
      const stakeAmount = parseEther("99");
      const uid = ethers.utils.formatBytes32String("miner1");
      
      await coreToken.connect(miner1).approve(modernTensor.address, stakeAmount);
      
      await expect(modernTensor.connect(miner1).registerMiner(
        uid,
        subnetId,
        stakeAmount,
        "http://miner1.example.com"
      )).to.be.revertedWith("Insufficient stake amount");
    });

    it("Should fail if miner already registered", async function () {
      const stakeAmount = parseEther("100");
      const uid = ethers.utils.formatBytes32String("miner1");
      
      await coreToken.connect(miner1).approve(modernTensor.address, stakeAmount.mul(2));
      
      // Register first time
      await modernTensor.connect(miner1).registerMiner(
        uid,
        subnetId,
        stakeAmount,
        "http://miner1.example.com"
      );
      
      // Try to register again
      await expect(modernTensor.connect(miner1).registerMiner(
        uid,
        subnetId,
        stakeAmount,
        "http://miner1.example.com"
      )).to.be.revertedWith("Miner already registered");
    });
  });

  describe("Validator Registration", function () {
    let subnetId;

    beforeEach(async function () {
      const tx = await modernTensor.createSubnet("Test Subnet");
      await tx.wait();
      subnetId = 1;
    });

    it("Should register a validator", async function () {
      const stakeAmount = parseEther("1000");
      const uid = ethers.utils.formatBytes32String("validator1");
      
      await coreToken.connect(validator1).approve(modernTensor.address, stakeAmount);
      
      await modernTensor.connect(validator1).registerValidator(
        uid,
        subnetId,
        stakeAmount,
        "http://validator1.example.com"
      );

      const validatorInfo = await modernTensor.getValidatorInfo(validator1.address);
      expect(validatorInfo.uid).to.equal(uid);
      expect(validatorInfo.stake).to.equal(stakeAmount);
      expect(validatorInfo.owner).to.equal(validator1.address);
      expect(validatorInfo.status).to.equal(1); // ACTIVE
    });

    it("Should fail if stake is below minimum", async function () {
      const stakeAmount = parseEther("999");
      const uid = ethers.utils.formatBytes32String("validator1");
      
      await coreToken.connect(validator1).approve(modernTensor.address, stakeAmount);
      
      await expect(modernTensor.connect(validator1).registerValidator(
        uid,
        subnetId,
        stakeAmount,
        "http://validator1.example.com"
      )).to.be.revertedWith("Insufficient stake amount");
    });
  });

  describe("Bitcoin Staking", function () {
    let subnetId;

    beforeEach(async function () {
      const tx = await modernTensor.createSubnet("Test Subnet");
      await tx.wait();
      subnetId = 1;

      // Register a miner
      const stakeAmount = parseEther("100");
      const uid = ethers.utils.formatBytes32String("miner1");
      
      await coreToken.connect(miner1).approve(modernTensor.address, stakeAmount);
      await modernTensor.connect(miner1).registerMiner(
        uid,
        subnetId,
        stakeAmount,
        "http://miner1.example.com"
      );
    });

    it("Should allow Bitcoin staking", async function () {
      const btcAmount = parseEther("1"); // 1 BTC worth
      const lockTime = Math.floor(Date.now() / 1000) + 86400; // 24 hours from now
      const txHash = ethers.utils.formatBytes32String("btc_tx_hash");

      await modernTensor.connect(miner1).stakeBitcoin(txHash, btcAmount, lockTime);

      const bitcoinStakes = await modernTensor.getBitcoinStakes(miner1.address);
      expect(bitcoinStakes.length).to.equal(1);
      expect(bitcoinStakes[0].amount).to.equal(btcAmount);
      expect(bitcoinStakes[0].isActive).to.be.true;

      const minerInfo = await modernTensor.getMinerInfo(miner1.address);
      expect(minerInfo.bitcoinStake).to.equal(btcAmount);
    });

    it("Should emit BitcoinStaked event", async function () {
      const btcAmount = parseEther("1");
      const lockTime = Math.floor(Date.now() / 1000) + 86400;
      const txHash = ethers.utils.formatBytes32String("btc_tx_hash");

      await expect(modernTensor.connect(miner1).stakeBitcoin(txHash, btcAmount, lockTime))
        .to.emit(modernTensor, "BitcoinStaked")
        .withArgs(miner1.address, txHash, btcAmount, lockTime);
    });

    it("Should fail if not registered", async function () {
      const btcAmount = parseEther("1");
      const lockTime = Math.floor(Date.now() / 1000) + 86400;
      const txHash = ethers.utils.formatBytes32String("btc_tx_hash");

      await expect(modernTensor.connect(miner2).stakeBitcoin(txHash, btcAmount, lockTime))
        .to.be.revertedWith("Must be registered miner or validator");
    });
  });

  describe("Staking Tiers", function () {
    let subnetId;

    beforeEach(async function () {
      const tx = await modernTensor.createSubnet("Test Subnet");
      await tx.wait();
      subnetId = 1;
    });

    it("Should calculate BASE tier for low stakes", async function () {
      const stakeAmount = parseEther("100");
      const uid = ethers.utils.formatBytes32String("miner1");
      
      await coreToken.connect(miner1).approve(modernTensor.address, stakeAmount);
      await modernTensor.connect(miner1).registerMiner(
        uid,
        subnetId,
        stakeAmount,
        "http://miner1.example.com"
      );

      const tier = await modernTensor.calculateStakingTier(miner1.address);
      expect(tier).to.equal(0); // BASE_TIER
    });

    it("Should calculate BOOST tier for medium stakes", async function () {
      const stakeAmount = parseEther("1000");
      const uid = ethers.utils.formatBytes32String("miner1");
      
      await coreToken.connect(miner1).approve(modernTensor.address, stakeAmount);
      await modernTensor.connect(miner1).registerMiner(
        uid,
        subnetId,
        stakeAmount,
        "http://miner1.example.com"
      );

      const tier = await modernTensor.calculateStakingTier(miner1.address);
      expect(tier).to.equal(1); // BOOST_TIER
    });

    it("Should calculate SUPER tier for high stakes", async function () {
      const stakeAmount = parseEther("10000");
      const uid = ethers.utils.formatBytes32String("miner1");
      
      await coreToken.connect(miner1).approve(modernTensor.address, stakeAmount);
      await modernTensor.connect(miner1).registerMiner(
        uid,
        subnetId,
        stakeAmount,
        "http://miner1.example.com"
      );

      const tier = await modernTensor.calculateStakingTier(miner1.address);
      expect(tier).to.equal(2); // SUPER_TIER
    });

    it("Should calculate SATOSHI tier for very high stakes", async function () {
      const stakeAmount = parseEther("50000");
      const uid = ethers.utils.formatBytes32String("miner1");
      
      await coreToken.connect(miner1).approve(modernTensor.address, stakeAmount);
      await modernTensor.connect(miner1).registerMiner(
        uid,
        subnetId,
        stakeAmount,
        "http://miner1.example.com"
      );

      const tier = await modernTensor.calculateStakingTier(miner1.address);
      expect(tier).to.equal(3); // SATOSHI_TIER
    });
  });

  describe("Score Updates", function () {
    let subnetId;

    beforeEach(async function () {
      const tx = await modernTensor.createSubnet("Test Subnet");
      await tx.wait();
      subnetId = 1;

      // Register a miner
      const stakeAmount = parseEther("100");
      const uid = ethers.utils.formatBytes32String("miner1");
      
      await coreToken.connect(miner1).approve(modernTensor.address, stakeAmount);
      await modernTensor.connect(miner1).registerMiner(
        uid,
        subnetId,
        stakeAmount,
        "http://miner1.example.com"
      );
    });

    it("Should update miner scores", async function () {
      await modernTensor.updateMinerScores(miner1.address, 8000, 9000);

      const minerInfo = await modernTensor.getMinerInfo(miner1.address);
      expect(minerInfo.lastPerformance).to.equal(8000);
      expect(minerInfo.trustScore).to.equal(9000);
    });

    it("Should emit MinerScoresUpdated event", async function () {
      await expect(modernTensor.updateMinerScores(miner1.address, 8000, 9000))
        .to.emit(modernTensor, "MinerScoresUpdated")
        .withArgs(miner1.address, 8000, 9000);
    });

    it("Should fail if not owner", async function () {
      await expect(modernTensor.connect(miner1).updateMinerScores(miner1.address, 8000, 9000))
        .to.be.revertedWith("Ownable: caller is not the owner");
    });
  });

  describe("View Functions", function () {
    let subnetId;

    beforeEach(async function () {
      const tx = await modernTensor.createSubnet("Test Subnet");
      await tx.wait();
      subnetId = 1;

      // Register miners and validators
      const stakeAmount1 = parseEther("100");
      const stakeAmount2 = parseEther("1000");
      const uid1 = ethers.utils.formatBytes32String("miner1");
      const uid2 = ethers.utils.formatBytes32String("validator1");
      
      await coreToken.connect(miner1).approve(modernTensor.address, stakeAmount1);
      await coreToken.connect(validator1).approve(modernTensor.address, stakeAmount2);
      
      await modernTensor.connect(miner1).registerMiner(
        uid1,
        subnetId,
        stakeAmount1,
        "http://miner1.example.com"
      );
      
      await modernTensor.connect(validator1).registerValidator(
        uid2,
        subnetId,
        stakeAmount2,
        "http://validator1.example.com"
      );
    });

    it("Should return all miners", async function () {
      const miners = await modernTensor.getAllMiners();
      expect(miners.length).to.equal(1);
      expect(miners[0]).to.equal(miner1.address);
    });

    it("Should return all validators", async function () {
      const validators = await modernTensor.getAllValidators();
      expect(validators.length).to.equal(1);
      expect(validators[0]).to.equal(validator1.address);
    });

    it("Should return all subnets", async function () {
      const subnets = await modernTensor.getAllSubnets();
      expect(subnets.length).to.equal(1);
      expect(subnets[0]).to.equal(1);
    });
  });
}); 