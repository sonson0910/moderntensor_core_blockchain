// SPDX-License-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract Vesting is Ownable {
    IERC20 public token;

    struct VestingSchedule {
        address recipient;
        uint256 totalAmount;
        uint256 releasedAmount;
        uint256 startTime;
        uint256 duration;
    }

    mapping(address => VestingSchedule) public schedules;

    event VestingInitialized(address indexed recipient, uint256 totalAmount, uint256 startTime, uint256 duration);
    event TokensReleased(address indexed recipient, uint256 amount);

    constructor(address _token) Ownable() {
        token = IERC20(_token);
    }

    function initializeVesting(uint256 depositAmount) external onlyOwner {
        require(token.transferFrom(msg.sender, address(this), depositAmount), "Transfer failed");
    }

    function setupVesting(
        address recipient,
        uint256 totalAmount,
        uint256 startTime,
        uint256 duration
    ) external onlyOwner {
        require(startTime > block.timestamp, "Start time must be in the future");
        require(duration > 0, "Duration must be greater than 0");
        require(recipient != address(0), "Invalid recipient");

        if (schedules[recipient].totalAmount > 0) {
            delete schedules[recipient];
        }

        schedules[recipient] = VestingSchedule({
            recipient: recipient,
            totalAmount: totalAmount,
            releasedAmount: 0,
            startTime: startTime,
            duration: duration
        });

        emit VestingInitialized(recipient, totalAmount, startTime, duration);
    }

    function releaseVesting(address recipient) external {
        VestingSchedule storage schedule = schedules[recipient];
        require(schedule.totalAmount > 0, "No vesting schedule found");
        require(block.timestamp >= schedule.startTime, "Vesting not started");

        uint256 elapsed = block.timestamp - schedule.startTime;
        uint256 vestedAmount = (elapsed >= schedule.duration)
            ? schedule.totalAmount
            : (schedule.totalAmount * elapsed) / schedule.duration;

        uint256 toRelease = vestedAmount - schedule.releasedAmount;
        require(toRelease > 0, "No tokens to release");
        require(token.balanceOf(address(this)) >= toRelease, "Insufficient balance");

        schedule.releasedAmount = vestedAmount;
        require(token.transfer(recipient, toRelease), "Transfer failed");

        emit TokensReleased(recipient, toRelease);
    }

    function topUpVesting(uint256 amount) external onlyOwner {
        require(token.transferFrom(msg.sender, address(this), amount), "Transfer failed");
    }
}