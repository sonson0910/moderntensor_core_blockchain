// SPDX-License-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

interface IRewardDistribution {
    function receiveTokens(uint256 amount) external;
}

contract RewardEmission is Ownable {
    IERC20 public token;
    address public rewardDistributor;

    struct RewardState {
        uint256 startTime;
        uint256 lastEmissionTime;
        uint256 totalSupply;
        uint256 secondsPerPeriod;
        uint256 secondsPerHalving;
        uint256 totalDistributed;
        uint256 emissionCount;
    }

    RewardState public rewardState;
    uint256 public communityVaultBalance;

    event RewardEmitted(uint256 amount, uint256 emissionCount);
    event TokensTransferred(address to, uint256 amount);
    event EmissionParamsUpdated(uint256 newTotalSupply, uint256 newHalvingInterval);

    constructor(
        address _token,
        uint256 totalSupply,
        uint256 emissionIntervalSecs,
        uint256 secondsPerHalving
    ) Ownable() {
        token = IERC20(_token);
        rewardState = RewardState({
            startTime: block.timestamp,
            lastEmissionTime: block.timestamp,
            totalSupply: totalSupply,
            secondsPerPeriod: emissionIntervalSecs,
            secondsPerHalving: secondsPerHalving,
            totalDistributed: 0,
            emissionCount: 0
        });
    }

    function initializeVaultAndEpoch(uint256 depositAmount) external onlyOwner {
        require(communityVaultBalance == 0, "Vault already initialized");
        require(token.transferFrom(msg.sender, address(this), depositAmount), "Transfer failed");
        communityVaultBalance = depositAmount;
    }

    function topUpVault(uint256 amount) external onlyOwner {
        require(token.transferFrom(msg.sender, address(this), amount), "Transfer failed");
        communityVaultBalance += amount;
    }

    function emitReward() external onlyOwner {
        require(block.timestamp >= rewardState.lastEmissionTime + rewardState.secondsPerPeriod, "Not time for emission");
        require(rewardDistributor != address(0), "Reward distributor not set");

        uint256 periodsPerHalving = rewardState.secondsPerHalving / rewardState.secondsPerPeriod;
        uint256 initialReward = rewardState.totalSupply / (2 * periodsPerHalving);
        uint256 halvings = rewardState.emissionCount / periodsPerHalving;
        uint256 shift = halvings > 63 ? 63 : halvings;
        uint256 adjustedReward = initialReward >> shift;

        require(rewardState.totalDistributed + adjustedReward <= rewardState.totalSupply, "Exceeds total supply");
        require(communityVaultBalance >= adjustedReward, "Insufficient vault balance");

        // Chuyển token sang RewardDistribution
        communityVaultBalance -= adjustedReward;
        require(token.transfer(rewardDistributor, adjustedReward), "Transfer failed");

        // Gọi receiveTokens trên RewardDistribution
        IRewardDistribution(rewardDistributor).receiveTokens(adjustedReward);

        rewardState.lastEmissionTime = block.timestamp;
        rewardState.totalDistributed += adjustedReward;
        rewardState.emissionCount += 1;

        emit RewardEmitted(adjustedReward, rewardState.emissionCount);
        emit TokensTransferred(rewardDistributor, adjustedReward);
    }

    function updateEmissionParams(uint256 newTotalSupply, uint256 newHalvingInterval) external onlyOwner {
        rewardState.totalSupply = newTotalSupply;
        rewardState.secondsPerHalving = newHalvingInterval;
        emit EmissionParamsUpdated(newTotalSupply, newHalvingInterval);
    }

    function setRewardDistributor(address _rewardDistributor) external onlyOwner {
        rewardDistributor = _rewardDistributor;
    }

    function getEmissionCount() external view returns (uint256) {
        return rewardState.emissionCount;
    }
}