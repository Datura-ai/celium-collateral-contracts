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
        assertEq(collateral.TRUSTEE(), TRUSTEE);
        assertEq(collateral.BURN_ADDRESS(), BURN_ADDRESS);
        assertEq(collateral.MIN_COLLATERAL_INCREASE(), MIN_COLLATERAL_INCREASE);
        assertEq(collateral.DECISION_TIMEOUT(), DECISION_TIMEOUT);
    }

    function test_revert_constructor_RevertIfTrusteeIsZero() public {
        vm.expectRevert("Trustee address must be non-zero");
        new Collateral(NETUID, address(0), BURN_ADDRESS, MIN_COLLATERAL_INCREASE, DECISION_TIMEOUT);
    }

    function test_revert_constructor_RevertIfBurnAddressIsZero() public {
        vm.expectRevert("Burn address must be non-zero");
        new Collateral(NETUID, TRUSTEE, address(0), MIN_COLLATERAL_INCREASE, DECISION_TIMEOUT);
    }

    function test_revert_constructor_RevertIfMinCollateralIncreaseIsZero() public {
        vm.expectRevert("Min collateral increase must be greater than 0");
        new Collateral(NETUID, TRUSTEE, BURN_ADDRESS, 0, DECISION_TIMEOUT);
    }

    function test_revert_constructor_RevertIfDecisionTimeoutIsZero() public {
        vm.expectRevert("Decision timeout must be greater than 0");
        new Collateral(NETUID, TRUSTEE, BURN_ADDRESS, MIN_COLLATERAL_INCREASE, 0);
    }

    function test_deposit() public {
        vm.startPrank(DEPOSITOR1);
        bytes16 executorId = 0x11111111111111111111111111111111;

        vm.expectEmit(true, true, false, true);
        emit Deposit(executorId, DEPOSITOR1, 1 ether);

        collateral.deposit{value: 1 ether}(executorId);
        assertEq(collateral.collaterals(executorId), 1 ether);
        assertEq(collateral.executorToMiner(executorId), DEPOSITOR1);
        assertEq(address(collateral).balance, 1 ether);

        vm.expectEmit(true, true, false, true);
        emit Deposit(executorId, DEPOSITOR1, 1 ether);

        collateral.deposit{value: 1 ether}(executorId);
        assertEq(collateral.collaterals(executorId), 2 ether);
        assertEq(address(collateral).balance, 2 ether);
    }

    function test_revert_deposit_CanNotDepositWhenCollateralLessThanMinCollateralIncrease() public {
        bytes16 executorId = 0x11111111111111111111111111111111;
        vm.expectRevert(InsufficientAmount.selector);
        collateral.deposit{value: 0.5 ether}(executorId);
    }

    function test_revert_deposit_ExecutorNotOwned() public {
        bytes16 executorId = 0x11111111111111111111111111111111;
        
        // DEPOSITOR1 deposits first, becomes owner
        vm.prank(DEPOSITOR1);
        collateral.deposit{value: 1 ether}(executorId);
        
        // DEPOSITOR2 tries to deposit for same executor
        vm.prank(DEPOSITOR2);
        vm.expectRevert(ExecutorNotOwned.selector);
        collateral.deposit{value: 1 ether}(executorId);
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
        bytes16 executorId = 0x11111111111111111111111111111111;

        collateral.deposit{value: 1 ether}(executorId);
        uint256 expectedReclaimId = 1;

        vm.expectEmit(true, true, true, false);
        emit ReclaimProcessStarted(
            expectedReclaimId,
            executorId,
            DEPOSITOR1,
            1 ether,
            uint64(block.timestamp + DECISION_TIMEOUT),
            URL,
            URL_CONTENT_MD5_CHECKSUM
        );

        collateral.reclaimCollateral(executorId, URL, URL_CONTENT_MD5_CHECKSUM);

        verifyReclaim(expectedReclaimId, executorId, DEPOSITOR1, 1 ether, block.timestamp + DECISION_TIMEOUT);

        assertEq(collateral.collaterals(executorId), 1 ether);
        assertEq(address(collateral).balance, 1 ether);
    }

    function test_reclaim_CanReclaimPartialAmount() public {
        vm.startPrank(DEPOSITOR1);
        bytes16 executorId = 0x11111111111111111111111111111111;

        collateral.deposit{value: 2 ether}(executorId);

        // First reclaim - should take all available collateral (2 ether)
        collateral.reclaimCollateral(executorId, URL, URL_CONTENT_MD5_CHECKSUM);
        verifyReclaim(1, executorId, DEPOSITOR1, 2 ether, block.timestamp + DECISION_TIMEOUT);

        // Try second reclaim - should fail with AmountZero since all collateral is pending
        vm.expectRevert(AmountZero.selector);
        collateral.reclaimCollateral(executorId, URL, URL_CONTENT_MD5_CHECKSUM);

        assertEq(collateral.collaterals(executorId), 2 ether);
        assertEq(address(collateral).balance, 2 ether);
    }

    function test_reclaim_MultipleUsersCanStartReclaimProcess() public {
        bytes16 executorId1 = 0x11111111111111111111111111111111;
        bytes16 executorId2 = 0x22222222222222222222222222222222;

        vm.prank(DEPOSITOR1);
        collateral.deposit{value: 1 ether}(executorId1);
        vm.prank(DEPOSITOR2);
        collateral.deposit{value: 1 ether}(executorId2);

        vm.prank(DEPOSITOR1);
        collateral.reclaimCollateral(executorId1, URL, URL_CONTENT_MD5_CHECKSUM);
        vm.prank(DEPOSITOR2);
        collateral.reclaimCollateral(executorId2, URL, URL_CONTENT_MD5_CHECKSUM);

        uint256 expectedDenyTimeout = block.timestamp + DECISION_TIMEOUT;
        verifyReclaim(1, executorId1, DEPOSITOR1, 1 ether, expectedDenyTimeout);
        verifyReclaim(2, executorId2, DEPOSITOR2, 1 ether, expectedDenyTimeout);

        assertEq(address(collateral).balance, 2 ether);
    }

    function test_revert_CanNotReclaimZero() public {
        vm.startPrank(DEPOSITOR1);
        bytes16 executorId = 0x11111111111111111111111111111111;
        // Try to reclaim without any deposits - should fail with ExecutorNotOwned
        vm.expectRevert(ExecutorNotOwned.selector);
        collateral.reclaimCollateral(executorId, URL, URL_CONTENT_MD5_CHECKSUM);
    }

    function test_revert_reclaim_AmountZero() public {
        vm.startPrank(DEPOSITOR1);
        bytes16 executorId = 0x11111111111111111111111111111111;
        
        // Deposit and immediately reclaim all
        collateral.deposit{value: 1 ether}(executorId);
        collateral.reclaimCollateral(executorId, URL, URL_CONTENT_MD5_CHECKSUM);
        
        // Try to reclaim again - should fail with AmountZero since all is pending
        vm.expectRevert(AmountZero.selector);
        collateral.reclaimCollateral(executorId, URL, URL_CONTENT_MD5_CHECKSUM);
    }

    function test_revert_reclaim_ExecutorNotOwned() public {
        bytes16 executorId = 0x11111111111111111111111111111111;
        
        vm.prank(DEPOSITOR1);
        collateral.deposit{value: 1 ether}(executorId);
        
        // DEPOSITOR2 tries to reclaim DEPOSITOR1's collateral
        vm.prank(DEPOSITOR2);
        vm.expectRevert(ExecutorNotOwned.selector);
        collateral.reclaimCollateral(executorId, URL, URL_CONTENT_MD5_CHECKSUM);
    }


    function test_finalizeReclaim() public {
        vm.startPrank(DEPOSITOR1);
        bytes16 executorId = 0x11111111111111111111111111111111;
        collateral.deposit{value: 1 ether}(executorId);

        collateral.reclaimCollateral(executorId, URL, URL_CONTENT_MD5_CHECKSUM);
        skip(DECISION_TIMEOUT + 1);

        uint256 depositorBalanceBefore = DEPOSITOR1.balance;
        uint256 contractBalanceBefore = address(collateral).balance;

        vm.expectEmit(true, true, true, false);
        emit Reclaimed(1, executorId, DEPOSITOR1, 1 ether);
        vm.stopPrank();
        
        // Anyone can finalize
        collateral.finalizeReclaim(1);

        uint256 depositorBalanceAfter = DEPOSITOR1.balance;
        uint256 contractBalanceAfter = address(collateral).balance;

        // Verify balances and reclaim deletion
        assertEq(depositorBalanceAfter, depositorBalanceBefore + 1 ether);
        assertEq(contractBalanceAfter, contractBalanceBefore - 1 ether);
        // Executor ownership should be reset
        assertEq(collateral.executorToMiner(executorId), address(0));
    }

    function test_revert_finalizeReclaim_CanNotFinalizeUntilDenyTimeoutExpires() public {
        vm.startPrank(DEPOSITOR1);
        bytes16 executorId = 0x11111111111111111111111111111111;
        collateral.deposit{value: 2 ether}(executorId);

        collateral.reclaimCollateral(executorId, URL, URL_CONTENT_MD5_CHECKSUM);

        vm.expectRevert(BeforeDenyTimeout.selector);
        collateral.finalizeReclaim(1);
    }

    function test_denyReclaimRequest() public {
        vm.startPrank(DEPOSITOR1);
        bytes16 executorId = 0x11111111111111111111111111111111;
        collateral.deposit{value: 1 ether}(executorId);

        collateral.reclaimCollateral(executorId, URL, URL_CONTENT_MD5_CHECKSUM);
        vm.stopPrank();

        vm.prank(TRUSTEE);
        uint256 reclaimRequestId = 1;
        uint256 contractBalanceBefore = address(collateral).balance;

        vm.expectEmit(true, false, false, false);
        emit Denied(reclaimRequestId, URL, URL_CONTENT_MD5_CHECKSUM);
        collateral.denyReclaimRequest(reclaimRequestId, URL, URL_CONTENT_MD5_CHECKSUM);

        uint256 contractBalanceAfter = address(collateral).balance;
        // does not change contract balance
        assertEq(contractBalanceAfter, contractBalanceBefore);

        skip(DECISION_TIMEOUT + 1);
        vm.expectRevert(ReclaimNotFound.selector);
        collateral.finalizeReclaim(reclaimRequestId);
    }

    function test_revert_denyReclaimRequest_CanBeCalledOnlyByTrustee() public {
        vm.startPrank(DEPOSITOR1);
        bytes16 executorId = 0x11111111111111111111111111111111;
        collateral.deposit{value: 1 ether}(executorId);

        collateral.reclaimCollateral(executorId, URL, URL_CONTENT_MD5_CHECKSUM);

        vm.expectRevert(NotTrustee.selector);
        collateral.denyReclaimRequest(1, URL, URL_CONTENT_MD5_CHECKSUM);
    }

    function test_revert_denyReclaimRequest_CanNotBeCalledAfterDenyTimeoutExpires() public {
        vm.startPrank(DEPOSITOR1);
        bytes16 executorId = 0x11111111111111111111111111111111;
        collateral.deposit{value: 1 ether}(executorId);

        collateral.reclaimCollateral(executorId, URL, URL_CONTENT_MD5_CHECKSUM);
        skip(DECISION_TIMEOUT + 1);

        vm.stopPrank();
        vm.prank(TRUSTEE);
        vm.expectRevert(PastDenyTimeout.selector);
        collateral.denyReclaimRequest(1, URL, URL_CONTENT_MD5_CHECKSUM);
    }

    function test_slashCollateral_Partial() public {
        bytes16 executorId = 0x11111111111111111111111111111111;

        vm.prank(DEPOSITOR1);
        collateral.deposit{value: 2 ether}(executorId);

        uint256 collateralBeforeSlash = collateral.collaterals(executorId);
        uint256 contractBalanceBeforeSlash = address(collateral).balance;
        uint256 burnAddressBalanceBefore = BURN_ADDRESS.balance;

        vm.prank(TRUSTEE);
        vm.expectEmit(true, true, false, false);
        emit Slashed(executorId, DEPOSITOR1, 1 ether, SLASH_REASON_URL, URL_CONTENT_MD5_CHECKSUM);
        collateral.slashCollateral(executorId, 1 ether, SLASH_REASON_URL, URL_CONTENT_MD5_CHECKSUM);

        uint256 collateralAfterSlash = collateral.collaterals(executorId);
        assertEq(collateralAfterSlash, collateralBeforeSlash - 1 ether);

        uint256 contractBalanceAfterSlash = address(collateral).balance;
        assertEq(contractBalanceAfterSlash, contractBalanceBeforeSlash - 1 ether);
        
        uint256 burnAddressBalanceAfter = BURN_ADDRESS.balance;
        assertEq(burnAddressBalanceAfter, burnAddressBalanceBefore + 1 ether);
        
        // Executor ownership should remain since collateral > 0
        assertEq(collateral.executorToMiner(executorId), DEPOSITOR1);
    }

    function test_slashCollateral_Full() public {
        bytes16 executorId = 0x11111111111111111111111111111111;

        vm.prank(DEPOSITOR1);
        collateral.deposit{value: 1 ether}(executorId);

        vm.prank(TRUSTEE);
        collateral.slashCollateral(executorId, 1 ether, SLASH_REASON_URL, URL_CONTENT_MD5_CHECKSUM);

        assertEq(collateral.collaterals(executorId), 0);
        // Executor ownership should be reset when collateral reaches 0
        assertEq(collateral.executorToMiner(executorId), address(0));
    }

    function test_slashCollateral_ExceedsAvailable() public {
        bytes16 executorId = 0x11111111111111111111111111111111;

        vm.prank(DEPOSITOR1);
        collateral.deposit{value: 1 ether}(executorId);

        // Try to slash 2 ether when only 1 ether available
        vm.prank(TRUSTEE);
        collateral.slashCollateral(executorId, 2 ether, SLASH_REASON_URL, URL_CONTENT_MD5_CHECKSUM);

        // Should only slash the available amount (1 ether)
        assertEq(collateral.collaterals(executorId), 0);
        assertEq(BURN_ADDRESS.balance, 1 ether);
    }

    function test_revert_slashCollateral_CanBeCalledOnlyByTrustee() public {
        bytes16 executorId = 0x11111111111111111111111111111111;
        vm.prank(DEPOSITOR1);
        collateral.deposit{value: 2 ether}(executorId);

        vm.expectRevert(NotTrustee.selector);
        collateral.slashCollateral(executorId, 1 ether, SLASH_REASON_URL, URL_CONTENT_MD5_CHECKSUM);
    }

    function test_revert_slashCollateral_CanNotSlashZero() public {
        bytes16 executorId = 0x11111111111111111111111111111111;
        vm.prank(TRUSTEE);
        vm.expectRevert(AmountZero.selector);
        collateral.slashCollateral(executorId, 1 ether, SLASH_REASON_URL, URL_CONTENT_MD5_CHECKSUM);
    }
}
