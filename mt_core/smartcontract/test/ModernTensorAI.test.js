const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("ModernTensorAI - Decentralized AI Training", function () {
    let modernTensorAI;
    let coreToken;
    let btcToken;
    let owner;
    let miner1;
    let miner2;
    let validator1;
    let validator2;
    let taskCreator;

    // Constants from contract
    const MIN_MINER_STAKE = ethers.utils.parseEther("100");
    const MIN_VALIDATOR_STAKE = ethers.utils.parseEther("1000");
    const MIN_TASK_REWARD = ethers.utils.parseEther("1");
    const MAX_TASK_REWARD = ethers.utils.parseEther("1000");

    beforeEach(async function () {
        // Get signers
        [owner, miner1, miner2, validator1, validator2, taskCreator] = await ethers.getSigners();

        // Deploy mock tokens
        const MockERC20 = await ethers.getContractFactory("MockCoreToken");
        coreToken = await MockERC20.deploy("Core Token", "CORE");
        btcToken = await MockERC20.deploy("Bitcoin Token", "BTC");

        // Deploy ModernTensorAI
        const ModernTensorAI = await ethers.getContractFactory("ModernTensorAI");
        modernTensorAI = await ModernTensorAI.deploy(coreToken.address, btcToken.address);

        // Distribute tokens to test accounts
        await coreToken.transfer(miner1.address, ethers.utils.parseEther("10000"));
        await coreToken.transfer(miner2.address, ethers.utils.parseEther("10000"));
        await coreToken.transfer(validator1.address, ethers.utils.parseEther("10000"));
        await coreToken.transfer(validator2.address, ethers.utils.parseEther("10000"));
        await coreToken.transfer(taskCreator.address, ethers.utils.parseEther("10000"));

        await btcToken.transfer(miner1.address, ethers.utils.parseEther("10"));
        await btcToken.transfer(validator1.address, ethers.utils.parseEther("10"));

        // Approve spending
        await coreToken.connect(miner1).approve(modernTensorAI.address, ethers.utils.parseEther("10000"));
        await coreToken.connect(miner2).approve(modernTensorAI.address, ethers.utils.parseEther("10000"));
        await coreToken.connect(validator1).approve(modernTensorAI.address, ethers.utils.parseEther("10000"));
        await coreToken.connect(validator2).approve(modernTensorAI.address, ethers.utils.parseEther("10000"));
        await coreToken.connect(taskCreator).approve(modernTensorAI.address, ethers.utils.parseEther("10000"));

        await btcToken.connect(miner1).approve(modernTensorAI.address, ethers.utils.parseEther("10"));
        await btcToken.connect(validator1).approve(modernTensorAI.address, ethers.utils.parseEther("10"));
    });

    describe("🏗️ Subnet Management", function () {
        it("Should create AI subnet successfully", async function () {
            const tx = await modernTensorAI.createAISubnet(
                "Foundation Models",
                0, // FOUNDATION type
                ethers.utils.formatBytes32String("gpt-architecture"),
                1000 // min compute power
            );

            const receipt = await tx.wait();
            const event = receipt.events.find(e => e.event === "SubnetCreated");
            
            expect(event.args.subnetId).to.equal(1);
            expect(event.args.name).to.equal("Foundation Models");
            expect(event.args.aiType).to.equal(0);
            expect(event.args.owner).to.equal(owner.address);
        });
    });

    describe("⛏️ Miner Registration", function () {
        beforeEach(async function () {
            // Create a subnet first
            await modernTensorAI.createAISubnet(
                "Language Models",
                1, // LANGUAGE type
                ethers.utils.formatBytes32String("transformer"),
                1000
            );
        });

        it("Should register miner with CORE stake only", async function () {
            const uid = ethers.utils.formatBytes32String("miner1");
            const specializations = [1]; // LANGUAGE
            
            await expect(
                modernTensorAI.connect(miner1).registerMiner(
                    uid,
                    1, // subnetId
                    MIN_MINER_STAKE,
                    0, // no BTC stake
                    5000, // compute power
                    specializations,
                    "http://miner1.example.com",
                    ethers.utils.formatBytes32String("gpu-capability")
                )
            ).to.emit(modernTensorAI, "MinerRegistered")
             .withArgs(miner1.address, uid, 1, MIN_MINER_STAKE);
        });
    });
}); 