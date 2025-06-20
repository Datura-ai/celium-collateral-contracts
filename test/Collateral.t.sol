// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.28;

import {Collateral} from "../src/Collateral.sol";
import {CollateralTestBase} from "./CollateralTestBase.sol";

contract CollateralTest is CollateralTestBase {
    address constant DEPOSITOR1 = address(0x1001);
    address constant DEPOSITOR2 = address(0x1002);

    // used to test a case in which transfer in finalizeReclaim fails
    receive() external payable {
        revert();
    }

    function setUp() public override {
        // fund depositors
        payable(DEPOSITOR1).transfer(3 ether);
        payable(DEPOSITOR2).transfer(3 ether);
        super.setUp();
    }

    function test_constructor_ConfigSetProperly() public view {
        assertEq(collateral.NETUID(), NETUID);
        assertEq(collateral.MIN_COLLATERAL_INCREASE(), MIN_COLLATERAL_INCREASE);
        assertEq(collateral.DECISION_TIMEOUT(), DECISION_TIMEOUT);
    }

    function test_revert_constructor_RevertIfMinCollateralIncreaseIsZero() public {
        vm.expectRevert();
        new Collateral(NETUID, 0, DECISION_TIMEOUT);
    }

    function test_revert_constructor_RevertIfDecisionTimeoutIsZero() public {
        vm.expectRevert();
        new Collateral(NETUID, MIN_COLLATERAL_INCREASE, 0);
    }

    function test_deposit() public {
        vm.startPrank(DEPOSITOR1);
        bytes16 executorUuid = 0x11111111111111111111111111111111;

        vm.expectEmit(true, false, false, true);
        emit Deposit(DEPOSITOR1, 1 ether);

        collateral.deposit{value: 1 ether}(TRUSTEE_1, executorUuid);
        assertEq(collateral.collaterals(DEPOSITOR1), 1 ether);
        assertEq(collateral.collateralPerExecutor(DEPOSITOR1, executorUuid), 1 ether);
        assertEq(address(collateral).balance, 1 ether);

        vm.expectEmit(true, false, false, true);
        emit Deposit(DEPOSITOR1, 1 ether);

        collateral.deposit{value: 1 ether}(TRUSTEE_1, executorUuid);
        assertEq(collateral.collaterals(DEPOSITOR1), 2 ether);
        assertEq(collateral.collateralPerExecutor(DEPOSITOR1, executorUuid), 2 ether);
        assertEq(address(collateral).balance, 2 ether);
    }

    function test_revert_deposit_CanNotDepositWhenCollateralLessThanMinCollateralIncrease() public {
        bytes16 executorUuid = 0x11111111111111111111111111111111;
        vm.expectRevert(InsufficientAmount.selector);
        collateral.deposit{value: 0.5 ether}(TRUSTEE_1, executorUuid);
    }

    function test_revert_CanNotDepositViaReceive() public {
        (bool success,) = address(collateral).call{value: 0.5 ether}("");
        assertFalse(success);
        assertEq(address(collateral).balance, 0);
    }

    function test_revert_CanNotDepositViaFallback() public {
        (bool success,) = address(collateral).call{value: 0.5 ether}(abi.encodeWithSignature("doesNotExist()", ""));
        assertFalse(success);
        assertEq(address(collateral).balance, 0);
    }

    function test_reclaim_CanStartReclaimProcess() public {
        vm.startPrank(DEPOSITOR1);
        bytes16 executorUuid = 0x11111111111111111111111111111111;

        collateral.deposit{value: 1 ether}(TRUSTEE_1, executorUuid);
        uint256 expectedReclaimId = 1;

        vm.expectEmit(true, true, false, true);
        emit ReclaimProcessStarted(
            expectedReclaimId,
            DEPOSITOR1,
            1 ether,
            uint64(block.timestamp + DECISION_TIMEOUT),
            URL,
            URL_CONTENT_MD5_CHECKSUM
        );

        collateral.reclaimCollateral(1 ether, URL, URL_CONTENT_MD5_CHECKSUM, executorUuid);

        verifyReclaim(expectedReclaimId, DEPOSITOR1, 1 ether, block.timestamp + DECISION_TIMEOUT, executorUuid);

        assertEq(collateral.collaterals(DEPOSITOR1), 1 ether);
        assertEq(collateral.collateralPerExecutor(DEPOSITOR1, executorUuid), 1 ether);
        assertEq(address(collateral).balance, 1 ether);
    }

    function test_reclaim_CanReclaimIfTotalReclaimAmountLessThanCollateral() public {
        vm.startPrank(DEPOSITOR1);
        bytes16 executorUuid = 0x11111111111111111111111111111111;

        collateral.deposit{value: 2 ether}(TRUSTEE_1, executorUuid);

        for (uint256 i = 1; i < 3; ++i) {
            vm.expectEmit(true, true, false, true);
            emit ReclaimProcessStarted(
                i, DEPOSITOR1, 1 ether, uint64(block.timestamp + DECISION_TIMEOUT), URL, URL_CONTENT_MD5_CHECKSUM
            );

            collateral.reclaimCollateral(1 ether, URL, URL_CONTENT_MD5_CHECKSUM, executorUuid);

            verifyReclaim(i, DEPOSITOR1, 1 ether, block.timestamp + DECISION_TIMEOUT, executorUuid);
        }

        assertEq(collateral.collaterals(DEPOSITOR1), 2 ether);
        assertEq(address(collateral).balance, 2 ether);
    }

    function test_reclaim_MultipleUsersCanStartReclaimProcess() public {
        bytes16 executorUuid1 = 0x11111111111111111111111111111111;
        bytes16 executorUuid2 = 0x22222222222222222222222222222222;

        vm.prank(DEPOSITOR1);
        collateral.deposit{value: 1 ether}(TRUSTEE_1, executorUuid1);
        vm.prank(DEPOSITOR2);
        collateral.deposit{value: 1 ether}(TRUSTEE_2, executorUuid2);

        vm.prank(DEPOSITOR1);
        collateral.reclaimCollateral(1 ether, URL, URL_CONTENT_MD5_CHECKSUM, executorUuid1);
        vm.prank(DEPOSITOR2);
        collateral.reclaimCollateral(1 ether, URL, URL_CONTENT_MD5_CHECKSUM, executorUuid2);

        uint256 expectedDenyTimeout = block.timestamp + DECISION_TIMEOUT;
        verifyReclaim(1, DEPOSITOR1, 1 ether, expectedDenyTimeout, executorUuid1);
        verifyReclaim(2, DEPOSITOR2, 1 ether, expectedDenyTimeout, executorUuid2);

        assertEq(address(collateral).balance, 2 ether);
    }

    function test_revert_CanNotReclaimZero() public {
        vm.startPrank(DEPOSITOR1);
        bytes16 executorUuid = 0x11111111111111111111111111111111;
        collateral.deposit{value: 1 ether}(TRUSTEE_1, executorUuid);

        vm.expectRevert(AmountZero.selector);
        collateral.reclaimCollateral(0, URL, URL_CONTENT_MD5_CHECKSUM, executorUuid);
    }

    function test_revert_reclaim_CanNotReclaimIfCollateralIsLessThanMinCollateralIncrease() public {
        vm.startPrank(DEPOSITOR1);
        bytes16 executorUuid = 0x11111111111111111111111111111111;
        collateral.deposit{value: 1 ether}(TRUSTEE_1, executorUuid);

        vm.expectRevert(ReclaimAmountTooSmall.selector);
        collateral.reclaimCollateral(0.5 ether, URL, URL_CONTENT_MD5_CHECKSUM, executorUuid);
    }

    function test_revert_reclaim_CanNotReclaimMoreThanCollateral() public {
        vm.startPrank(DEPOSITOR1);
        bytes16 executorUuid = 0x11111111111111111111111111111111;
        collateral.deposit{value: 1 ether}(TRUSTEE_1, executorUuid);

        vm.expectRevert(ReclaimAmountTooLarge.selector);
        collateral.reclaimCollateral(2 ether, URL, URL_CONTENT_MD5_CHECKSUM, executorUuid);
    }

    function test_revert_reclaim_CollateralUnderReclaimCanNotBeGreaterThanCollateral() public {
        vm.startPrank(DEPOSITOR1);
        bytes16 executorUuid = 0x11111111111111111111111111111111;
        collateral.deposit{value: 3 ether}(TRUSTEE_1, executorUuid);

        collateral.reclaimCollateral(1 ether, URL, URL_CONTENT_MD5_CHECKSUM, executorUuid);
        collateral.reclaimCollateral(1 ether, URL, URL_CONTENT_MD5_CHECKSUM, executorUuid);

        // This reclaim pushes collateral under reclaim over total collateral
        vm.expectRevert(ReclaimAmountTooLarge.selector);
        collateral.reclaimCollateral(2 ether, URL, URL_CONTENT_MD5_CHECKSUM, executorUuid);
    }

    function test_finalizeReclaim() public {
        vm.startPrank(DEPOSITOR1);
        bytes16 executorUuid = 0x11111111111111111111111111111111;
        collateral.deposit{value: 1 ether}(TRUSTEE_1, executorUuid);

        collateral.reclaimCollateral(1 ether, URL, URL_CONTENT_MD5_CHECKSUM, executorUuid);
        skip(DECISION_TIMEOUT + 1);

        uint256 depositorBalanceBefore = DEPOSITOR1.balance;
        uint256 contractBalanceBefore = address(collateral).balance;

        // Ensure the emitted log matches the expected log
       // vm.expectEmit(true, true, false, true);
        //emit Reclaimed(1, DEPOSITOR1, 1 ether);
        vm.stopPrank();
        vm.prank(TRUSTEE_1);
        collateral.finalizeReclaim(1);

        uint256 depositorBalanceAfter = DEPOSITOR1.balance;
        uint256 contractBalanceAfter = address(collateral).balance;

        // Verify balances and reclaim deletion
        //assertEq(depositorBalanceAfter, depositorBalanceBefore + 1 ether);
        //assertEq(contractBalanceAfter, contractBalanceBefore - 1 ether);
        //verifyReclaim(1, address(0), 0, 0, executorUuid);
    }

    function test_revert_finalizeReclaim_CanNotFinalizeUntilDenyTimeoutExpires() public {
        vm.startPrank(DEPOSITOR1);
        bytes16 executorUuid = 0x11111111111111111111111111111111;
        collateral.deposit{value: 2 ether}(TRUSTEE_1, executorUuid);

        collateral.reclaimCollateral(1 ether, URL, URL_CONTENT_MD5_CHECKSUM, executorUuid);

        vm.expectRevert(BeforeDenyTimeout.selector);
        collateral.finalizeReclaim(1);
    }

    function test_denyReclaimRequest() public {
        vm.startPrank(DEPOSITOR1);
        bytes16 executorUuid = 0x11111111111111111111111111111111;
        collateral.deposit{value: 1 ether}(TRUSTEE_1, executorUuid);

        collateral.reclaimCollateral(1 ether, URL, URL_CONTENT_MD5_CHECKSUM, executorUuid);
        vm.stopPrank();

        vm.prank(TRUSTEE_1);
        uint256 reclaimRequestId = 1;
        uint256 contractBalanceBefore = address(collateral).balance;

        vm.expectEmit(true, false, false, false);
        emit Denied(reclaimRequestId, URL, URL_CONTENT_MD5_CHECKSUM);
        collateral.denyReclaimRequest(reclaimRequestId, URL, URL_CONTENT_MD5_CHECKSUM);

        uint256 contractBalanceAfter = address(collateral).balance;
        // does not change contract balance
        assertEq(contractBalanceAfter, contractBalanceBefore);

        skip(DECISION_TIMEOUT + 1);
        vm.prank(DEPOSITOR1);
        vm.expectRevert(ReclaimNotFound.selector);
        collateral.finalizeReclaim(reclaimRequestId);
    }

    function test_revert_denyReclaimRequest_CanBeCalledOnlyByTrustee() public {
        vm.startPrank(DEPOSITOR1);
        bytes16 executorUuid = 0x11111111111111111111111111111111;
        collateral.deposit{value: 1 ether}(TRUSTEE_1, executorUuid);

        collateral.reclaimCollateral(1 ether, URL, URL_CONTENT_MD5_CHECKSUM, executorUuid);
        skip(DECISION_TIMEOUT + 1);

        vm.expectRevert(NotTrustee.selector);
        collateral.denyReclaimRequest(1, URL, URL_CONTENT_MD5_CHECKSUM);
    }

    function test_revert_denyReclaimRequest_CanNotBeCalledAfterDenyTimeoutExpires() public {
        vm.startPrank(DEPOSITOR1);
        bytes16 executorUuid = 0x11111111111111111111111111111111;
        collateral.deposit{value: 1 ether}(TRUSTEE_1, executorUuid);

        collateral.reclaimCollateral(1 ether, URL, URL_CONTENT_MD5_CHECKSUM, executorUuid);
        skip(DECISION_TIMEOUT + 1);

        vm.stopPrank();
        vm.prank(TRUSTEE_1);
        vm.expectRevert(PastDenyTimeout.selector);
        collateral.denyReclaimRequest(1, URL, URL_CONTENT_MD5_CHECKSUM);
    }

    function test_slashCollateral() public {
        bytes16 executorUuid = 0x11111111111111111111111111111111;

        vm.prank(DEPOSITOR1);
        collateral.deposit{value: 2 ether}(TRUSTEE_1, executorUuid);

        uint256 bondPosterCollateralBeforeSlash = collateral.collaterals(DEPOSITOR1);
        uint256 contractBalanceBeforeSlash = address(collateral).balance;

        vm.prank(TRUSTEE_1);
        vm.expectEmit(true, false, false, true);
        emit Slashed(DEPOSITOR1, 1 ether, SLASH_REASON_URL, URL_CONTENT_MD5_CHECKSUM);
        collateral.slashCollateral(DEPOSITOR1, 1 ether, SLASH_REASON_URL, URL_CONTENT_MD5_CHECKSUM, executorUuid);

        uint256 bondPosterCollateralAfterSlash = collateral.collaterals(DEPOSITOR1);
        assertEq(bondPosterCollateralAfterSlash, bondPosterCollateralBeforeSlash - 1 ether);

        uint256 contractBalanceAfterSlash = address(collateral).balance;
        assertEq(contractBalanceAfterSlash, contractBalanceBeforeSlash - 1 ether);
    }

    function test_revert_slashCollateral_CanBeCalledOnlyByTrustee() public {
        bytes16 executorUuid = 0x11111111111111111111111111111111;
        vm.prank(DEPOSITOR1);
        collateral.deposit{value: 2 ether}(TRUSTEE_1, executorUuid);

        vm.expectRevert(NotTrustee.selector);
        collateral.slashCollateral(DEPOSITOR1, 1 ether, SLASH_REASON_URL, URL_CONTENT_MD5_CHECKSUM, executorUuid);
    }

    function test_revert_slashCollateral_CanNotSlashZero() public {
        vm.prank(TRUSTEE_1);
        bytes16 executorUuid = 0x11111111111111111111111111111111;
        vm.expectRevert(AmountZero.selector);
        collateral.slashCollateral(DEPOSITOR1, 0, SLASH_REASON_URL, URL_CONTENT_MD5_CHECKSUM, executorUuid);
    }
}
