#!/usr/bin/env python3

"""
Update Validator for Miner Script

This script updates the validator for a specific miner in the Collateral smart contract.
"""

import argparse
import sys
from common import (
    load_contract_abi,
    get_web3_connection,
    get_account,
    validate_address_format,
    build_and_send_transaction,
    wait_for_receipt,
    get_revert_reason,
)


def update_validator_for_miner(w3, account, contract_address, miner_address, new_validator):
    """Update the validator for a specific miner.

    Args:
        w3: Web3 instance
        account: Account to use for the transaction
        contract_address: Address of the Collateral contract
        miner_address: Address of the miner
        new_validator: Address of the new validator

    Returns:
        dict: Transaction receipt
    """
    validate_address_format(contract_address)
    validate_address_format(miner_address)
    validate_address_format(new_validator)

    contract_abi = load_contract_abi()
    contract = w3.eth.contract(address=contract_address, abi=contract_abi)

    tx_hash = build_and_send_transaction(
        w3,
        contract.functions.updateValidatorForMiner(miner_address, new_validator),
        account,
    )

    receipt = wait_for_receipt(w3, tx_hash)
    if receipt["status"] == 0:
        revert_reason = get_revert_reason(w3, tx_hash, receipt["blockNumber"])
        raise Exception(f"Transaction failed. Revert reason: {revert_reason}")

    return receipt


def main():
    parser = argparse.ArgumentParser(
        description="Update the validator for a specific miner."
    )
    parser.add_argument(
        "--contract-address", required=True, help="Address of the Collateral contract"
    )
    parser.add_argument(
        "--miner-address", required=True, help="Address of the miner"
    )
    parser.add_argument(
        "--new-validator", required=True, help="Address of the new validator"
    )
    parser.add_argument("--keystr", required=True, help="Keystring of the account to use")
    parser.add_argument("--network", default="finney", help="The Subtensor Network to connect to.")

    args = parser.parse_args()

    w3 = get_web3_connection(args.network)
    account = get_account(args.keystr)

    try:
        receipt = update_validator_for_miner(
            w3, account, args.contract_address, args.miner_address, args.new_validator
        )
        print(f"Validator updated successfully. Transaction hash: {receipt['transactionHash'].hex()}")
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
