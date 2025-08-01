// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/math/SafeMath.sol";
import "@openzeppelin/contracts/governance/Governor.sol";

/**
 * @title ModernTensorAI - Decentralized AI Training on Core Blockchain
 * @dev Advanced smart contract for decentralized AI model training inspired by Bittensor
 * Features: Core Consensus Algorithm, AI Task Distribution, Model Quality Validation
 */
contract ModernTensorAI is ReentrancyGuard, AccessControl {
    using SafeMath for uint256;

    // Role definitions
    bytes32 public constant VALIDATOR_ROLE = keccak256("VALIDATOR_ROLE");
    bytes32 public constant SUBNET_OWNER_ROLE = keccak256("SUBNET_OWNER_ROLE");
    bytes32 public constant GOVERNANCE_ROLE = keccak256("GOVERNANCE_ROLE");

    // Core tokens
    IERC20 public immutable coreToken;
    IERC20 public immutable btcToken; // Wrapped Bitcoin on Core

    // === CORE CONSENSUS PARAMETERS ===
    uint256 public constant CONSENSUS_WINDOW = 100; // blocks
    uint256 public constant MIN_CONSENSUS_VALIDATORS = 3;
    uint256 public constant CONSENSUS_THRESHOLD = 6667; // 66.67% in basis points
    uint256 public constant INCENTIVE_DECAY = 9900; // 99% in basis points

    // === AI TASK PARAMETERS ===
    uint256 public constant MAX_MODEL_SIZE = 1000000; // bytes
    uint256 public constant TASK_TIMEOUT = 3600; // seconds
    uint256 public constant MIN_TASK_REWARD = 1e18; // 1 CORE
    uint256 public constant MAX_TASK_REWARD = 1000e18; // 1000 CORE

    // === STAKING PARAMETERS ===
    uint256 public constant MIN_MINER_STAKE = 100e18; // 100 CORE
    uint256 public constant MIN_VALIDATOR_STAKE = 1000e18; // 1000 CORE
    uint256 public constant MIN_BTC_BOOST = 1e8; // 1 BTC (in satoshis)
    uint256 public constant BTC_BOOST_MULTIPLIER = 15000; // 150% in basis points

    // === ENUMS ===
    enum NodeStatus {
        INACTIVE,
        ACTIVE,
        SUSPENDED,
        BANNED
    }
    enum TaskStatus {
        PENDING,
        IN_PROGRESS,
        COMPLETED,
        FAILED,
        DISPUTED
    }
    enum SubnetType {
        FOUNDATION,
        LANGUAGE,
        VISION,
        MULTIMODAL,
        CUSTOM
    }

    // === AI TASK STRUCTURES ===
    struct AITask {
        bytes32 taskId;
        uint64 subnetId;
        address creator;
        SubnetType taskType;
        bytes32 dataHash; // IPFS hash of training data
        bytes32 modelRequirement; // Required model architecture hash
        uint256 reward;
        uint256 deadline;
        uint256 maxParticipants;
        uint256 difficulty; // 1-100 scale
        TaskStatus status;
        bytes32[] submittedResults;
        mapping(address => ModelSubmission) submissions;
        address[] participants;
        uint256 createdAt;
    }

    struct ModelSubmission {
        bytes32 modelHash; // IPFS hash of trained model
        bytes32 weightsHash; // Hash of model weights
        uint256 accuracy; // Reported accuracy in basis points
        uint256 loss; // Loss value * 1e18
        uint256 trainingTime; // Time spent training in seconds
        uint256 gasUsed; // Computational cost
        bytes32 validationProof; // Proof of validation
        uint256 submittedAt;
        bool validated;
        uint256 score; // Final calculated score
    }

    // === MINER STRUCTURE (AI Trainers) ===
    struct MinerNode {
        bytes32 uid;
        address owner;
        uint64 subnetId;
        uint256 coreStake;
        uint256 btcStake;
        uint256 reputation; // 0-10000 basis points
        uint256 aiPerformance; // Average model performance
        uint256 validationAccuracy; // Track validation accuracy
        uint256 tasksCompleted;
        uint256 totalRewards;
        uint256 computePower; // Self-reported compute capability
        SubnetType[] specializations;
        NodeStatus status;
        string endpoint; // API endpoint for communication
        bytes32 capabilityHash; // Hash of AI capabilities
        uint256 lastActive;
        uint256 registeredAt;
    }

    // === VALIDATOR STRUCTURE (AI Evaluators) ===
    struct ValidatorNode {
        bytes32 uid;
        address owner;
        uint64 subnetId;
        uint256 coreStake;
        uint256 btcStake;
        uint256 reputation;
        uint256 validationAccuracy;
        uint256 tasksValidated;
        uint256 totalRewards;
        uint256 consensusParticipation; // % of consensus rounds participated
        NodeStatus status;
        string endpoint;
        bytes32 validationCapability;
        uint256 lastActive;
        uint256 registeredAt;
    }

    // === SUBNET STRUCTURE (AI Specialization) ===
    struct AISubnet {
        uint64 uid;
        string name;
        SubnetType aiType;
        address owner;
        uint256 totalStake;
        uint256 minerCount;
        uint256 validatorCount;
        uint256 rewardPool;
        uint256 taskCount;
        bytes32 modelArchitecture; // Required model architecture
        uint256 minComputePower;
        uint256 consensusRate; // Target consensus rate
        bool isActive;
        mapping(bytes32 => AITask) tasks;
        bytes32[] allTasks;
        uint256 createdAt;
    }

    // === CONSENSUS TRACKING ===
    struct ConsensusRound {
        uint256 blockNumber;
        uint64 subnetId;
        bytes32 taskId;
        mapping(address => bytes32) validatorVotes; // validator -> model hash
        mapping(bytes32 => uint256) voteCounts; // model hash -> vote count
        mapping(address => bool) hasVoted;
        address[] participants;
        bytes32 winningModel;
        bool finalized;
        uint256 reward;
        uint256 startTime;
    }

    // === STATE VARIABLES ===
    mapping(address => MinerNode) public miners;
    mapping(address => ValidatorNode) public validators;
    mapping(uint64 => AISubnet) public subnets;
    mapping(bytes32 => ConsensusRound) public consensusRounds;
    mapping(address => uint256) public totalBtcStake;

    // Array tracking
    address[] public allMiners;
    address[] public allValidators;
    uint64[] public allSubnets;
    bytes32[] public activeConsensusRounds;

    // Global counters
    uint64 public nextSubnetId = 1;
    uint256 public totalCoreStaked;
    uint256 public totalBtcStaked;
    uint256 public totalTasksCreated;
    uint256 public totalModelsValidated;

    // === EVENTS ===
    event MinerRegistered(
        address indexed miner,
        bytes32 indexed uid,
        uint64 indexed subnetId,
        uint256 stake
    );
    event ValidatorRegistered(
        address indexed validator,
        bytes32 indexed uid,
        uint64 indexed subnetId,
        uint256 stake
    );
    event AITaskCreated(
        bytes32 indexed taskId,
        uint64 indexed subnetId,
        address indexed creator,
        uint256 reward
    );
    event ModelSubmitted(
        bytes32 indexed taskId,
        address indexed miner,
        bytes32 indexed modelHash,
        uint256 accuracy
    );
    event ConsensusReached(
        bytes32 indexed taskId,
        bytes32 indexed winningModel,
        uint256 reward
    );
    event IncentiveDistributed(
        address indexed recipient,
        uint256 amount,
        bytes32 indexed taskId
    );
    event SubnetCreated(
        uint64 indexed subnetId,
        string name,
        SubnetType aiType,
        address indexed owner
    );
    event ReputationUpdated(
        address indexed node,
        uint256 newReputation,
        string reason
    );

    // === CONSTRUCTOR ===
    constructor(address _coreToken, address _btcToken) {
        coreToken = IERC20(_coreToken);
        btcToken = IERC20(_btcToken);
        _setupRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _setupRole(GOVERNANCE_ROLE, msg.sender);
    }

    // === MINER REGISTRATION (AI Trainers) ===
    function registerMiner(
        bytes32 uid,
        uint64 subnetId,
        uint256 coreStakeAmount,
        uint256 btcStakeAmount,
        uint256 computePower,
        SubnetType[] memory specializations,
        string memory endpoint,
        bytes32 capabilityHash
    ) external nonReentrant {
        require(
            miners[msg.sender].owner == address(0),
            "Miner already registered"
        );
        require(coreStakeAmount >= MIN_MINER_STAKE, "Insufficient CORE stake");
        require(subnets[subnetId].isActive, "Subnet not active");
        require(computePower > 0, "Invalid compute power");

        // Transfer stakes
        require(
            coreToken.transferFrom(msg.sender, address(this), coreStakeAmount),
            "CORE transfer failed"
        );
        if (btcStakeAmount > 0) {
            require(
                btcToken.transferFrom(
                    msg.sender,
                    address(this),
                    btcStakeAmount
                ),
                "BTC transfer failed"
            );
            totalBtcStake[msg.sender] = btcStakeAmount;
            totalBtcStaked = totalBtcStaked.add(btcStakeAmount);
        }

        // Register miner
        miners[msg.sender] = MinerNode({
            uid: uid,
            owner: msg.sender,
            subnetId: subnetId,
            coreStake: coreStakeAmount,
            btcStake: btcStakeAmount,
            reputation: 5000, // Start at 50%
            aiPerformance: 0,
            validationAccuracy: 0,
            tasksCompleted: 0,
            totalRewards: 0,
            computePower: computePower,
            specializations: specializations,
            status: NodeStatus.ACTIVE,
            endpoint: endpoint,
            capabilityHash: capabilityHash,
            lastActive: block.timestamp,
            registeredAt: block.timestamp
        });

        allMiners.push(msg.sender);
        totalCoreStaked = totalCoreStaked.add(coreStakeAmount);
        subnets[subnetId].minerCount++;
        subnets[subnetId].totalStake = subnets[subnetId].totalStake.add(
            coreStakeAmount.add(btcStakeAmount)
        );

        emit MinerRegistered(msg.sender, uid, subnetId, coreStakeAmount);
    }

    // === VALIDATOR REGISTRATION (AI Evaluators) ===
    function registerValidator(
        bytes32 uid,
        uint64 subnetId,
        uint256 coreStakeAmount,
        uint256 btcStakeAmount,
        string memory endpoint,
        bytes32 validationCapability
    ) external nonReentrant {
        require(
            validators[msg.sender].owner == address(0),
            "Validator already registered"
        );
        require(
            coreStakeAmount >= MIN_VALIDATOR_STAKE,
            "Insufficient CORE stake"
        );
        require(subnets[subnetId].isActive, "Subnet not active");

        // Transfer stakes
        require(
            coreToken.transferFrom(msg.sender, address(this), coreStakeAmount),
            "CORE transfer failed"
        );
        if (btcStakeAmount > 0) {
            require(
                btcToken.transferFrom(
                    msg.sender,
                    address(this),
                    btcStakeAmount
                ),
                "BTC transfer failed"
            );
            totalBtcStake[msg.sender] = btcStakeAmount;
            totalBtcStaked = totalBtcStaked.add(btcStakeAmount);
        }

        // Register validator
        validators[msg.sender] = ValidatorNode({
            uid: uid,
            owner: msg.sender,
            subnetId: subnetId,
            coreStake: coreStakeAmount,
            btcStake: btcStakeAmount,
            reputation: 5000, // Start at 50%
            validationAccuracy: 0,
            tasksValidated: 0,
            totalRewards: 0,
            consensusParticipation: 0,
            status: NodeStatus.ACTIVE,
            endpoint: endpoint,
            validationCapability: validationCapability,
            lastActive: block.timestamp,
            registeredAt: block.timestamp
        });

        allValidators.push(msg.sender);
        _setupRole(VALIDATOR_ROLE, msg.sender);
        totalCoreStaked = totalCoreStaked.add(coreStakeAmount);
        subnets[subnetId].validatorCount++;
        subnets[subnetId].totalStake = subnets[subnetId].totalStake.add(
            coreStakeAmount.add(btcStakeAmount)
        );

        emit ValidatorRegistered(msg.sender, uid, subnetId, coreStakeAmount);
    }

    // === AI TASK CREATION ===
    function createAITask(
        uint64 subnetId,
        SubnetType taskType,
        bytes32 dataHash,
        bytes32 modelRequirement,
        uint256 reward,
        uint256 deadline,
        uint256 maxParticipants,
        uint256 difficulty
    ) external nonReentrant returns (bytes32) {
        require(subnets[subnetId].isActive, "Subnet not active");
        require(
            reward >= MIN_TASK_REWARD && reward <= MAX_TASK_REWARD,
            "Invalid reward amount"
        );
        require(deadline > block.timestamp, "Invalid deadline");
        require(
            maxParticipants > 0 && maxParticipants <= 100,
            "Invalid max participants"
        );
        require(difficulty >= 1 && difficulty <= 100, "Invalid difficulty");

        // Transfer reward to contract
        require(
            coreToken.transferFrom(msg.sender, address(this), reward),
            "Reward transfer failed"
        );

        // Generate task ID
        bytes32 taskId = keccak256(
            abi.encodePacked(
                block.timestamp,
                msg.sender,
                subnetId,
                totalTasksCreated++
            )
        );

        // Create task
        AITask storage task = subnets[subnetId].tasks[taskId];
        task.taskId = taskId;
        task.subnetId = subnetId;
        task.creator = msg.sender;
        task.taskType = taskType;
        task.dataHash = dataHash;
        task.modelRequirement = modelRequirement;
        task.reward = reward;
        task.deadline = deadline;
        task.maxParticipants = maxParticipants;
        task.difficulty = difficulty;
        task.status = TaskStatus.PENDING;
        task.createdAt = block.timestamp;

        subnets[subnetId].allTasks.push(taskId);
        subnets[subnetId].taskCount++;
        subnets[subnetId].rewardPool = subnets[subnetId].rewardPool.add(reward);

        emit AITaskCreated(taskId, subnetId, msg.sender, reward);
        return taskId;
    }

    // === MODEL SUBMISSION ===
    function submitModel(
        bytes32 taskId,
        uint64 subnetId,
        bytes32 modelHash,
        bytes32 weightsHash,
        uint256 accuracy,
        uint256 loss,
        uint256 trainingTime,
        uint256 gasUsed,
        bytes32 validationProof
    ) external nonReentrant {
        AITask storage task = subnets[subnetId].tasks[taskId];
        require(task.creator != address(0), "Task not found");
        require(
            task.status == TaskStatus.PENDING ||
                task.status == TaskStatus.IN_PROGRESS,
            "Task not active"
        );
        require(block.timestamp < task.deadline, "Task deadline passed");
        require(
            task.participants.length < task.maxParticipants,
            "Max participants reached"
        );
        require(
            miners[msg.sender].owner == msg.sender,
            "Not a registered miner"
        );
        require(miners[msg.sender].subnetId == subnetId, "Wrong subnet");

        // Check if already submitted
        require(
            task.submissions[msg.sender].modelHash == bytes32(0),
            "Already submitted"
        );

        // Add to participants if first submission
        bool isNewParticipant = true;
        for (uint256 i = 0; i < task.participants.length; i++) {
            if (task.participants[i] == msg.sender) {
                isNewParticipant = false;
                break;
            }
        }
        if (isNewParticipant) {
            task.participants.push(msg.sender);
        }

        // Store submission
        task.submissions[msg.sender] = ModelSubmission({
            modelHash: modelHash,
            weightsHash: weightsHash,
            accuracy: accuracy,
            loss: loss,
            trainingTime: trainingTime,
            gasUsed: gasUsed,
            validationProof: validationProof,
            submittedAt: block.timestamp,
            validated: false,
            score: 0
        });

        task.submittedResults.push(modelHash);
        task.status = TaskStatus.IN_PROGRESS;

        // Update miner activity
        miners[msg.sender].lastActive = block.timestamp;

        emit ModelSubmitted(taskId, msg.sender, modelHash, accuracy);

        // Trigger consensus if enough submissions
        if (task.participants.length >= MIN_CONSENSUS_VALIDATORS) {
            _initializeConsensus(taskId, subnetId);
        }
    }

    // === CONSENSUS VOTING (Core Innovation) ===
    function submitConsensusVote(
        bytes32 consensusId,
        bytes32 modelHash,
        uint256 score
    ) external onlyRole(VALIDATOR_ROLE) nonReentrant {
        ConsensusRound storage round = consensusRounds[consensusId];
        require(!round.finalized, "Consensus already finalized");
        require(!round.hasVoted[msg.sender], "Already voted");
        require(
            validators[msg.sender].subnetId == round.subnetId,
            "Wrong subnet"
        );
        require(score <= 10000, "Invalid score"); // Max 100%

        round.validatorVotes[msg.sender] = modelHash;
        round.voteCounts[modelHash] = round.voteCounts[modelHash].add(1);
        round.hasVoted[msg.sender] = true;
        round.participants.push(msg.sender);

        // Update validator activity
        validators[msg.sender].lastActive = block.timestamp;
        validators[msg.sender].consensusParticipation++;

        // Check if consensus reached
        if (round.participants.length >= MIN_CONSENSUS_VALIDATORS) {
            _finalizeConsensus(consensusId);
        }
    }

    // === SUBNET MANAGEMENT ===
    function createAISubnet(
        string memory name,
        SubnetType aiType,
        bytes32 modelArchitecture,
        uint256 minComputePower
    ) external returns (uint64) {
        uint64 subnetId = nextSubnetId++;

        AISubnet storage subnet = subnets[subnetId];
        subnet.uid = subnetId;
        subnet.name = name;
        subnet.aiType = aiType;
        subnet.owner = msg.sender;
        subnet.totalStake = 0;
        subnet.minerCount = 0;
        subnet.validatorCount = 0;
        subnet.rewardPool = 0;
        subnet.taskCount = 0;
        subnet.modelArchitecture = modelArchitecture;
        subnet.minComputePower = minComputePower;
        subnet.consensusRate = 8000; // 80% default
        subnet.isActive = true;
        subnet.createdAt = block.timestamp;

        allSubnets.push(subnetId);
        _setupRole(SUBNET_OWNER_ROLE, msg.sender);

        emit SubnetCreated(subnetId, name, aiType, msg.sender);
        return subnetId;
    }

    // === REPUTATION AND INCENTIVE SYSTEM ===
    function updateReputation(
        address nodeAddr,
        uint256 newReputation,
        string memory reason
    ) external onlyRole(GOVERNANCE_ROLE) {
        require(newReputation <= 10000, "Invalid reputation");

        if (miners[nodeAddr].owner == nodeAddr) {
            miners[nodeAddr].reputation = newReputation;
        } else if (validators[nodeAddr].owner == nodeAddr) {
            validators[nodeAddr].reputation = newReputation;
        } else {
            revert("Node not found");
        }

        emit ReputationUpdated(nodeAddr, newReputation, reason);
    }

    function calculateIncentive(
        address participant,
        bytes32 taskId,
        uint64 subnetId,
        uint256 baseReward
    ) public view returns (uint256) {
        // Get task and participant data
        AITask storage task = subnets[subnetId].tasks[taskId];
        ModelSubmission storage submission = task.submissions[participant];

        uint256 incentive = baseReward;

        // Accuracy bonus (up to 50% bonus)
        if (submission.accuracy > 5000) {
            // Above 50%
            uint256 accuracyBonus = (submission.accuracy - 5000)
                .mul(baseReward)
                .div(10000);
            incentive = incentive.add(accuracyBonus);
        }

        // Reputation multiplier
        uint256 reputation = 5000; // default
        if (miners[participant].owner == participant) {
            reputation = miners[participant].reputation;
        } else if (validators[participant].owner == participant) {
            reputation = validators[participant].reputation;
        }

        incentive = incentive.mul(reputation).div(5000); // Normalize around 50%

        // BTC staking bonus
        if (totalBtcStake[participant] >= MIN_BTC_BOOST) {
            incentive = incentive.mul(BTC_BOOST_MULTIPLIER).div(10000);
        }

        return incentive;
    }

    // === PRIVATE CONSENSUS FUNCTIONS ===
    function _initializeConsensus(bytes32 taskId, uint64 subnetId) private {
        bytes32 consensusId = keccak256(abi.encodePacked(taskId, block.number));

        ConsensusRound storage round = consensusRounds[consensusId];
        round.blockNumber = block.number;
        round.subnetId = subnetId;
        round.taskId = taskId;
        round.finalized = false;
        round.reward = subnets[subnetId].tasks[taskId].reward;
        round.startTime = block.timestamp;

        activeConsensusRounds.push(consensusId);
    }

    function _finalizeConsensus(bytes32 consensusId) private {
        ConsensusRound storage round = consensusRounds[consensusId];

        // Find winning model (most votes)
        bytes32 winningModel;
        uint256 maxVotes = 0;

        AITask storage task = subnets[round.subnetId].tasks[round.taskId];

        for (uint256 i = 0; i < task.submittedResults.length; i++) {
            bytes32 modelHash = task.submittedResults[i];
            if (round.voteCounts[modelHash] > maxVotes) {
                maxVotes = round.voteCounts[modelHash];
                winningModel = modelHash;
            }
        }

        // Check if consensus threshold met
        uint256 totalVotes = round.participants.length;
        if (maxVotes.mul(10000).div(totalVotes) >= CONSENSUS_THRESHOLD) {
            round.winningModel = winningModel;
            round.finalized = true;
            task.status = TaskStatus.COMPLETED;

            // Distribute rewards
            _distributeRewards(round.taskId, round.subnetId, winningModel);

            emit ConsensusReached(round.taskId, winningModel, round.reward);
        }
    }

    function _distributeRewards(
        bytes32 taskId,
        uint64 subnetId,
        bytes32 winningModel
    ) private {
        AITask storage task = subnets[subnetId].tasks[taskId];
        uint256 totalReward = task.reward;

        // Find winning miner
        address winner;
        for (uint256 i = 0; i < task.participants.length; i++) {
            address participant = task.participants[i];
            if (task.submissions[participant].modelHash == winningModel) {
                winner = participant;
                break;
            }
        }

        if (winner != address(0)) {
            // Calculate incentive for winner
            uint256 winnerReward = calculateIncentive(
                winner,
                taskId,
                subnetId,
                totalReward.mul(7000).div(10000)
            ); // 70%

            // Transfer reward
            require(
                coreToken.transfer(winner, winnerReward),
                "Winner reward transfer failed"
            );

            // Update miner stats
            miners[winner].totalRewards = miners[winner].totalRewards.add(
                winnerReward
            );
            miners[winner].tasksCompleted++;
            miners[winner].aiPerformance = _calculateAveragePerformance(winner);

            emit IncentiveDistributed(winner, winnerReward, taskId);

            // Distribute remaining rewards to validators
            uint256 validatorPool = totalReward.sub(winnerReward);
            _distributeValidatorRewards(taskId, subnetId, validatorPool);
        }
    }

    function _distributeValidatorRewards(
        bytes32 taskId,
        uint64 subnetId,
        uint256 totalPool
    ) private {
        bytes32 consensusId = keccak256(abi.encodePacked(taskId, block.number));
        ConsensusRound storage round = consensusRounds[consensusId];

        if (round.participants.length > 0) {
            uint256 rewardPerValidator = totalPool.div(
                round.participants.length
            );

            for (uint256 i = 0; i < round.participants.length; i++) {
                address validator = round.participants[i];
                uint256 validatorReward = calculateIncentive(
                    validator,
                    taskId,
                    subnetId,
                    rewardPerValidator
                );

                require(
                    coreToken.transfer(validator, validatorReward),
                    "Validator reward transfer failed"
                );

                validators[validator].totalRewards = validators[validator]
                    .totalRewards
                    .add(validatorReward);
                validators[validator].tasksValidated++;

                emit IncentiveDistributed(validator, validatorReward, taskId);
            }
        }
    }

    function _calculateAveragePerformance(
        address miner
    ) private view returns (uint256) {
        // Simplified average performance calculation
        // In production, this would use more sophisticated metrics
        return
            miners[miner].reputation.add(miners[miner].validationAccuracy).div(
                2
            );
    }

    // === VIEW FUNCTIONS ===
    function getMinerInfo(
        address minerAddr
    ) external view returns (MinerNode memory) {
        return miners[minerAddr];
    }

    function getValidatorInfo(
        address validatorAddr
    ) external view returns (ValidatorNode memory) {
        return validators[validatorAddr];
    }

    function getSubnetInfo(
        uint64 subnetId
    )
        external
        view
        returns (
            uint64 uid,
            string memory name,
            SubnetType aiType,
            address owner,
            uint256 totalStake,
            uint256 minerCount,
            uint256 validatorCount,
            uint256 rewardPool,
            uint256 taskCount,
            bool isActive
        )
    {
        AISubnet storage subnet = subnets[subnetId];
        return (
            subnet.uid,
            subnet.name,
            subnet.aiType,
            subnet.owner,
            subnet.totalStake,
            subnet.minerCount,
            subnet.validatorCount,
            subnet.rewardPool,
            subnet.taskCount,
            subnet.isActive
        );
    }

    function getTaskInfo(
        uint64 subnetId,
        bytes32 taskId
    )
        external
        view
        returns (
            bytes32 id,
            address creator,
            uint256 reward,
            uint256 deadline,
            TaskStatus status,
            uint256 participantCount
        )
    {
        AITask storage task = subnets[subnetId].tasks[taskId];
        return (
            task.taskId,
            task.creator,
            task.reward,
            task.deadline,
            task.status,
            task.participants.length
        );
    }

    function getNetworkStats()
        external
        view
        returns (
            uint256 totalMiners,
            uint256 totalValidators,
            uint256 totalSubnets,
            uint256 totalStakedCore,
            uint256 totalStakedBtc,
            uint256 totalTasks,
            uint256 totalModels
        )
    {
        return (
            allMiners.length,
            allValidators.length,
            allSubnets.length,
            totalCoreStaked,
            totalBtcStaked,
            totalTasksCreated,
            totalModelsValidated
        );
    }

    // === GOVERNANCE FUNCTIONS ===
    function updateConsensusParameters(
        uint256 newConsensusThreshold,
        uint256 newMinValidators,
        uint256 newIncentiveDecay
    ) external onlyRole(GOVERNANCE_ROLE) {
        // Update consensus parameters through governance
        // Implementation would include parameter validation and time-delayed execution
    }

    function pauseSubnet(uint64 subnetId) external onlyRole(GOVERNANCE_ROLE) {
        subnets[subnetId].isActive = false;
    }

    function unpauseSubnet(uint64 subnetId) external onlyRole(GOVERNANCE_ROLE) {
        subnets[subnetId].isActive = true;
    }

    // === EMERGENCY FUNCTIONS ===
    function emergencyPause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        // Emergency pause implementation
    }
}
