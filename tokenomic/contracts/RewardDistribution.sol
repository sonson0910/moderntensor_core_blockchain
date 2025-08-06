// SPDX-License-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract RewardDistribution is Ownable {
    IERC20 public token;
    uint256 public availableBalance;
    address public rewardEmission; // Thêm biến để lưu địa chỉ RewardEmission

    struct Subnet {
        uint256 subnetId;
        address subnetAddress;
        uint256 weight;
    }

    struct Participant {
        address participantAddress;
        uint256 performanceScore;
    }

    Subnet[] public subnets;
    mapping(uint256 => Participant[]) public validators;
    mapping(uint256 => Participant[]) public miners;

    uint256 public subnetRatio; // 18% = 1800 basis points
    uint256 public validatorRatio; // 41% = 4100
    uint256 public minerRatio; // 41% = 4100

    event RewardsDistributed(
        uint256 subnetId,
        address indexed recipient,
        uint256 amount,
        string role
    );

    constructor(address _token) Ownable() {
        token = IERC20(_token);
        subnetRatio = 1800;
        validatorRatio = 4100;
        minerRatio = 4100;
        availableBalance = 0;
    }

    function setRewardEmission(address _rewardEmission) external onlyOwner {
        require(_rewardEmission != address(0), "Invalid address");
        rewardEmission = _rewardEmission;
    }

    function setSubnets(uint256[] memory _subnetIds,address[] memory _subnetAddresses, uint256[] memory _weights) external onlyOwner {
        require(_subnetAddresses.length == _weights.length, "Invalid input lengths");
        require(_subnetIds.length == _weights.length, "Invalid input lengths");
        delete subnets;
        uint256 totalWeight = 0;
        for (uint256 i = 0; i < _subnetAddresses.length; i++) {
            subnets.push(Subnet({subnetId: _subnetIds[i],subnetAddress: _subnetAddresses[i], weight: _weights[i]}));
            totalWeight += _weights[i];
        }
        require(totalWeight > 0, "Total weight must be positive");
    }
event DebugStep(string step, uint256 subnetId, string message);

    function setParticipants(
        uint256 _subnetId,
        address[] memory _validatorAddresses,
        uint256[] memory _validatorScores,
        address[] memory _minerAddresses,
        uint256[] memory _minerScores
    ) external onlyOwner {
        emit DebugStep("Start setParticipants", _subnetId, "Checking subnet ID");
        bool subnetExists = false;
        for (uint256 i = 0; i < subnets.length; i++) {
            if (subnets[i].subnetId == _subnetId) {
                subnetExists = true;
                break;
            }
        }
        require(subnetExists, "Invalid subnet ID");

        emit DebugStep("Checking input lengths", _subnetId, "Validating arrays");
        require(_validatorAddresses.length == _validatorScores.length, "Invalid validator input");
        require(_minerAddresses.length == _minerScores.length, "Invalid miner input");

        emit DebugStep("Checking addresses and scores", _subnetId, "Validating data");
        for (uint256 i = 0; i < _validatorAddresses.length; i++) {
            require(_validatorAddresses[i] != address(0), "Invalid validator address");
            require(_validatorScores[i] > 0, "Validator score must be positive");
        }
        for (uint256 i = 0; i < _minerAddresses.length; i++) {
            require(_minerAddresses[i] != address(0), "Invalid miner address");
            require(_minerScores[i] > 0, "Miner score must be positive");
        }

        emit DebugStep("Deleting validators", _subnetId, "Clearing old data");
        delete validators[_subnetId];
        emit DebugStep("Deleting miners", _subnetId, "Clearing old data");
        delete miners[_subnetId];

        emit DebugStep("Setting validators", _subnetId, "Adding new validators");
        for (uint256 i = 0; i < _validatorAddresses.length; i++) {
            validators[_subnetId].push(
                Participant({participantAddress: _validatorAddresses[i], performanceScore: _validatorScores[i]})
            );
        }

        emit DebugStep("Setting miners", _subnetId, "Adding new miners");
        for (uint256 i = 0; i < _minerAddresses.length; i++) {
            miners[_subnetId].push(
                Participant({participantAddress: _minerAddresses[i], performanceScore: _minerScores[i]})
            );
        }
        emit DebugStep("Participants set successfully", _subnetId, "Completed");
    }

    function updateDistributionRatios(uint256 _subnetRatio, uint256 _validatorRatio, uint256 _minerRatio)
        external
        onlyOwner
    {
        require(_subnetRatio + _validatorRatio + _minerRatio == 10000, "Ratios must sum to 100%");
        subnetRatio = _subnetRatio;
        validatorRatio = _validatorRatio;
        minerRatio = _minerRatio;
    }

function distributeRewards(uint256 _amount) external onlyOwner {
    require(_amount <= availableBalance, "Insufficient available balance");
    require(subnets.length > 0, "No subnets configured");

    availableBalance -= _amount;

    uint256 totalWeight = 0;
    for (uint256 i = 0; i < subnets.length; i++) {
        totalWeight += subnets[i].weight;
    }

    for (uint256 i = 0; i < subnets.length; i++) {
        Subnet memory subnet = subnets[i];
        uint256 subnetShare = (_amount * subnet.weight) / totalWeight;

        // 1. Gửi phần subnet (18%)
        uint256 subnetAmount = (subnetShare * subnetRatio) / 10000;
        if (subnetAmount > 0) {
            require(token.transfer(subnet.subnetAddress, subnetAmount), "Transfer failed");
            emit RewardsDistributed(subnet.subnetId, subnet.subnetAddress, subnetAmount, "subnet");
        }

        // 2. Gửi phần validator (41%)
        uint256 validatorAmount = (subnetShare * validatorRatio) / 10000;
        uint256 totalValidatorScore = 0;
        for (uint256 j = 0; j < validators[subnet.subnetId].length; j++) {
            totalValidatorScore += validators[subnet.subnetId][j].performanceScore;
        }
        if (totalValidatorScore > 0) {
            for (uint256 j = 0; j < validators[subnet.subnetId].length; j++) {
                Participant memory validator = validators[subnet.subnetId][j];
                uint256 validatorShare = (validatorAmount * validator.performanceScore) / totalValidatorScore;
                if (validatorShare > 0) {
                    require(token.transfer(validator.participantAddress, validatorShare), "Transfer failed");
                    emit RewardsDistributed(subnet.subnetId, validator.participantAddress, validatorShare, "validator");
                }
            }
        }

        // 3. Gửi phần miner (41%)
        uint256 minerAmount = (subnetShare * minerRatio) / 10000;
        uint256 totalMinerScore = 0;
        for (uint256 j = 0; j < miners[subnet.subnetId].length; j++) {
            totalMinerScore += miners[subnet.subnetId][j].performanceScore;
        }
        if (totalMinerScore > 0) {
            for (uint256 j = 0; j < miners[subnet.subnetId].length; j++) {
                Participant memory miner = miners[subnet.subnetId][j];
                uint256 minerShare = (minerAmount * miner.performanceScore) / totalMinerScore;
                if (minerShare > 0) {
                    require(token.transfer(miner.participantAddress, minerShare), "Transfer failed");
                    emit RewardsDistributed(subnet.subnetId, miner.participantAddress, minerShare, "miner");
                }
            }
        }
    }
}

    function getAvailableBalance() external view returns (uint256) {
        return availableBalance;
    }

    function receiveTokens(uint256 amount) external {
        require(msg.sender == rewardEmission, "Only RewardEmission can call");
        availableBalance += amount;
    }
    function getSubnets() external view returns (Subnet[] memory) {
    return subnets;
    }

    function getValidators(uint256 subnetId) external view returns (Participant[] memory) {
        return validators[subnetId];
    }

    function getMiners(uint256 subnetId) external view returns (Participant[] memory) {
        return miners[subnetId];
    }

}