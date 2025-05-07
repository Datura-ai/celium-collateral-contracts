const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();

  const Collateral = await hre.ethers.getContractFactory("Collateral");
  const contract = await Collateral.deploy(1, hre.ethers.parseEther("0.1"), 60);

  await contract.waitForDeployment();
  console.log("Collateral deployed to:", await contract.getAddress());
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
