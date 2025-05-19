#!/usr/bin/env python3

"""
Get Validator of Miner Script

This script retrieves the validator associated with a specific miner from the Collateral smart contract.
"""

import argparse
import sys
from celium_collateral_contracts.common import (
    load_contract_abi,
    get_web3_connection,
    validate_address_format,
)


def get_validator_of_miner(w3, contract_address, miner_address):
    """Retrieve the validator associated with a specific miner.

    Args:
        w3: Web3 instance
        contract_address: Address of the Collateral contract
        miner_address: Address of the miner

    Returns:
        str: Validator address
    """
    validate_address_format(contract_address)
    validate_address_format(miner_address)

    contract_abi = load_contract_abi()
    contract = w3.eth.contract(address=contract_address, abi=contract_abi)

    return contract.functions.validatorOfMiner(miner_address).call()


def main():
    parser = argparse.ArgumentParser(
        description="Retrieve the validator associated with a specific miner."
    )
    parser.add_argument(
        "--contract-address", required=True, help="Address of the Collateral contract"
    )
    parser.add_argument(
        "--miner-address", required=True, help="Address of the miner"
    )
    parser.add_argument("--network", default="finney", help="The Subtensor Network to connect to.")

    args = parser.parse_args()

    w3 = get_web3_connection(args.network)

    try:
        validator = get_validator_of_miner(w3, args.contract_address, args.miner_address)
        print(f"Validator for miner {args.miner_address}: {validator}")
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
