// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract Governance is Ownable {
    IERC20 public token; // Token MTNSRTEST01 for voting

    struct Proposal {
        address proposer;
        uint256 votes;
        bool executed;
    }

    mapping(uint256 => Proposal) public proposals;
    uint256 public nextProposalId;

    event ProposalCreated(uint256 indexed proposalId, address proposer);
    event Voted(uint256 indexed proposalId, address voter, uint256 votes);
    event ProposalExecuted(uint256 indexed proposalId);

    constructor(address _token) Ownable(msg.sender) {
        token = IERC20(_token);
    }

    function initializeGovernance() external onlyOwner {
        // Không cần logic bổ sung vì mapping và nextProposalId đã được khởi tạo
    }

    function propose() external {
        proposals[nextProposalId] = Proposal({
            proposer: msg.sender,
            votes: 0,
            executed: false
        });
        emit ProposalCreated(nextProposalId, msg.sender);
        nextProposalId += 1;
    }

    function vote(uint256 proposalId) external {
        Proposal storage proposal = proposals[proposalId];
        require(!proposal.executed, "Proposal already executed");
        require(proposal.proposer != address(0), "Proposal does not exist");

        uint256 voterBalance = token.balanceOf(msg.sender);
        require(voterBalance > 0, "No tokens to vote");

        proposal.votes += voterBalance;
        emit Voted(proposalId, msg.sender, voterBalance);
    }

    function executeProposal(uint256 proposalId) external onlyOwner {
        Proposal storage proposal = proposals[proposalId];
        require(!proposal.executed, "Proposal already executed");
        require(proposal.proposer != address(0), "Proposal does not exist");

        proposal.executed = true;
        // Thêm logic thực thi đề xuất, ví dụ: cập nhật thông số hoặc gọi hàm khác
        emit ProposalExecuted(proposalId);
    }
}