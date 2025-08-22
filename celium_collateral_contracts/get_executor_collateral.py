#!/usr/bin/env python3
"""
Executor Collateral Query Tool

This script allows users to query the collateral amount for a specific miner and executor UUID
in a given smart contract. It connects to a blockchain network, validates
the provided addresses, and retrieves the collateral information.

The script will output the collateral amount in TAO (the native token).
"""
import argparse
import sys
import asyncio
from celium_collateral_contracts.common import (
    get_web3_connection,
    get_executor_collateral,
    validate_address_format,
    get_miner_address_of_executor
)

async def main():
    parser = argparse.ArgumentParser(
        description="Query the collateral amount for a specific miner and executor UUID in a smart contract"
    )
    parser.add_argument(
        "--contract-address",
        required=True,
        help="The address of the smart contract"
    )
    parser.add_argument(
        "--executor-uuid",
        required=True,
        help="The UUID of the executor (as a string or hex)"
    )
    parser.add_argument(
        "--network",
        default="finney",
        help="The Subtensor Network to connect to.",
    )
    args = parser.parse_args()
    validate_address_format(args.contract_address)
    w3 = get_web3_connection(args.network)
    collateral = await get_executor_collateral(w3, args.contract_address, args.executor_uuid)
    miner_address = await get_miner_address_of_executor(w3, args.contract_address, args.executor_uuid)

    print(
        f"Collateral for miner {miner_address}, executor {args.executor_uuid}: {collateral} TAO"
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1) 