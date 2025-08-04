// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/**
 * @title ModernTensorAI v2.0 - Improved
 * @dev Enhanced ModernTensor contract aligned with metagraph expectations
 * Features Bittensor-style UID indexing and improved data structures
 */
contract ModernTensorAI_v2_Improved is Ownable, ReentrancyGuard, Pausable {
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
    
    // ===== Improved Data Structures (Aligned with Metagraph) =====
    
    /**
     * @dev MinerData struct aligned with metagraph_datum.py
     * This matches the expected structure for seamless integration
     */
    struct MinerData {
        bytes32 uid;                        // hexadecimal string -> bytes32
        uint64 subnet_uid;                  // subnet identifier
        uint256 stake;                      // CORE tokens staked
        uint256 bitcoin_stake;              // Bitcoin staked amount (satoshis)
        uint64 scaled_last_performance;     // Performance score x SCALE_FACTOR
        uint64 scaled_trust_score;          // Trust score x SCALE_FACTOR
        uint256 accumulated_rewards;        // Total rewards earned
        uint64 last_update_time;            // Last update timestamp
        bytes32 performance_history_hash;   // Performance history hash
        bytes32 wallet_addr_hash;           // Wallet address hash
        uint8 status;                       // 0: Inactive, 1: Active, 2: Jailed
        uint64 registration_time;           // Registration timestamp
        string api_endpoint;                // API endpoint for miner
        address owner;                      // Owner address
    }
    
    /**
     * @dev ValidatorData struct aligned with metagraph_datum.py
     */
    struct ValidatorData {
        bytes32 uid;                        // hexadecimal string -> bytes32
        uint64 subnet_uid;                  // subnet identifier
        uint256 stake;                      // CORE tokens staked
        uint256 bitcoin_stake;              // Bitcoin staked amount (satoshis)
        uint64 scaled_last_performance;     // Performance score x SCALE_FACTOR
        uint64 scaled_trust_score;          // Trust score x SCALE_FACTOR
        uint256 accumulated_rewards;        // Total rewards earned
        uint64 last_update_time;            // Last update timestamp
        bytes32 performance_history_hash;   // Performance history hash
        bytes32 wallet_addr_hash;           // Wallet address hash
        uint8 status;                       // 0: Inactive, 1: Active, 2: Jailed
        uint64 registration_time;           // Registration timestamp
        string api_endpoint;                // API endpoint for validator
        address owner;                      // Owner address
    }
    
    /**
     * @dev SubnetStaticData struct aligned with metagraph_datum.py
     */
    struct SubnetStaticData {
        uint64 net_uid;                     // Network/subnet UID
        string name;                        // Subnet name
        string description;                 // Subnet description
        address owner_addr;                 // Subnet owner
        uint256 max_miners;                 // Maximum miners allowed
        uint256 max_validators;             // Maximum validators allowed
        uint256 immunity_period;            // Immunity period for new participants
        uint64 creation_time;               // Creation timestamp
        uint256 min_stake_miner;            // Minimum stake for miners
        uint256 min_stake_validator;        // Minimum stake for validators
        uint32 version;                     // Subnet version
    }
    
    /**
     * @dev SubnetDynamicData struct aligned with metagraph_datum.py
     */
    struct SubnetDynamicData {
        uint64 net_uid;                     // Network/subnet UID
        uint64 scaled_weight;               // Subnet weight x SCALE_FACTOR
        uint64 scaled_performance;          // Subnet performance x SCALE_FACTOR
        uint256 current_epoch;              // Current epoch number
        uint8 registration_open;            // Registration status (0/1)
        uint256 reg_cost;                   // Registration cost
        uint64 scaled_incentive_ratio;      // Incentive ratio x SCALE_FACTOR
        uint64 last_update_time;            // Last update timestamp
        uint256 total_stake;                // Total staked in subnet
        uint256 validator_count;            // Current validator count
        uint256 miner_count;                // Current miner count
    }

    // ===== Bittensor-Style UID Management =====
    
    // UID-based indexing for miners and validators
    mapping(uint256 => MinerData) public miners;           // uid -> MinerData
    mapping(uint256 => ValidatorData) public validators;   // uid -> ValidatorData
    mapping(uint256 => SubnetStaticData) public subnets;   // subnet_id -> SubnetStaticData
    mapping(uint256 => SubnetDynamicData) public subnetDynamics; // subnet_id -> SubnetDynamicData
    
    // Address to UID mappings for reverse lookup
    mapping(address => uint256) public minerAddressToUid;
    mapping(address => uint256) public validatorAddressToUid;
    
    // UID counters for automatic assignment
    uint256 public nextMinerUid = 0;
    uint256 public nextValidatorUid = 0;
    uint256 public nextSubnetUid = 0;
    
    // Active UIDs tracking
    uint256[] public activeMinerUids;
    uint256[] public activeValidatorUids;
    uint256[] public activeSubnetUids;
    
    // ===== Bitcoin Staking Integration =====
    mapping(address => bytes32) public bitcoinTxHashes;
    mapping(bytes32 => uint256) public bitcoinStakeAmounts;
    mapping(bytes32 => uint256) public bitcoinLockTimes;
    
    // ===== Events =====
    event MinerRegistered(address indexed owner, uint256 indexed uid, uint64 subnet_uid, uint256 stake, uint256 bitcoin_stake, string api_endpoint);
    event ValidatorRegistered(address indexed owner, uint256 indexed uid, uint64 subnet_uid, uint256 stake, uint256 bitcoin_stake, string api_endpoint);
    event SubnetCreated(uint256 indexed subnet_uid, string name, address indexed owner);
    event StakesUpdated(address indexed user, uint256 core_stake, uint256 bitcoin_stake);
    event PerformanceUpdated(uint256 indexed uid, uint8 entity_type, uint64 scaled_performance, uint64 scaled_trust_score);
    event BitcoinStaked(address indexed user, bytes32 indexed tx_hash, uint256 amount, uint256 lock_time);
    
    // ===== Constructor =====
    constructor(address _coreToken) {
        coreToken = IERC20(_coreToken);
    }
    
    // ===== Miner Registration (Bittensor-style) =====
    function registerMiner(
        uint64 subnet_uid,
        uint256 stake_amount,
        string calldata api_endpoint
    ) external nonReentrant whenNotPaused returns (uint256 uid) {
        require(stake_amount >= MIN_STAKE, "Insufficient stake");
        require(minerAddressToUid[msg.sender] == 0, "Already registered");
        
        // Transfer stake
        coreToken.safeTransferFrom(msg.sender, address(this), stake_amount);
        
        // Assign new UID
        uid = nextMinerUid++;
        
        // Create miner data
        miners[uid] = MinerData({
            uid: bytes32(uid),
            subnet_uid: subnet_uid,
            stake: stake_amount,
            bitcoin_stake: 0,
            scaled_last_performance: 0,
            scaled_trust_score: uint64(SCALE_FACTOR), // Start with 1.0 trust
            accumulated_rewards: 0,
            last_update_time: uint64(block.timestamp),
            performance_history_hash: keccak256(abi.encodePacked(uid, block.timestamp)),
            wallet_addr_hash: keccak256(abi.encodePacked(msg.sender)),
            status: STATUS_ACTIVE,
            registration_time: uint64(block.timestamp),
            api_endpoint: api_endpoint,
            owner: msg.sender
        });
        
        // Update mappings
        minerAddressToUid[msg.sender] = uid;
        activeMinerUids.push(uid);
        
        emit MinerRegistered(msg.sender, uid, subnet_uid, stake_amount, 0, api_endpoint);
        return uid;
    }
    
    // ===== Validator Registration (Bittensor-style) =====
    function registerValidator(
        uint64 subnet_uid,
        uint256 stake_amount,
        string calldata api_endpoint
    ) external nonReentrant whenNotPaused returns (uint256 uid) {
        require(stake_amount >= MIN_STAKE * 10, "Insufficient validator stake"); // Higher minimum for validators
        require(validatorAddressToUid[msg.sender] == 0, "Already registered");
        
        // Transfer stake
        coreToken.safeTransferFrom(msg.sender, address(this), stake_amount);
        
        // Assign new UID
        uid = nextValidatorUid++;
        
        // Create validator data
        validators[uid] = ValidatorData({
            uid: bytes32(uid),
            subnet_uid: subnet_uid,
            stake: stake_amount,
            bitcoin_stake: 0,
            scaled_last_performance: 0,
            scaled_trust_score: uint64(SCALE_FACTOR), // Start with 1.0 trust
            accumulated_rewards: 0,
            last_update_time: uint64(block.timestamp),
            performance_history_hash: keccak256(abi.encodePacked(uid, block.timestamp)),
            wallet_addr_hash: keccak256(abi.encodePacked(msg.sender)),
            status: STATUS_ACTIVE,
            registration_time: uint64(block.timestamp),
            api_endpoint: api_endpoint,
            owner: msg.sender
        });
        
        // Update mappings
        validatorAddressToUid[msg.sender] = uid;
        activeValidatorUids.push(uid);
        
        emit ValidatorRegistered(msg.sender, uid, subnet_uid, stake_amount, 0, api_endpoint);
        return uid;
    }
    
    // ===== Performance Updates (Bittensor-style Consensus) =====
    function updateMinerPerformance(
        uint256 miner_uid,
        uint64 scaled_performance,
        uint64 scaled_trust_score
    ) external {
        require(validatorAddressToUid[msg.sender] != 0, "Only validators can update");
        require(miners[miner_uid].status == STATUS_ACTIVE, "Miner not active");
        require(scaled_performance <= MAX_PERFORMANCE, "Invalid performance");
        require(scaled_trust_score <= SCALE_FACTOR, "Invalid trust score");
        
        miners[miner_uid].scaled_last_performance = scaled_performance;
        miners[miner_uid].scaled_trust_score = scaled_trust_score;
        miners[miner_uid].last_update_time = uint64(block.timestamp);
        
        emit PerformanceUpdated(miner_uid, 0, scaled_performance, scaled_trust_score); // 0 = miner
    }
    
    function updateValidatorPerformance(
        uint256 validator_uid,
        uint64 scaled_performance,
        uint64 scaled_trust_score
    ) external onlyOwner {
        require(validators[validator_uid].status == STATUS_ACTIVE, "Validator not active");
        require(scaled_performance <= MAX_PERFORMANCE, "Invalid performance");
        require(scaled_trust_score <= SCALE_FACTOR, "Invalid trust score");
        
        validators[validator_uid].scaled_last_performance = scaled_performance;
        validators[validator_uid].scaled_trust_score = scaled_trust_score;
        validators[validator_uid].last_update_time = uint64(block.timestamp);
        
        emit PerformanceUpdated(validator_uid, 1, scaled_performance, scaled_trust_score); // 1 = validator
    }
    
    // ===== Bitcoin Staking Integration =====
    function stakeBitcoin(
        bytes32 tx_hash,
        uint256 amount,
        uint256 lock_time
    ) external {
        uint256 miner_uid = minerAddressToUid[msg.sender];
        uint256 validator_uid = validatorAddressToUid[msg.sender];
        
        require(miner_uid != 0 || validator_uid != 0, "Not registered");
        require(bitcoinStakeAmounts[tx_hash] == 0, "Bitcoin already staked");
        require(lock_time > block.timestamp, "Invalid lock time");
        
        bitcoinTxHashes[msg.sender] = tx_hash;
        bitcoinStakeAmounts[tx_hash] = amount;
        bitcoinLockTimes[tx_hash] = lock_time;
        
        // Update stake amounts
        if (miner_uid != 0) {
            miners[miner_uid].bitcoin_stake = amount;
        }
        if (validator_uid != 0) {
            validators[validator_uid].bitcoin_stake = amount;
        }
        
        emit BitcoinStaked(msg.sender, tx_hash, amount, lock_time);
    }
    
    // ===== View Functions =====
    function getMinerData(uint256 uid) external view returns (MinerData memory) {
        return miners[uid];
    }
    
    function getValidatorData(uint256 uid) external view returns (ValidatorData memory) {
        return validators[uid];
    }
    
    function getActiveMinerUids() external view returns (uint256[] memory) {
        return activeMinerUids;
    }
    
    function getActiveValidatorUids() external view returns (uint256[] memory) {
        return activeValidatorUids;
    }
    
    function calculateStakingTier(address user) external view returns (uint256) {
        uint256 core_stake = 0;
        uint256 bitcoin_stake = 0;
        
        uint256 miner_uid = minerAddressToUid[user];
        uint256 validator_uid = validatorAddressToUid[user];
        
        if (miner_uid != 0) {
            core_stake = miners[miner_uid].stake;
            bitcoin_stake = miners[miner_uid].bitcoin_stake;
        } else if (validator_uid != 0) {
            core_stake = validators[validator_uid].stake;
            bitcoin_stake = validators[validator_uid].bitcoin_stake;
        }
        
        if (bitcoin_stake == 0) return 0; // Base tier
        
        uint256 ratio = (core_stake * 1000) / bitcoin_stake; // Scale by 1000 for precision
        
        // Tier calculation logic
        if (ratio >= 1000) return 3; // Satoshi tier (1:1 ratio)
        if (ratio >= 500) return 2;  // Super tier (1:2 ratio)
        if (ratio >= 100) return 1;  // Boost tier (1:10 ratio)
        return 0; // Base tier
    }
    
    // ===== Admin Functions =====
    function pause() external onlyOwner {
        _pause();
    }
    
    function unpause() external onlyOwner {
        _unpause();
    }
    
    function setCoreToken(address _coreToken) external onlyOwner {
        coreToken = IERC20(_coreToken);
    }
}