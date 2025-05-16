#!/usr/bin/env python3

"""
Get Eligible Executors Script

This script allows users to retrieve the list of eligible executors (executors
with non-zero TAO in collateral and not slashed or penalized) for a given miner.
"""

import sys
import argparse
import uuid  # Add this import for UUID conversion
from celium_collateral_contracts.common import (
    load_contract_abi,
    get_web3_connection,
    get_account,
    validate_address_format,
)


class GetEligibleExecutorsError(Exception):
    """Raised when fetching eligible executors fails."""
    pass


def get_eligible_executors(w3, contract_address, miner_address, executor_uuids):
    """Get the list of eligible executors for a miner from the contract.

    Args:
        w3: Web3 instance
        contract_address: Address of the contract
        miner_address: Address of the miner to fetch executors for
        executor_uuids: List of executor UUIDs to check eligibility

    Returns:
        list: List of human-readable UUID strings for the given miner

    Raises:
        GetEligibleExecutorsError: If the contract call fails for any reason
    """
    validate_address_format(contract_address)
    validate_address_format(miner_address)

    contract_abi = load_contract_abi()
    contract = w3.eth.contract(address=contract_address, abi=contract_abi)

    # Convert executor_uuids from strings to bytes16
    executor_uuids_bytes = [uuid.UUID(uuid_str).bytes for uuid_str in executor_uuids]

    try:
        executors = contract.functions.getEligibleExecutors(miner_address, executor_uuids_bytes).call({'gas': 3000000})
        # Convert bytes16 to UUID strings
        readable_executors = [str(uuid.UUID(bytes=executor)) for executor in executors]
        return readable_executors
    except Exception as e:
        print("Error calling getEligibleExecutors:", str(e))
        raise GetEligibleExecutorsError(f"Error getting eligible executors for miner {miner_address}: {str(e)}")


def main():
    parser = argparse.ArgumentParser(
        description="Get the list of eligible executors for a specific miner on the Collateral contract"
    )
    parser.add_argument(
        "--contract-address", help="Address of the deployed Collateral contract"
    )
    parser.add_argument(
        "--miner-address", help="Address of the miner to fetch eligible executors for"
    )
    parser.add_argument(
        "--executor-uuids",
        help="Comma-separated list of executor UUIDs to check eligibility",
    )
    parser.add_argument("--keystr", help="Keystring of the account to use")
    parser.add_argument("--network", default="finney")

    args = parser.parse_args()

    w3 = get_web3_connection(args.network)
    account = get_account(args.keystr)  # You may not need to use this for reading data, but it's useful for connection checks

    try:
        executor_uuids = args.executor_uuids.split(",")  # Keep UUIDs as strings
        executors = get_eligible_executors(
            w3=w3,
            contract_address=args.contract_address,
            miner_address=args.miner_address,
            executor_uuids=executor_uuids,  # Pass UUID strings
        )

        print(f"Successfully fetched eligible executors for miner {args.miner_address}")
        if not executors:
            print("No eligible executors found.")
        else:
            print("Eligible Executors:", ",".join(executors))  # Join list into a single string

    except GetEligibleExecutorsError as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
