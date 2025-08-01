// SPDX-License-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract Treasury is Ownable {
    IERC20 public token; // Token MTNSRTEST01
    uint256 public balance;

    event Deposited(address indexed sender, uint256 amount);
    event Withdrawn(address indexed recipient, uint256 amount);

    constructor(address _token) Ownable() {
        token = IERC20(_token);
    }

    function initializeTreasury() external onlyOwner {
        // Không cần logic bổ sung vì balance đã được khởi tạo
    }

    function depositToTreasury(uint256 amount) external {
        require(amount > 0, "Amount must be greater than 0");
        require(token.transferFrom(msg.sender, address(this), amount), "Transfer failed");
        balance += amount;
        emit Deposited(msg.sender, amount);
    }

    function withdrawFromTreasury(address recipient, uint256 amount) external onlyOwner {
        require(amount > 0, "Amount must be greater than 0");
        require(balance >= amount, "Insufficient balance");
        require(token.transfer(recipient, amount), "Transfer failed");
        balance -= amount;
        emit Withdrawn(recipient, amount);
    }
}