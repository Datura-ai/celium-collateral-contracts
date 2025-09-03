// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.28;

import {Test} from "forge-std/Test.sol";
import {Collateral} from "../src/Collateral.sol";

abstract contract CollateralTestBase is Test {
    uint16 constant NETUID = 1;
    address constant TRUSTEE = address(0x1000);
    address constant BURN_ADDRESS = address(0x2000);
    uint64 constant DECISION_TIMEOUT = 1 days;
    uint256 constant MIN_COLLATERAL_INCREASE = 1 ether;
    string constant URL = "https://reclaimreason.io";
    string constant SLASH_REASON_URL = "https://slashreason.io";
    bytes16 constant URL_CONTENT_MD5_CHECKSUM = 0x12345678901234567890123456789012;

    Collateral public collateral;

    // this boilerplate code had to be copied from Collateral contract to be able to test events and errors
    // it's not possible to import events and errors from another contract
    event Deposit(bytes16 indexed executorId, address indexed miner, uint256 amount);
    event ReclaimProcessStarted(
        uint256 indexed reclaimRequestId,
        bytes16 indexed executorId,
        address indexed miner,
        uint256 amount,
        uint64 expirationTime,
        string url,
        bytes16 urlContentMd5Checksum
    );
    event Reclaimed(uint256 indexed reclaimRequestId, bytes16 indexed executorId, address indexed miner, uint256 amount);
    event Denied(uint256 indexed reclaimRequestId, string url, bytes16 urlContentMd5Checksum);
    event Slashed(
        bytes16 indexed executorId,
        address indexed miner,
        uint256 amount,
        string url,
        bytes16 urlContentMd5Checksum
    );

    error AmountZero();
    error BeforeDenyTimeout();
    error ExecutorNotOwned();
    error InsufficientAmount();
    error InvalidDepositMethod();
    error NotTrustee();
    error PastDenyTimeout();
    error ReclaimNotFound();
    error TransferFailed();
    error InsufficientCollateralForReclaim();

    function setUp() public virtual {
        collateral = new Collateral(NETUID, TRUSTEE, BURN_ADDRESS, MIN_COLLATERAL_INCREASE, DECISION_TIMEOUT);
    }

    function verifyReclaim(
        uint256 reclaimRequestId,
        bytes16 expectedExecutorId,
        address expectedMiner,
        uint256 expectedAmount,
        uint256 expectedDenyTimeout
    ) internal view {
        (bytes16 executorId, address miner, uint256 amount, uint64 denyTimeout) = collateral.reclaims(reclaimRequestId);
        assertEq(executorId, expectedExecutorId);
        assertEq(miner, expectedMiner);
        assertEq(amount, expectedAmount);
        assertEq(denyTimeout, expectedDenyTimeout);
    }
}
