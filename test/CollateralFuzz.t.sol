// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.28;

import {CollateralTestBase} from "./CollateralTestBase.sol";

contract CollateralTest is CollateralTestBase {
    receive() external payable {}

    function testFuzz_deposit(uint256 amount, bytes16 executorId) public {
        // leave some ether to cover gas fees
        vm.assume((amount >= MIN_COLLATERAL_INCREASE) && (amount < address(this).balance - 1 ether));
        vm.expectEmit(true, true, false, true);
        emit Deposit(executorId, address(this), amount);

        collateral.deposit{value: amount}(executorId);
        assertEq(collateral.collaterals(executorId), amount);
        assertEq(collateral.executorToMiner(executorId), address(this));
        assertEq(address(collateral).balance, amount);
    }

    function testFuzz_reclaim(uint256 amount, bytes16 executorId) public {
        vm.assume((amount >= MIN_COLLATERAL_INCREASE) && (amount < address(this).balance - 1 ether));

        collateral.deposit{value: amount}(executorId);

        vm.expectEmit(true, true, true, false);
        emit ReclaimProcessStarted(
            1, executorId, address(this), amount, uint64(block.timestamp) + DECISION_TIMEOUT, URL, URL_CONTENT_MD5_CHECKSUM
        );

        collateral.reclaimCollateral(executorId, URL, URL_CONTENT_MD5_CHECKSUM);
        
        verifyReclaim(1, executorId, address(this), amount, block.timestamp + DECISION_TIMEOUT);
    }

    function testFuzz_revert_reclaim_AmountZero(uint256 amount) public {
        vm.assume((amount >= MIN_COLLATERAL_INCREASE) && (amount < address(this).balance - 1 ether));
        bytes16 executorId = bytes16(uint128(amount % type(uint128).max)); // Ensure executorId is non-zero
        vm.assume(executorId != bytes16(0)); // Make sure executorId is not zero
        
        // Deposit first to establish ownership
        collateral.deposit{value: amount}(executorId);
        
        // Reclaim all collateral
        collateral.reclaimCollateral(executorId, URL, URL_CONTENT_MD5_CHECKSUM);
        
        // Try to reclaim again - should fail with AmountZero since all is under pending reclaim
        vm.expectRevert(AmountZero.selector);
        collateral.reclaimCollateral(executorId, URL, URL_CONTENT_MD5_CHECKSUM);
    }

    function testFuzz_denyReclaimRequest(uint256 amount, uint64 decisionTimeout, bytes16 executorId) public {
        vm.assume((amount >= MIN_COLLATERAL_INCREASE) && (amount < address(this).balance - 1 ether));
        vm.assume(decisionTimeout > 0 && decisionTimeout <= DECISION_TIMEOUT);

        collateral.deposit{value: amount}(executorId);
        collateral.reclaimCollateral(executorId, URL, URL_CONTENT_MD5_CHECKSUM);

        skip(decisionTimeout);

        vm.expectEmit(true, false, false, false);
        emit Denied(1, URL, URL_CONTENT_MD5_CHECKSUM);

        vm.prank(TRUSTEE);
        collateral.denyReclaimRequest(1, URL, URL_CONTENT_MD5_CHECKSUM);

        // check that the reclaim request is denied
        // make sure finalizeReclaim can't be called on the reclaim request
        skip(DECISION_TIMEOUT);
        vm.expectRevert(ReclaimNotFound.selector);
        collateral.finalizeReclaim(1);
    }

    function testFuzz_slash(uint256 amount, uint256 slashAmount) public {
        vm.assume((amount >= MIN_COLLATERAL_INCREASE) && (amount < address(this).balance / 2));
        vm.assume(slashAmount > 0 && slashAmount <= amount);

        bytes16 executorId = 0x11111111111111111111111111111111;

        collateral.deposit{value: amount}(executorId);

        uint256 expectedSlashAmount = slashAmount > amount ? amount : slashAmount;
        
        vm.expectEmit(true, true, false, false);
        emit Slashed(executorId, address(this), expectedSlashAmount, SLASH_REASON_URL, URL_CONTENT_MD5_CHECKSUM);

        vm.prank(TRUSTEE);
        collateral.slashCollateral(executorId, slashAmount, SLASH_REASON_URL, URL_CONTENT_MD5_CHECKSUM);

        assertEq(collateral.collaterals(executorId), amount - expectedSlashAmount);
        assertEq(address(collateral).balance, amount - expectedSlashAmount);
        assertEq(BURN_ADDRESS.balance, expectedSlashAmount);
    }

    function testFuzz_slashMoreThanAvailable(uint256 amount) public {
        vm.assume((amount >= MIN_COLLATERAL_INCREASE) && (amount < address(this).balance / 2));

        bytes16 executorId = bytes16(0);

        collateral.deposit{value: amount}(executorId);

        // Try to slash more than available
        uint256 slashAmount = amount * 2;
        
        vm.expectEmit(true, true, false, false);
        emit Slashed(executorId, address(this), amount, SLASH_REASON_URL, URL_CONTENT_MD5_CHECKSUM);

        vm.prank(TRUSTEE);
        collateral.slashCollateral(executorId, slashAmount, SLASH_REASON_URL, URL_CONTENT_MD5_CHECKSUM);

        // Should only slash the available amount
        assertEq(collateral.collaterals(executorId), 0);
        assertEq(address(collateral).balance, 0);
        assertEq(BURN_ADDRESS.balance, amount);
    }
}
