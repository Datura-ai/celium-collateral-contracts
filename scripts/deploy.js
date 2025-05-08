const hre = require("hardhat");

async function deployCollateral() {
  const [deployer] = await hre.ethers.getSigners();

  const Collateral = await hre.ethers.getContractFactory("Collateral");
  const contract = await Collateral.deploy(1, hre.ethers.parseEther("0.1"), 60);

  await contract.waitForDeployment();
  console.log("Collateral deployed to:", await contract.getAddress());
}

async function deployValueStore() {
  const [deployer] = await hre.ethers.getSigners();

  const Collateral = await hre.ethers.getContractFactory("ValueStore");
  const contract = await Collateral.deploy();

  await contract.waitForDeployment();
  console.log("ValueStore deployed to:", await contract.getAddress());
}


async function main() {
  await deployCollateral();
  await deployValueStore();
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

