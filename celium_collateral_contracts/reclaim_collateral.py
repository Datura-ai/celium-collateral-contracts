#!/usr/bin/env python3

"""
Collateral Reclaim Script

This script allows users to initiate the process of reclaiming their collateral
from the Collateral smart contract. It handles the creation of reclaim requests
with associated URLs for verification purposes.
"""

import sys
import argparse
from uuid import UUID
from celium_collateral_contracts.common import (
    load_contract_abi,
    get_web3_connection,
    get_account,
    validate_address_format,
    build_and_send_transaction,
    wait_for_receipt,
    calculate_md5_checksum,
    get_revert_reason,
)
import asyncio


class ReclaimCollateralError(Exception):
    """Exception raised when there is an error during the collateral reclaim process."""
    pass


async def reclaim_collateral(
    w3,
    account,
    contract_address,
    url,
    executor_uuid,
):
    """Reclaim collateral from the contract.

    Args:
        w3 (Web3): Web3 instance
        account: The account to use for the transaction
        contract_address (str): Address of the collateral contract
        url (str): URL for reclaim information
        executor_uuid (str): Executor UUID for the reclaim operation

    Returns:
        dict: Transaction receipt with reclaim event details

    Raises:
        Exception: If the transaction fails
    """
    contract_abi = load_contract_abi()
    contract = w3.eth.contract(address=contract_address, abi=contract_abi)

    # Calculate MD5 checksum if URL is valid
    md5_checksum = "0" * 32
    if url.startswith(("http://", "https://")):
        print("Calculating MD5 checksum of URL content...", file=sys.stderr)
        md5_checksum = await calculate_md5_checksum(url)
        print(f"MD5 checksum: {md5_checksum}", file=sys.stderr)

    executor_uuid_bytes = UUID(executor_uuid).bytes

    tx_hash = build_and_send_transaction(
        w3,
        contract.functions.reclaimCollateral(            
            executor_uuid_bytes,
            url,
            bytes.fromhex(md5_checksum)
        ),
        account,
        gas_limit=200000,  # Higher gas limit for this function
    )

    receipt = wait_for_receipt(w3, tx_hash)
    if receipt['status'] == 0:
        revert_reason = get_revert_reason(w3, tx_hash, receipt['blockNumber'])
        raise ReclaimCollateralError(f"Transaction failed for reclaiming collateral. Revert reason: {revert_reason}")
    reclaim_event = contract.events.ReclaimProcessStarted().process_receipt(
        receipt,
    )[0]

    print("Event details:")
    print(f"  Reclaim ID: {reclaim_event['args']['reclaimRequestId']}")
    print(f"  Executor ID: {reclaim_event['args']['executorId']}")
    print(f"  Miner Address: {reclaim_event['args']['miner']}")
    print(
        f"  Amount: "
        f"{w3.from_wei(reclaim_event['args']['amount'], 'ether')} TAO",
    )
    print(
        f"  Expiration Time: {reclaim_event['args']['expirationTime']}")
    print(f"  URL: {reclaim_event['args']['url']}")
    print(
        f"  URL Content MD5: "
        f"{reclaim_event['args']['urlContentMd5Checksum'].hex()}",
    )
    print(
        f"  Transaction hash: {receipt['transactionHash'].hex()}")
    print(f"  Block number: {receipt['blockNumber']}")

    return receipt, reclaim_event


async def main():
    parser = argparse.ArgumentParser(
        description="Initiate the process of reclaiming collateral."
    )
    parser.add_argument(
        "--contract-address",
        required=True,
        help="Address of the collateral contract"
    )
    parser.add_argument(
        "--url",
        required=True,
        help="URL for reclaim information"
    )
    parser.add_argument("--private-key", help="Private key of the account to use")
    parser.add_argument(
        "--network",
        default="finney",
        help="The Subtensor Network to connect to.",
    )
    parser.add_argument(
        "--executor-uuid",
        help="Executor UUID for the reclaim operation"
    )

    args = parser.parse_args()

    validate_address_format(args.contract_address)

    w3 = get_web3_connection(args.network)
    account = get_account(args.private_key)

    try:
        receipt, event = await reclaim_collateral(
            w3, account, args.contract_address, args.url, args.executor_uuid
        )
    except Exception as e:
        print(f"Error during collateral reclaim: {str(e)}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
