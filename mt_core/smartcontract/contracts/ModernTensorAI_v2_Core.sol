// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "./libraries/BitcoinSPV.sol";
import "./libraries/AIModelValidator.sol";

/**
 * @title ModernTensorAI_v2_Core
 * @dev ModernTensor decentralized AI training on Core DAO
 * Features: UID-based indexing, trust scores, consensus mechanisms, incentive distribution
 */
contract ModernTensorAI_v2_Core is ReentrancyGuard, AccessControl {
    using BitcoinSPV for BitcoinSPV.BitcoinTransaction;
    using AIModelValidator for AIModelValidator.ModelMetrics;

    // ============ CONSTANTS (ModernTensor-style) ============
    
    uint256 public constant DIVISOR = 1_000_000; // From metagraph_datum.py
    uint64 public constant DIVISOR_64 = 1_000_000; // For uint64 fields
    uint64 public constant MAX_SUBNET_UID = type(uint64).max;
    uint32 public constant IMMUNITY_PERIOD = 7200; // 2 hours (ModernTensor default)
    uint16 public constant MAX_REPUTATION = 65535;
    
    // Status constants matching metagraph_datum.py
    uint8 public constant STATUS_INACTIVE = 0;
    uint8 public constant STATUS_ACTIVE = 1;
    uint8 public constant STATUS_JAILED = 2;

    // ============ DATA STRUCTURES (Aligned with metagraph_datum.py) ============

    /**
     * @dev MinerData struct matching metagraph_datum.py exactly
     */
    struct MinerData {
        bytes32 uid;                        // hexadecimal string as bytes32
        uint64 subnet_uid;                  // subnet identifier
        uint256 stake;                      // total stake amount
        uint64 scaled_last_performance;     // performance * DIVISOR
        uint64 scaled_trust_score;          // trust score * DIVISOR
        uint256 accumulated_rewards;        // total rewards earned
        uint64 last_update_time;           // timestamp of last update
        bytes32 performance_history_hash;   // hash of performance history
        bytes32 wallet_addr_hash;          // hash of wallet address
        uint8 status;                      // 0: Inactive, 1: Active, 2: Jailed
        uint64 registration_time;          // when miner was registered
        string api_endpoint;               // miner's API endpoint
    }

    /**
     * @dev ValidatorData struct matching metagraph_datum.py exactly
     */
    struct ValidatorData {
        bytes32 uid;
        uint64 subnet_uid;
        uint256 stake;
        uint64 scaled_last_performance;
        uint64 scaled_trust_score;
        uint256 accumulated_rewards;
        uint64 last_update_time;
        bytes32 performance_history_hash;
        bytes32 wallet_addr_hash;
        uint8 status;
        uint64 registration_time;
        string api_endpoint;
    }

    /**
     * @dev SubnetStaticData struct for subnet metadata
     */
    struct SubnetStaticData {
        uint64 net_uid;
        string name;
        address owner_addr;
        uint32 max_miners;
        uint32 max_validators;
        uint64 immunity_period;
        uint64 creation_time;
        string description;
        uint32 version;
        uint256 min_stake_miner;
        uint256 min_stake_validator;
    }

    /**
     * @dev SubnetDynamicData struct for changing subnet state
     */
    struct SubnetDynamicData {
        uint64 net_uid;
        uint64 scaled_weight;          // weight * DIVISOR
        uint64 scaled_performance;     // performance * DIVISOR
        uint64 current_epoch;
        uint8 registration_open;       // 0 or 1
        uint256 reg_cost;
        uint64 scaled_incentive_ratio; // incentive ratio * DIVISOR
        uint64 last_update_time;
        uint256 total_stake;
        uint32 validator_count;
        uint32 miner_count;
    }

    // ============ STATE VARIABLES ============

    // Core tokens
    IERC20 public immutable coreToken;
    IERC20 public immutable btcToken;

    // Role definitions
    bytes32 public constant VALIDATOR_ROLE = keccak256("VALIDATOR_ROLE");
    bytes32 public constant SUBNET_OWNER_ROLE = keccak256("SUBNET_OWNER_ROLE");
    bytes32 public constant GOVERNANCE_ROLE = keccak256("GOVERNANCE_ROLE");

    // Network state
    uint64 public nextSubnetId = 1;
    uint64 public currentEpoch = 0;
    uint256 public totalNetworkStake = 0;

    // Mappings for network data
    mapping(address => MinerData) public miners;          // address -> MinerData
    mapping(address => ValidatorData) public validators;  // address -> ValidatorData
    mapping(uint64 => SubnetStaticData) public subnetStatic;   // subnet_uid -> static data
    mapping(uint64 => SubnetDynamicData) public subnetDynamic; // subnet_uid -> dynamic data
    
    // ModernTensor-style UID mappings
    mapping(uint64 => address[]) public subnetMiners;     // subnet_uid -> miner addresses
    mapping(uint64 => address[]) public subnetValidators; // subnet_uid -> validator addresses
    mapping(address => uint64) public minerToSubnet;      // miner address -> subnet_uid
    mapping(address => uint64) public validatorToSubnet;  // validator address -> subnet_uid

    // Trust and consensus data
    mapping(uint64 => mapping(address => uint64)) public trustScores;    // subnet -> miner -> trust
    mapping(uint64 => mapping(address => uint64)) public incentiveWeights; // subnet -> miner -> weight
    mapping(uint64 => uint256) public emissionRates;     // subnet -> emission rate

    // ============ EVENTS ============

    event SubnetCreated(uint64 indexed subnetId, string name, address owner);
    event MinerRegistered(address indexed miner, uint64 indexed subnetId, bytes32 uid);
    event ValidatorRegistered(address indexed validator, uint64 indexed subnetId, bytes32 uid);
    event TrustScoreUpdated(uint64 indexed subnetId, address indexed miner, uint64 newScore);
    event ConsensusReached(uint64 indexed subnetId, uint64 epoch, bytes32 consensusHash);
    event IncentiveDistributed(uint64 indexed subnetId, address indexed recipient, uint256 amount);
    
    // Score update events for validators
    event MinerScoreUpdated(
        address indexed miner,
        bytes32 indexed uid,
        uint64 newPerformance,
        uint64 newTrustScore
    );
    
    event ValidatorScoreUpdated(
        address indexed validator,
        bytes32 indexed uid,
        uint64 newPerformance,
        uint64 newTrustScore
    );

    // ============ CONSTRUCTOR ============

    constructor(
        address _coreToken,
        address _btcToken,
        uint256 _minMinerStake,
        uint256 _minValidatorStake
    ) {
        coreToken = IERC20(_coreToken);
        btcToken = IERC20(_btcToken);
        
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(GOVERNANCE_ROLE, msg.sender);

        // Create default subnet (subnet 0)
        _createSubnet("Default", msg.sender, _minMinerStake, _minValidatorStake);
    }

        // ============ MODERNTENSOR-INSPIRED FUNCTIONS ============
    
    /**
     * @dev Create a new subnet (like ModernTensor's register_subnet)
     */
    function createSubnet(
        string memory name,
        string memory description,
        uint32 maxMiners,
        uint32 maxValidators,
        uint256 minStakeMiner,
        uint256 minStakeValidator
    ) external returns (uint64 subnetId) {
        require(bytes(name).length > 0, "Name required");
        
        subnetId = nextSubnetId++;
        
        subnetStatic[subnetId] = SubnetStaticData({
            net_uid: subnetId,
            name: name,
            owner_addr: msg.sender,
            max_miners: maxMiners,
            max_validators: maxValidators,
            immunity_period: IMMUNITY_PERIOD,
            creation_time: uint64(block.timestamp),
            description: description,
            version: 1,
            min_stake_miner: minStakeMiner,
            min_stake_validator: minStakeValidator
        });

        subnetDynamic[subnetId] = SubnetDynamicData({
            net_uid: subnetId,
            scaled_weight: DIVISOR_64, // 100% weight initially
            scaled_performance: 0,
            current_epoch: 0,
            registration_open: 1,
            reg_cost: 0,
            scaled_incentive_ratio: DIVISOR_64,
            last_update_time: uint64(block.timestamp),
            total_stake: 0,
            validator_count: 0,
            miner_count: 0
        });

        _grantRole(SUBNET_OWNER_ROLE, msg.sender);
        emit SubnetCreated(subnetId, name, msg.sender);
    }

    /**
     * @dev Register as miner (ModernTensor-style with UID generation)
     */
    function registerMiner(
        uint64 subnetId,
        uint256 coreStake,
        uint256 btcStake,
        string memory apiEndpoint
    ) external nonReentrant {
        require(subnetStatic[subnetId].net_uid != 0, "Subnet not found");
        require(subnetDynamic[subnetId].registration_open == 1, "Registration closed");
        require(coreStake >= subnetStatic[subnetId].min_stake_miner, "Insufficient CORE stake");
        require(miners[msg.sender].uid == bytes32(0), "Already registered");

        // Generate UID like ModernTensor
        bytes32 uid = keccak256(abi.encodePacked(
            msg.sender,
            subnetId,
            block.timestamp,
            block.number
        ));

        // Transfer stakes
        if (coreStake > 0) {
            coreToken.transferFrom(msg.sender, address(this), coreStake);
        }
        if (btcStake > 0) {
            btcToken.transferFrom(msg.sender, address(this), btcStake);
        }

        // Create miner data
        miners[msg.sender] = MinerData({
            uid: uid,
            subnet_uid: subnetId,
            stake: coreStake + btcStake,
            scaled_last_performance: 0,
            scaled_trust_score: DIVISOR_64 / 2, // 50% initial trust
            accumulated_rewards: 0,
            last_update_time: uint64(block.timestamp),
            performance_history_hash: bytes32(0),
            wallet_addr_hash: keccak256(abi.encodePacked(msg.sender)),
            status: STATUS_ACTIVE,
            registration_time: uint64(block.timestamp),
            api_endpoint: apiEndpoint
        });

        // Update subnet state
        subnetMiners[subnetId].push(msg.sender);
        minerToSubnet[msg.sender] = subnetId;
        subnetDynamic[subnetId].miner_count++;
        subnetDynamic[subnetId].total_stake += coreStake + btcStake;

        emit MinerRegistered(msg.sender, subnetId, uid);
    }

    /**
     * @dev Register as validator (ModernTensor-style)
     */
    function registerValidator(
        uint64 subnetId,
        uint256 coreStake,
        uint256 btcStake,
        string memory apiEndpoint
    ) external nonReentrant {
        require(subnetStatic[subnetId].net_uid != 0, "Subnet not found");
        require(subnetDynamic[subnetId].registration_open == 1, "Registration closed");
        require(coreStake >= subnetStatic[subnetId].min_stake_validator, "Insufficient CORE stake");
        require(validators[msg.sender].uid == bytes32(0), "Already registered");

        // Generate UID
        bytes32 uid = keccak256(abi.encodePacked(
            msg.sender,
            subnetId,
            block.timestamp,
            block.number,
            "validator"
        ));

        // Transfer stakes
        if (coreStake > 0) {
            coreToken.transferFrom(msg.sender, address(this), coreStake);
        }
        if (btcStake > 0) {
            btcToken.transferFrom(msg.sender, address(this), btcStake);
        }

        // Create validator data
        validators[msg.sender] = ValidatorData({
            uid: uid,
            subnet_uid: subnetId,
            stake: coreStake + btcStake,
            scaled_last_performance: 0,
            scaled_trust_score: DIVISOR_64, // 100% initial trust for validators
            accumulated_rewards: 0,
            last_update_time: uint64(block.timestamp),
            performance_history_hash: bytes32(0),
            wallet_addr_hash: keccak256(abi.encodePacked(msg.sender)),
            status: STATUS_ACTIVE,
            registration_time: uint64(block.timestamp),
            api_endpoint: apiEndpoint
        });

        // Update subnet state
        subnetValidators[subnetId].push(msg.sender);
        validatorToSubnet[msg.sender] = subnetId;
        subnetDynamic[subnetId].validator_count++;
        subnetDynamic[subnetId].total_stake += coreStake + btcStake;

        // Grant validator role
        _grantRole(VALIDATOR_ROLE, msg.sender);

        emit ValidatorRegistered(msg.sender, subnetId, uid);
    }

    // ============ GETTER FUNCTIONS (Metagraph-compatible) ============

    /**
     * @dev Get miner info (compatible with metagraph_datum.py)
     */
    function getMinerInfo(address minerAddress) external view returns (MinerData memory) {
        return miners[minerAddress];
    }

    /**
     * @dev Get validator info (compatible with metagraph_datum.py)
     */
    function getValidatorInfo(address validatorAddress) external view returns (ValidatorData memory) {
        return validators[validatorAddress];
    }

    /**
     * @dev Get network stats for metagraph
     */
    function getNetworkStats() external view returns (
        uint256 totalMiners,
        uint256 totalValidators,
        uint256 totalStaked,
        uint256 totalRewards
    ) {
        // Sum across all subnets
        for (uint64 i = 0; i < nextSubnetId; i++) {
            if (subnetStatic[i].net_uid != 0) {
                totalMiners += subnetDynamic[i].miner_count;
                totalValidators += subnetDynamic[i].validator_count;
                totalStaked += subnetDynamic[i].total_stake;
            }
        }
        totalRewards = totalNetworkStake; // Simplified
    }

    /**
     * @dev Get all miners in a subnet (ModernTensor-style)
     */
    function getSubnetMiners(uint64 subnetId) external view returns (address[] memory) {
        return subnetMiners[subnetId];
    }

    /**
     * @dev Get all validators in a subnet (ModernTensor-style)
     */
    function getSubnetValidators(uint64 subnetId) external view returns (address[] memory) {
        return subnetValidators[subnetId];
    }

    /**
     * @dev Get trust scores for a subnet (ModernTensor-inspired)
     */
    function getTrustScores(uint64 subnetId) external view returns (uint64[] memory scores) {
        address[] memory minerAddresses = subnetMiners[subnetId];
        scores = new uint64[](minerAddresses.length);
        
        for (uint256 i = 0; i < minerAddresses.length; i++) {
            scores[i] = miners[minerAddresses[i]].scaled_trust_score;
        }
    }

    // ============ SCORE UPDATE FUNCTIONS (For Validators) ============

    /**
     * @dev Update miner performance and trust scores (Validator only)
     */
    function updateMinerScores(
        address minerAddr,
        uint64 newPerformance,
        uint64 newTrustScore
    ) external onlyRole(VALIDATOR_ROLE) {
        require(miners[minerAddr].uid != bytes32(0), "Miner not found");
        require(newPerformance <= DIVISOR_64, "Invalid performance");
        require(newTrustScore <= DIVISOR_64, "Invalid trust score");
        
        miners[minerAddr].scaled_last_performance = newPerformance;
        miners[minerAddr].scaled_trust_score = newTrustScore;
        miners[minerAddr].last_update_time = uint64(block.timestamp);
        
        emit MinerScoreUpdated(minerAddr, miners[minerAddr].uid, newPerformance, newTrustScore);
    }
    
    /**
     * @dev Update validator performance and trust scores (Validator only)
     */
    function updateValidatorScores(
        address validatorAddr,
        uint64 newPerformance,
        uint64 newTrustScore
    ) external onlyRole(VALIDATOR_ROLE) {
        require(validators[validatorAddr].uid != bytes32(0), "Validator not found");
        require(newPerformance <= DIVISOR_64, "Invalid performance");
        require(newTrustScore <= DIVISOR_64, "Invalid trust score");
        
        validators[validatorAddr].scaled_last_performance = newPerformance;
        validators[validatorAddr].scaled_trust_score = newTrustScore;
        validators[validatorAddr].last_update_time = uint64(block.timestamp);
        
        emit ValidatorScoreUpdated(validatorAddr, validators[validatorAddr].uid, newPerformance, newTrustScore);
    }

    // ============ INTERNAL HELPER FUNCTIONS ============

    function _createSubnet(
        string memory name,
        address owner,
        uint256 minMinerStake,
        uint256 minValidatorStake
    ) internal returns (uint64 subnetId) {
        subnetId = 0; // Default subnet
        
        subnetStatic[subnetId] = SubnetStaticData({
            net_uid: subnetId,
            name: name,
            owner_addr: owner,
            max_miners: 1000,
            max_validators: 100,
            immunity_period: IMMUNITY_PERIOD,
            creation_time: uint64(block.timestamp),
            description: "Default subnet for ModernTensorAI",
            version: 1,
            min_stake_miner: minMinerStake,
            min_stake_validator: minValidatorStake
        });

        subnetDynamic[subnetId] = SubnetDynamicData({
            net_uid: subnetId,
            scaled_weight: DIVISOR_64,
            scaled_performance: 0,
            current_epoch: 0,
            registration_open: 1,
            reg_cost: 0,
            scaled_incentive_ratio: DIVISOR_64,
            last_update_time: uint64(block.timestamp),
            total_stake: 0,
            validator_count: 0,
            miner_count: 0
        });
    }
} 