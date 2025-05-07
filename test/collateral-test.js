const { expect } = require("chai");
const { ethers } = require("hardhat"); // Ensure ethers is imported from hardhat

describe("Collateral Contract", function () {
  let Collateral;
  let collateral;
  let owner;
  let addr1;
  let addr2;
  let validatorAddress;

  beforeEach(async function () {
    // Get the signers
    [owner, addr1, addr2, validatorAddress] = await ethers.getSigners();

    // Deploy the Collateral contract
    const NETUID = 1;
    const MIN_COLLATERAL_INCREASE = ethers.utils.parseEther("1.0"); // 1 Ether
    const DECISION_TIMEOUT = 60 * 60; // 1 hour in seconds

    const CollateralFactory = await ethers.getContractFactory("Collateral");
    collateral = await CollateralFactory.deploy(
      NETUID,
      MIN_COLLATERAL_INCREASE,
      DECISION_TIMEOUT
    );
    await collateral.deployed();
  });

  it("should allow users to deposit collateral", async function () {
    // User deposits collateral
    await collateral.connect(addr1).deposit(validatorAddress.address, ethers.utils.formatBytes32String("executor1"), { value: ethers.utils.parseEther("2.0") });

    // Check the balance of collateral
    const depositedAmount = await collateral.collaterals(addr1.address);
    expect(depositedAmount).to.equal(ethers.utils.parseEther("2.0"));
  });

  it("should allow a user to reclaim collateral", async function () {
    // User deposits collateral first
    await collateral.connect(addr1).deposit(validatorAddress.address, ethers.utils.formatBytes32String("executor1"), { value: ethers.utils.parseEther("2") });

    // User requests to reclaim a portion of the collateral
    await collateral.connect(addr1).reclaimCollateral(
      ethers.utils.parseEther("1"), 
      "http://example.com/reclaim", 
      ethers.utils.formatBytes32String("checksum"),
      ethers.utils.formatBytes32String("executor1")
    );

    // Ensure that the reclaim was registered
    const reclaim = await collateral.reclaims(1);
    expect(reclaim.miner).to.equal(addr1.address);
    expect(reclaim.amount).to.equal(ethers.utils.parseEther("1"));
  });

  it("should allow validator to finalize a reclaim", async function () {
    // User deposits collateral
    await collateral.connect(addr1).deposit(validatorAddress.address, ethers.utils.formatBytes32String("executor1"), { value: ethers.utils.parseEther("2") });

    // User requests to reclaim collateral
    await collateral.connect(addr1).reclaimCollateral(
      ethers.utils.parseEther("1"),
      "http://example.com/reclaim",
      ethers.utils.formatBytes32String("checksum"),
      ethers.utils.formatBytes32String("executor1")
    );

    // Fast forward time to after the decision timeout
    await ethers.provider.send('evm_increaseTime', [60 * 60]); // Increase time by 1 hour
    await ethers.provider.send('evm_mine', []); // Mine a block

    // Validator finalizes the reclaim
    await collateral.connect(validatorAddress).finalizeReclaim(1);

    // Check the balance after reclaim
    const remainingCollateral = await collateral.collaterals(addr1.address);
    expect(remainingCollateral).to.equal(ethers.utils.parseEther("1"));
  });

  it("should allow the validator to deny a reclaim", async function () {
    // User deposits collateral
    await collateral.connect(addr1).deposit(validatorAddress.address, ethers.utils.formatBytes32String("executor1"), { value: ethers.utils.parseEther("2") });

    // User requests to reclaim collateral
    await collateral.connect(addr1).reclaimCollateral(
      ethers.utils.parseEther("1"),
      "http://example.com/reclaim",
      ethers.utils.formatBytes32String("checksum"),
      ethers.utils.formatBytes32String("executor1")
    );

    // Fast forward time to before the deny timeout
    await ethers.provider.send('evm_increaseTime', [30 * 60]); // Increase time by 30 minutes
    await ethers.provider.send('evm_mine', []); // Mine a block

    // Validator denies the reclaim
    await collateral.connect(validatorAddress).denyReclaimRequest(1, "http://example.com/reason", ethers.utils.formatBytes32String("checksum"));

    // Check that the reclaim was denied and collateral is still in place
    const reclaim = await collateral.reclaims(1);
    expect(reclaim.amount).to.equal(0);
    const remainingCollateral = await collateral.collaterals(addr1.address);
    expect(remainingCollateral).to.equal(ethers.utils.parseEther("2"));
  });
});
