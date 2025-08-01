const { ethers } = require("hardhat");
require("dotenv").config();

async function main() {
    const [signer] = await ethers.getSigners();
    console.log("Address:", signer.address);
    const balance = await ethers.provider.getBalance(signer.address);
    console.log("Balance:", ethers.formatEther(balance), "CORE");
}

main().catch(console.error);
