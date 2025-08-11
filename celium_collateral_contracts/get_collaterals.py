"""
Collateral Retrieval Script

This script retrieves and displays collateral information for miners who have
deposited within a specified block range. It aggregates deposit events and
calculates the current collateral amounts for each miner.
"""
import asyncio
import argparse
import csv
import sys
from collections import defaultdict
from celium_collateral_contracts.common import load_contract_abi, get_web3_connection, get_executor_collateral
from dataclasses import dataclass


@dataclass
class DepositEvent:
    """Represents a Deposit event emitted by the Collateral contract."""

    account: str
    miner: str
    executor_uuid: str
    amount: int
    block_number: int
    transaction_hash: str


async def get_deposit_events(w3, contract_address, block_num_low, block_num_high):
    """Fetch all Deposit events emitted by the Collateral contract within a block range.

    Args:
        w3 (Web3): Web3 instance to use for blockchain interaction
        contract_address (str): The address of the deployed Collateral contract
        block_num_low (int): The starting block number (inclusive)
        block_num_high (int): The ending block number (inclusive)

    Returns:
        list[DepositEvent]: List of Deposit events
    """
    contract_abi = load_contract_abi()

    contract = w3.eth.contract(address=contract_address, abi=contract_abi)

    checksum_address = w3.to_checksum_address(contract_address)

    event_signature = "Deposit(bytes16,address,uint256)"
    event_topic = w3.keccak(text=event_signature).hex()

    filter_params = {
        "fromBlock": hex(block_num_low),
        "toBlock": hex(block_num_high),
        "address": checksum_address,
        "topics": [event_topic]
    }

    logs = w3.eth.get_logs(filter_params)

    formatted_events = []
    for log in logs:
        # Extract miner address from topics[2] (indexed)
        miner_address = "0x" + log["topics"][2].hex()[-40:]
        miner = w3.to_checksum_address(miner_address)

        decoded_event = contract.events.Deposit().process_log(log)

        formatted_events.append(
            DepositEvent(
                account=miner,  # For backward compatibility, use miner as account
                miner=miner,
                executor_uuid=decoded_event['args']['executorId'].hex(),
                amount=decoded_event['args']['amount'],
                block_number=log["blockNumber"],
                transaction_hash=log["transactionHash"].hex(),
            )
        )

    return formatted_events


async def main():
    parser = argparse.ArgumentParser(
        description="Get collaterals for miners who deposited in a given block range"
    )
    parser.add_argument(
        "--contract-address", required=True, help="The address of the deployed Collateral contract"
    )
    parser.add_argument(
        "--block-start", required=True, type=int, help="Starting block number (inclusive)"
    )
    parser.add_argument(
        "--block-end", required=True, type=int, help="Ending block number (inclusive)"
    )
    parser.add_argument("--network", default="finney", help="The Subtensor Network to connect to.")
    args = parser.parse_args()

    w3 = get_web3_connection(args.network)

    deposit_events = await get_deposit_events(
        w3, args.contract_address, args.block_start, args.block_end
    )

    cumulative_deposits = defaultdict(int)
    for event in deposit_events:
        cumulative_deposits[event.executorId] += event.amount

    executor_ids = set(event.executorId for event in deposit_events)
    results = []
    for executor_id in executor_ids:
        collateral = get_executor_collateral(
            w3, args.contract_address, executor_id)
        results.append(
            [executor_id, w3.from_wei(cumulative_deposits[executor_id], 'ether'), w3.from_wei(collateral, 'ether')])

    writer = csv.writer(sys.stdout)
    writer.writerow(
        ["executor_id", "cumulative_amount_of_deposits_tao", "total_collateral_amount_tao"]
    )
    writer.writerows(results)

    print(f"Found {len(results)} miners with deposits", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())