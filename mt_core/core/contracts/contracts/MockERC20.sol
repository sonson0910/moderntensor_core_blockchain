// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MockERC20 is ERC20 {
    constructor(
        string memory name,
        string memory symbol,
        uint256 initialSupply
    ) ERC20(name, symbol) {
        _mint(msg.sender, initialSupply);
    }

    // Mint function for testing
    function mint(address to, uint256 amount) public {
        _mint(to, amount);
    }

    // Allow anyone to approve any amount for testing
    function approveForAll(address spender, uint256 amount) public {
        _approve(msg.sender, spender, amount);
    }
}