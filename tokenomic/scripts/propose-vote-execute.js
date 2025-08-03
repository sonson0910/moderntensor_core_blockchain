import hardhat from "hardhat";
import * as dotenv from "dotenv";
dotenv.config();
const { ethers } = hardhat;
//demo trong tương lại thêm các trường để trỏ đến các tài nguyên cần thiết của các hoạt đọng ví dụ các tài liệu cho proposal, vote,..
async function main() {
  const governanceAddr = process.env.GOVERNANCE_ADDRESS;
  const Governance = await ethers.getContractAt("Governance", governanceAddr);

  // Propose
  const tx1 = await Governance.propose();
  await tx1.wait();
  const proposalId = (await Governance.nextProposalId()) - 1n;
  console.log("✅ Created proposal ID:", proposalId.toString());

  // Vote
  const tx2 = await Governance.vote(proposalId);
  await tx2.wait();
  const proposal = await Governance.proposals(proposalId);
  console.log("✅ Voted on proposal. Total votes now:", ethers.formatUnits(proposal.votes, 8));

  // Execute
  const tx3 = await Governance.executeProposal(proposalId);
  await tx3.wait();
  const updated = await Governance.proposals(proposalId);
  console.log("✅ Proposal executed:", updated.executed);
}

main().catch(console.error);
