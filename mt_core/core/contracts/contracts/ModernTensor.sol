// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/**
 * @title ModernTensor
 * @dev Main contract for ModernTensor AI training network on Core blockchain
 * Features Bitcoin staking integration and dual staking rewards
 */
contract ModernTensor is Ownable, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    // ===== Constants =====
    uint8 public constant STATUS_INACTIVE = 0;
    uint8 public constant STATUS_ACTIVE = 1;
    uint8 public constant STATUS_JAILED = 2;
    
    uint256 public constant SCALE_FACTOR = 1000000; // For performance/trust scores
    uint256 public constant MIN_STAKE = 1e18; // 1 CORE token minimum
    uint256 public constant MAX_PERFORMANCE = 1000000; // 1.0 scaled
    
    // Core blockchain integration
    IERC20 public coreToken; // CORE token contract
    
    // ===== Structs =====
    
    struct MinerInfo {
        bytes32 uid;
        uint64 subnetUid;
        uint256 stake;
        uint256 bitcoinStake; // Bitcoin staked amount
        uint256 lastPerformance;
        uint256 trustScore;
        uint256 accumulatedRewards;
        uint256 lastUpdateTimestamp;
        uint256 registrationTimestamp;
        uint8 status;
        bytes32 performanceHistoryHash;
        string apiEndpoint;
        address owner;
    }
    
    struct ValidatorInfo {
        bytes32 uid;
        uint64 subnetUid;
        uint256 stake;
        uint256 bitcoinStake;
        uint256 lastPerformance;
        uint256 trustScore;
        uint256 accumulatedRewards;
        uint256 lastUpdateTimestamp;
        uint256 registrationTimestamp;
        uint8 status;
        bytes32 performanceHistoryHash;
        string apiEndpoint;
        address owner;
    }
    
    struct SubnetInfo {
        uint64 uid;
        string name;
        string description;
        uint256 maxMiners;
        uint256 maxValidators;
        uint256 immunityPeriod;
        uint256 minMinerStake;
        uint256 minValidatorStake;
        uint256 registrationCost;
        address owner;
        uint256 creationTimestamp;
    }
    
    struct StakingTier {
        uint256 minCoreRatio; // Minimum CORE to Bitcoin ratio
        uint256 multiplier; // Reward multiplier (scaled by 1000)
        string name;
    }
    
    // ===== Storage =====
    
    // Registries
    mapping(address => MinerInfo) public miners;
    mapping(address => ValidatorInfo) public validators;
    mapping(uint64 => SubnetInfo) public subnets;
    
    // Address arrays for enumeration
    address[] public minerAddresses;
    address[] public validatorAddresses;
    uint64[] public subnetIds;
    
    // Staking tiers for dual staking
    StakingTier[] public stakingTiers;
    
    // Bitcoin staking tracking
    mapping(address => bytes32) public bitcoinTxHashes; // Bitcoin transaction hashes
    mapping(bytes32 => uint256) public bitcoinStakeAmounts;
    mapping(bytes32 => uint256) public bitcoinLockTimes;
    
    // Counters
    uint256 public totalMiners;
    uint256 public totalValidators;
    uint64 public totalSubnets;
    
    // ===== Events =====
    
    event MinerRegistered(
        address indexed miner,
        bytes32 indexed uid,
        uint64 indexed subnetUid,
        uint256 stake,
        uint256 bitcoinStake,
        string apiEndpoint
    );
    
    event ValidatorRegistered(
        address indexed validator,
        bytes32 indexed uid,
        uint64 indexed subnetUid,
        uint256 stake,
        uint256 bitcoinStake,
        string apiEndpoint
    );
    
    event SubnetCreated(
        uint64 indexed uid,
        string name,
        address indexed owner
    );
    
    event MinerScoreUpdated(
        address indexed miner,
        bytes32 indexed uid,
        uint256 newPerformance,
        uint256 newTrustScore
    );
    
    event ValidatorScoreUpdated(
        address indexed validator,
        bytes32 indexed uid,
        uint256 newPerformance,
        uint256 newTrustScore
    );
    
    event BitcoinStaked(
        address indexed user,
        bytes32 indexed txHash,
        uint256 amount,
        uint256 lockTime
    );
    
    event RewardsDistributed(
        address indexed user,
        uint256 amount,
        uint256 tier
    );
    
    // ===== Constructor =====
    
    constructor(address _coreToken) {
        coreToken = IERC20(_coreToken);
        
        // Initialize staking tiers
        stakingTiers.push(StakingTier(0, 1000, "Base")); // 1x multiplier
        stakingTiers.push(StakingTier(100, 1250, "Boost")); // 1.25x multiplier
        stakingTiers.push(StakingTier(500, 1500, "Super")); // 1.5x multiplier
        stakingTiers.push(StakingTier(1000, 2000, "Satoshi")); // 2x multiplier
    }
    
    // ===== Modifiers =====
    
    modifier onlyValidator() {
        require(validators[msg.sender].status == STATUS_ACTIVE, "Not an active validator");
        _;
    }
    
    modifier validSubnet(uint64 subnetUid) {
        require(subnets[subnetUid].uid == subnetUid, "Invalid subnet");
        _;
    }
    
    // ===== Subnet Management =====
    
    function createSubnet(
        uint64 uid,
        string calldata name,
        string calldata description,
        uint256 maxMiners,
        uint256 maxValidators,
        uint256 immunityPeriod,
        uint256 minMinerStake,
        uint256 minValidatorStake,
        uint256 registrationCost
    ) external onlyOwner {
        require(subnets[uid].uid == 0, "Subnet already exists");
        
        subnets[uid] = SubnetInfo({
            uid: uid,
            name: name,
            description: description,
            maxMiners: maxMiners,
            maxValidators: maxValidators,
            immunityPeriod: immunityPeriod,
            minMinerStake: minMinerStake,
            minValidatorStake: minValidatorStake,
            registrationCost: registrationCost,
            owner: msg.sender,
            creationTimestamp: block.timestamp
        });
        
        subnetIds.push(uid);
        totalSubnets++;
        
        emit SubnetCreated(uid, name, msg.sender);
    }
    
    // ===== Miner Management =====
    
    function registerMiner(
        bytes32 uid,
        uint64 subnetUid,
        uint256 stakeAmount,
        string calldata apiEndpoint
    ) external payable nonReentrant validSubnet(subnetUid) {
        require(miners[msg.sender].uid == bytes32(0), "Miner already registered");
        require(stakeAmount >= subnets[subnetUid].minMinerStake, "Insufficient stake");
        require(bytes(apiEndpoint).length > 0, "Invalid API endpoint");
        
        // Transfer CORE tokens
        coreToken.safeTransferFrom(msg.sender, address(this), stakeAmount);
        
        miners[msg.sender] = MinerInfo({
            uid: uid,
            subnetUid: subnetUid,
            stake: stakeAmount,
            bitcoinStake: 0,
            lastPerformance: 500000, // Default 0.5
            trustScore: 500000, // Default 0.5
            accumulatedRewards: 0,
            lastUpdateTimestamp: block.timestamp,
            registrationTimestamp: block.timestamp,
            status: STATUS_ACTIVE,
            performanceHistoryHash: bytes32(0),
            apiEndpoint: apiEndpoint,
            owner: msg.sender
        });
        
        minerAddresses.push(msg.sender);
        totalMiners++;
        
        emit MinerRegistered(msg.sender, uid, subnetUid, stakeAmount, 0, apiEndpoint);
    }
    
    function registerValidator(
        bytes32 uid,
        uint64 subnetUid,
        uint256 stakeAmount,
        string calldata apiEndpoint
    ) external payable nonReentrant validSubnet(subnetUid) {
        require(validators[msg.sender].uid == bytes32(0), "Validator already registered");
        require(stakeAmount >= subnets[subnetUid].minValidatorStake, "Insufficient stake");
        require(bytes(apiEndpoint).length > 0, "Invalid API endpoint");
        
        // Transfer CORE tokens
        coreToken.safeTransferFrom(msg.sender, address(this), stakeAmount);
        
        validators[msg.sender] = ValidatorInfo({
            uid: uid,
            subnetUid: subnetUid,
            stake: stakeAmount,
            bitcoinStake: 0,
            lastPerformance: 500000, // Default 0.5
            trustScore: 500000, // Default 0.5
            accumulatedRewards: 0,
            lastUpdateTimestamp: block.timestamp,
            registrationTimestamp: block.timestamp,
            status: STATUS_ACTIVE,
            performanceHistoryHash: bytes32(0),
            apiEndpoint: apiEndpoint,
            owner: msg.sender
        });
        
        validatorAddresses.push(msg.sender);
        totalValidators++;
        
        emit ValidatorRegistered(msg.sender, uid, subnetUid, stakeAmount, 0, apiEndpoint);
    }
    
    // ===== Bitcoin Staking Integration =====
    
    function stakeBitcoin(
        bytes32 txHash,
        uint256 amount,
        uint256 lockTime
    ) external {
        require(miners[msg.sender].uid != bytes32(0) || validators[msg.sender].uid != bytes32(0), "Not registered");
        require(bitcoinStakeAmounts[txHash] == 0, "Bitcoin already staked");
        require(lockTime > block.timestamp, "Invalid lock time");
        
        bitcoinTxHashes[msg.sender] = txHash;
        bitcoinStakeAmounts[txHash] = amount;
        bitcoinLockTimes[txHash] = lockTime;
        
        // Update stake amounts
        if (miners[msg.sender].uid != bytes32(0)) {
            miners[msg.sender].bitcoinStake = amount;
        }
        if (validators[msg.sender].uid != bytes32(0)) {
            validators[msg.sender].bitcoinStake = amount;
        }
        
        emit BitcoinStaked(msg.sender, txHash, amount, lockTime);
    }
    
    // ===== Dual Staking Rewards =====
    
    function calculateStakingTier(address user) public view returns (uint256) {
        uint256 coreStake = 0;
        uint256 bitcoinStake = 0;
        
        if (miners[user].uid != bytes32(0)) {
            coreStake = miners[user].stake;
            bitcoinStake = miners[user].bitcoinStake;
        } else if (validators[user].uid != bytes32(0)) {
            coreStake = validators[user].stake;
            bitcoinStake = validators[user].bitcoinStake;
        }
        
        if (bitcoinStake == 0) return 0; // Base tier
        
        uint256 ratio = (coreStake * 1000) / bitcoinStake; // Scale by 1000 for precision
        
        for (uint256 i = stakingTiers.length - 1; i > 0; i--) {
            if (ratio >= stakingTiers[i].minCoreRatio) {
                return i;
            }
        }
        
        return 0; // Base tier
    }
    
    function distributeRewards(address user, uint256 baseReward) external onlyValidator {
        uint256 tier = calculateStakingTier(user);
        uint256 multiplier = stakingTiers[tier].multiplier;
        uint256 finalReward = (baseReward * multiplier) / 1000;
        
        // Update accumulated rewards
        if (miners[user].uid != bytes32(0)) {
            miners[user].accumulatedRewards += finalReward;
        } else if (validators[user].uid != bytes32(0)) {
            validators[user].accumulatedRewards += finalReward;
        }
        
        emit RewardsDistributed(user, finalReward, tier);
    }
    
    // ===== Score Updates =====
    
    function updateMinerScores(
        address minerAddr,
        uint256 newPerformance,
        uint256 newTrustScore
    ) external onlyValidator {
        require(miners[minerAddr].uid != bytes32(0), "Miner not found");
        require(newPerformance <= MAX_PERFORMANCE, "Invalid performance");
        require(newTrustScore <= MAX_PERFORMANCE, "Invalid trust score");
        
        miners[minerAddr].lastPerformance = newPerformance;
        miners[minerAddr].trustScore = newTrustScore;
        miners[minerAddr].lastUpdateTimestamp = block.timestamp;
        
        emit MinerScoreUpdated(minerAddr, miners[minerAddr].uid, newPerformance, newTrustScore);
    }
    
    function updateValidatorScores(
        address validatorAddr,
        uint256 newPerformance,
        uint256 newTrustScore
    ) external onlyValidator {
        require(validators[validatorAddr].uid != bytes32(0), "Validator not found");
        require(newPerformance <= MAX_PERFORMANCE, "Invalid performance");
        require(newTrustScore <= MAX_PERFORMANCE, "Invalid trust score");
        
        validators[validatorAddr].lastPerformance = newPerformance;
        validators[validatorAddr].trustScore = newTrustScore;
        validators[validatorAddr].lastUpdateTimestamp = block.timestamp;
        
        emit ValidatorScoreUpdated(validatorAddr, validators[validatorAddr].uid, newPerformance, newTrustScore);
    }
    
    // ===== Status Management =====
    
    function setMinerStatus(address minerAddr, uint8 newStatus) external onlyOwner {
        require(miners[minerAddr].uid != bytes32(0), "Miner not found");
        require(newStatus <= STATUS_JAILED, "Invalid status");
        
        miners[minerAddr].status = newStatus;
        miners[minerAddr].lastUpdateTimestamp = block.timestamp;
    }
    
    function setValidatorStatus(address validatorAddr, uint8 newStatus) external onlyOwner {
        require(validators[validatorAddr].uid != bytes32(0), "Validator not found");
        require(newStatus <= STATUS_JAILED, "Invalid status");
        
        validators[validatorAddr].status = newStatus;
        validators[validatorAddr].lastUpdateTimestamp = block.timestamp;
    }
    
    // ===== View Functions =====
    
    function getMinerInfo(address minerAddr) external view returns (MinerInfo memory) {
        return miners[minerAddr];
    }
    
    function getValidatorInfo(address validatorAddr) external view returns (ValidatorInfo memory) {
        return validators[validatorAddr];
    }
    
    function getSubnetInfo(uint64 subnetUid) external view returns (SubnetInfo memory) {
        return subnets[subnetUid];
    }
    
    function getAllMiners() external view returns (address[] memory) {
        return minerAddresses;
    }
    
    function getAllValidators() external view returns (address[] memory) {
        return validatorAddresses;
    }
    
    function getAllSubnets() external view returns (uint64[] memory) {
        return subnetIds;
    }
    
    function getStakingTiers() external view returns (StakingTier[] memory) {
        return stakingTiers;
    }
    
    // ===== Emergency Functions =====
    
    function pause() external onlyOwner {
        _pause();
    }
    
    function unpause() external onlyOwner {
        _unpause();
    }
    
    function emergencyWithdraw(address token, uint256 amount) external onlyOwner {
        IERC20(token).safeTransfer(owner(), amount);
    }
} 