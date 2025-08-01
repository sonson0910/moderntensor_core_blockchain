// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract MTNSRTEST01 is ERC20, Ownable {
    uint256 public totalSupplyCap;
    uint8 private constant _DECIMALS = 8;

    constructor(uint256 initialSupply) ERC20("Moderntensor Token Test01", "MTNSRTEST01") Ownable() {
        totalSupplyCap = initialSupply;
        _mint(msg.sender, initialSupply);
    }

    function decimals() public pure override returns (uint8) {
        return _DECIMALS;
    }

    function mint(address to, uint256 amount) external onlyOwner {
        require(to != address(0), "Invalid address");
        require(amount > 0, "Amount must be greater than 0");
        totalSupplyCap += amount;
        _mint(to, amount);
    }

    function burn(uint256 amount) external {
        require(amount > 0, "Amount must be greater than 0");
        _burn(msg.sender, amount);
    }

    function burnFrom(address account, uint256 amount) external onlyOwner {
        require(amount > 0, "Amount must be greater than 0");
        uint256 currentAllowance = allowance(account, msg.sender);
        require(currentAllowance >= amount, "Burn amount exceeds allowance");
        _approve(account, msg.sender, currentAllowance - amount);
        _burn(account, amount);
    }

    mapping(address => bool) public frozenAccounts;
    event AccountFrozen(address indexed account, bool frozen);

    function freezeAccount(address account, bool freeze) external onlyOwner {
        require(account != address(0), "Invalid address");
        frozenAccounts[account] = freeze;
        emit AccountFrozen(account, freeze);
    }

    function _beforeTokenTransfer(address from, address to, uint256 amount) internal virtual override {
        super._beforeTokenTransfer(from, to, amount);
        require(!frozenAccounts[from], "Sender account is frozen");
        require(!frozenAccounts[to], "Recipient account is frozen");
    }
}
