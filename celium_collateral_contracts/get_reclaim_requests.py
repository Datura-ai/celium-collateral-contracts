#!/usr/bin/env python3

"""
Reclaim Request Retrieval Script

This script retrieves and displays information about reclaim requests from the
Collateral smart contract. It fetches ReclaimProcessStarted events within a
specified block range and provides details about each reclaim request.
"""
import asyncio
import sys
import csv
import argparse
from dataclasses import dataclass
from celium_collateral_contracts.common import get_web3_connection, load_contract_abi
import uuid
import datetime


@dataclass
class ReclaimProcessStartedEvent:
    """Represents a ReclaimProcessStarted event emitted by the Collateral contract."""

    reclaim_request_id: int
    amount: int
    expiration_time: str
    url: str
    url_content_md5_checksum: str
    block_number: int
    executor_uuid: str

@dataclass
class ReclaimRequest:
    """Represents a Reclaim."""

    reclaim_request_id: int
    executor_uuid: str
    miner: str
    amount: int
    expiration_time: str

async def get_reclaim_process_started_events(
    w3, contract_address, block_num_low, block_num_high
):
    """Fetch all ReclaimProcessStarted events emitted by the Collateral contract within a block range.

    Args:
        w3 (Web3): Web3 instance to use for blockchain interaction
        contract_address (str): The address of the deployed Collateral contract
        block_num_low (int): The starting block number (inclusive)
        block_num_high (int): The ending block number (inclusive)

    Returns:
        list[ReclaimProcessStartedEvent]: List of ReclaimProcessStarted events
    """
    contract_abi = load_contract_abi()

    contract = w3.eth.contract(address=contract_address, abi=contract_abi)

    checksum_address = w3.to_checksum_address(contract_address)
    
    event_signature = "ReclaimProcessStarted(uint256,bytes16,address,uint256,uint64,string,bytes16)"
    event_topic = w3.keccak(text=event_signature).hex()

    filter_params = {
        "fromBlock": hex(block_num_low),
        "toBlock": hex(block_num_high),
        "address": checksum_address,
        "topics": [
            event_topic,  # Event signature topic
            None,  # reclaimRequestId (indexed)
            None,  # account (indexed)
        ]
    }
    logs = w3.eth.get_logs(filter_params)
    def get_reclaim_by_id(reclaim_id):
        """Fetch reclaim information using reclaim_id."""
        reclaim = contract.functions.reclaims(reclaim_id).call()
        return {
            "miner": reclaim[1],
            "amount": float(w3.from_wei(reclaim[2], "ether")),
            "denyTimeout": datetime.datetime.utcfromtimestamp(reclaim[3]).strftime('%Y-%m-%d %H:%M:%S UTC'),
            "executorUuid": reclaim[0].hex(),
        }

    formatted_events = []
    for log in logs:
        reclaim_request_id = int(log["topics"][1].hex(), 16)

        decoded_event = contract.events.ReclaimProcessStarted().process_log(log)

        reclaim_info = get_reclaim_by_id(reclaim_request_id)
        # Convert executorUuid hex string to bytes before creating UUID
        executor_uuid_bytes = bytes.fromhex(reclaim_info["executorUuid"])
        formatted_events.append(
            ReclaimProcessStartedEvent(
                reclaim_request_id=reclaim_request_id,
                amount=reclaim_info["amount"],
                expiration_time=reclaim_info["denyTimeout"],
                executor_uuid=str(uuid.UUID(bytes=executor_uuid_bytes)),
                url=decoded_event['args']['url'],
                url_content_md5_checksum=decoded_event['args']['urlContentMd5Checksum'].hex(),
                block_number=log["blockNumber"],
            ))

    return formatted_events


async def main():
    parser = argparse.ArgumentParser(
        description="Fetch ReclaimProcessStarted events from Collateral contract")
    parser.add_argument(
        "--contract-address", required=True, help="Address of the deployed Collateral contract"
    )
    parser.add_argument(
        "--block-start", required=True, type=int, help="Starting block number (inclusive)"
    )
    parser.add_argument(
        "--block-end", required=True, type=int, help="Ending block number (inclusive)"
    )
    parser.add_argument(
        "--network",
        default="finney")
    
    args = parser.parse_args()

    w3 = get_web3_connection(args.network)
    events = await get_reclaim_process_started_events(
        w3, args.contract_address, args.block_start, args.block_end
    )

    fieldnames = [
        "reclaim_request_id",
        "amount",
        "expiration_time",
        "url",
        "url_content_md5_checksum",
        "block_number",
        "executor_uuid"
    ]

    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()

    for event in events:
        writer.writerow(
            {
                "reclaim_request_id": event.reclaim_request_id,
                "amount": event.amount,
                "expiration_time": event.expiration_time,
                "url": event.url,
                "url_content_md5_checksum": event.url_content_md5_checksum,
                "block_number": event.block_number,
                "executor_uuid": event.executor_uuid
            }
        )


if __name__ == "__main__":
    asyncio.run(main())