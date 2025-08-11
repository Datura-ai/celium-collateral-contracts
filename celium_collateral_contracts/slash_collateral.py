#!/usr/bin/env python3

"""
Collateral Slashing Script

This script allows trustees to slash collateral from miners who have violated
protocol rules. It handles the creation of slashing requests with associated
URLs for verification purposes.
"""

import sys
import asyncio
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


class SlashCollateralError(Exception):
    """Custom exception for errors that occur during collateral slashing operations."""
    pass


async def slash_collateral(
    w3,
    account,
    contract_address,
    executor_uuid,
    slash_amount_tao,
    url,
):
    """Slash collateral from a miner.

    Args:
        w3 (Web3): Web3 instance
        account: The account to use for the transaction
        contract_address (str): Address of the collateral contract
        executor_uuid (str): Executor UUID for the slashing operation
        slash_amount_tao (float): Amount to slash in TAO
        url (str): URL containing information about the slash

    Returns:
        dict: Transaction receipt with slash event details

    Raises:
        Exception: If the transaction fails
    """
    contract_abi = load_contract_abi()
    contract = w3.eth.contract(address=contract_address, abi=contract_abi)

    # Calculate MD5 checksum if URL is valid
    md5_checksum = "0" * 32
    if url.startswith(("http://", "https://")):
        print("Calculating MD5 checksum of URL content...", file=sys.stderr)
        md5_checksum = calculate_md5_checksum(url)
        print(f"MD5 checksum: {md5_checksum}", file=sys.stderr)

    executor_uuid_bytes = UUID(executor_uuid).bytes
    slash_amount_wei = w3.to_wei(slash_amount_tao, "ether")

    tx_hash = build_and_send_transaction(
        w3,
        contract.functions.slashCollateral(
            executor_uuid_bytes,
            slash_amount_wei,
            url,
            bytes.fromhex(md5_checksum),
        ),
        account,
        gas_limit=200000,  # Higher gas limit for this function
    )

    receipt = wait_for_receipt(w3, tx_hash)
    if receipt['status'] == 0:
        revert_reason = get_revert_reason(w3, tx_hash, receipt['blockNumber'])
        raise SlashCollateralError(f"Transaction failed for slashing collateral. Revert reason: {revert_reason}")
    slash_event = contract.events.Slashed().process_receipt(receipt)[0]

    return receipt, slash_event


async def main():
    parser = argparse.ArgumentParser(
        description="Slash collateral from a miner."
    )
    parser.add_argument(
        "--contract-address",
        required=True,
        help="Address of the collateral contract"
    )
    parser.add_argument(
        "--executor-uuid",
        required=True,
        help="Executor UUID for the slashing operation"
    )
    parser.add_argument(
        "--slash-amount",
        type=float,
        required=True,
        help="Amount to slash in TAO"
    )
    parser.add_argument(
        "--url",
        required=True,
        help="URL containing information about the slash"
    )
    parser.add_argument("--private-key", help="Private key of the account to use")
    parser.add_argument("--network", default="finney", help="The Subtensor Network to connect to.")

    args = parser.parse_args()

    validate_address_format(args.contract_address)

    w3 = get_web3_connection(args.network)
    account = get_account(args.private_key)

    try:
        receipt, event = await slash_collateral(
            w3,
            account,
            args.contract_address,
            args.executor_uuid,
            args.slash_amount,
            args.url
        )

        print(f"Successfully slashed for executor {args.executor_uuid}")
        print("Event details:")
        print(f"  Executor ID: {event['args']['executorId']}")
        print(f"  Miner address: {event['args']['miner']}")
        print(
            f"  Amount: "
            f"{w3.from_wei(event['args']['amount'], 'ether')} TAO",
        )
        print(f"  URL: {event['args']['url']}")
        print(
            f"  URL Content MD5: "
            f"{event['args']['urlContentMd5Checksum'].hex()}",
        )
        print(
            f"  Transaction hash: {receipt['transactionHash'].hex()}")
        print(f"  Block number: {receipt['blockNumber']}")
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
