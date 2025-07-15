"""
Common Utilities for Collateral Management

This module provides shared functionality for interacting with the Collateral smart contract.
It includes utilities for:
- Loading contract ABIs
- Establishing Web3 connections
- Managing accounts and transactions
- Retrieving and processing blockchain events
- Validating addresses and calculating checksums
"""

import os
import pathlib
import sys
import json
import hashlib
import uuid

import bittensor
import requests
from web3 import Web3
from web3.eth import AsyncEth
from web3.contract import Contract
from eth_account import Account
from web3.exceptions import ContractLogicError


def validate_address_format(address):
    """Validate if the given address is a valid Ethereum address."""
    if not Web3.is_address(address):
        raise ValueError("Invalid address")


def load_contract_abi():
    """Load the contract ABI from the artifacts file."""
    abi_file = pathlib.Path(__file__).parent / "abi.json"
    return json.loads(abi_file.read_text())


RPC_URLS = {
    "local": "http://127.0.0.1:9944",
    # "finney": "https://entrypoint-finney.opentensor.ai",
    "test": "https://test.finney.opentensor.ai",
    "finney": "https://lite.chain.opentensor.ai",
}


def get_web3_connection(network: str, rpc_url: str | None = None) -> Web3:
    """Get Web3 connection for the specified network."""
    if rpc_url:
        network_url = rpc_url
    else:
        if network in RPC_URLS:
            network_url = RPC_URLS[network]
        else:
            _, network_url = bittensor.utils.determine_chain_endpoint_and_network(network)

    w3 = Web3(
        Web3.AsyncHTTPProvider(network_url),
        modules={"eth": (AsyncEth,)},
        middlewares=[],
    )
    # if not w3.is_connected():
    #     raise ConnectionError("Failed to connect to the network")
    return w3


def get_contract(w3: Web3, contract_address: str) -> Contract:
    validate_address_format(contract_address)

    contract_abi = load_contract_abi()
    return w3.eth.contract(address=contract_address, abi=contract_abi)


def get_account(keystr=None):
    """Get the account from the keyfile or PRIVATE_KEY environment variable."""
    if keystr:
        private_key = keystr
    else:
        private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        raise KeyError("PRIVATE_KEY environment variable not set")
    return Account.from_key(private_key)


async def build_and_send_transaction(
    w3, function_call, account, gas_limit=100000, value=0
):
    """Build, sign and send a transaction.

    Args:
        w3: Web3 instance
        function_call: Contract function call to execute
        account: Account to send transaction from
        gas_limit: Maximum gas to use for the transaction
        value: Amount of ETH to send with the transaction (in Wei)
    """
    transaction = await function_call.build_transaction(
        {
            "from": account.address,
            "nonce": await w3.eth.get_transaction_count(account.address),
            "gas": gas_limit,
            "gasPrice": await w3.eth.gas_price,
            "chainId": await w3.eth.chain_id,
            "value": value,
        }
    )

    signed_txn = w3.eth.account.sign_transaction(transaction, account.key)

    raw_tx = getattr(signed_txn, "rawTransaction", None) or getattr(signed_txn, "raw_transaction", None)

    if raw_tx is None:
        raise AttributeError("Signed transaction has neither 'rawTransaction' nor 'raw_transaction'.")

    tx_hash = await w3.eth.send_raw_transaction(raw_tx)
    print(f"Transaction sent: {tx_hash.hex()}", file=sys.stderr)
    return tx_hash


async def wait_for_receipt(w3, tx_hash, timeout=300, poll_latency=2):
    """Wait for transaction receipt and return it."""
    return await w3.eth.wait_for_transaction_receipt(tx_hash, timeout, poll_latency)


def calculate_md5_checksum(url):
    """Calculate MD5 checksum of the content at the given URL.

    Args:
        url (str): The URL to fetch content from.

    Returns:
        str: The MD5 checksum of the content.

    Raises:
        SystemExit: If there's an error fetching the URL content.
    """
    response = requests.get(url)
    response.raise_for_status()
    return hashlib.md5(response.content).hexdigest()


async def get_revert_reason(w3, tx_hash, block_number):
    """Returns the custom Solidity error name for a failed transaction, or 'Could not parse error' if not decodable.
    If the error is SlashAmountTooLarge, also prints its parameters.
    """
    tx = await w3.eth.get_transaction(tx_hash)
    try:
        await w3.eth.call({
            'to': tx['to'],
            'from': tx['from'],
            'data': tx['input'],
            'value': tx['value'],
        }, block_identifier=block_number)
    except ContractLogicError as e:
        import re
        msg = str(e)
        hex_pattern = re.compile(r'(0x[a-fA-F0-9]{8,})')
        match = hex_pattern.search(msg)
        revert_data = match.group(1) if match else None
        if revert_data and len(revert_data) >= 10:
            selector = revert_data[:10]
            contract_abi = load_contract_abi()
            for item in contract_abi:
                if item.get('type') == 'error':
                    sig = item['name'] + '(' + ','.join([input['type'] for input in item.get('inputs', [])]) + ')'
                    import eth_utils
                    selector_bytes = eth_utils.keccak(text=sig)[:4]
                    selector_hex = '0x' + selector_bytes.hex()
                    if selector == selector_hex:
                        # If error is SlashAmountTooLarge, decode parameters
                        return item['name']
        return "Could not parse error"
    return "Could not parse error"


async def get_executor_collateral(w3: Web3, contract: Contract, executor_uuid: uuid.UUID | str):
    """Query the collateral amount for a given miner and executor UUID."""
    # executor_uuid must be bytes16
    if isinstance(executor_uuid, str):
        import uuid
        try:
            # Try to parse as UUID string
            uuid_bytes = uuid.UUID(executor_uuid).bytes
        except Exception:
            # If not a UUID, try to decode as hex
            uuid_bytes = bytes.fromhex(executor_uuid.replace('0x', ''))
        # Pad or trim to 16 bytes
        uuid_bytes = uuid_bytes[:16] if len(uuid_bytes) > 16 else uuid_bytes.ljust(16, b'\0')
    else:
        uuid_bytes = executor_uuid
    executor_collateral = await contract.functions.collaterals(uuid_bytes).call()
    return w3.from_wei(executor_collateral, "ether")


async def get_miner_address_of_executor(contract: Contract, executor_uuid: uuid.UUID | str):
    """Query the collateral amount for a given miner and executor UUID."""
    # executor_uuid must be bytes16
    if isinstance(executor_uuid, str):
        import uuid
        try:
            # Try to parse as UUID string
            uuid_bytes = uuid.UUID(executor_uuid).bytes
        except Exception:
            # If not a UUID, try to decode as hex
            uuid_bytes = bytes.fromhex(executor_uuid.replace('0x', ''))
        # Pad or trim to 16 bytes
        uuid_bytes = uuid_bytes[:16] if len(uuid_bytes) > 16 else uuid_bytes.ljust(16, b'\0')
    else:
        uuid_bytes = executor_uuid
    miner_address = await contract.functions.executorToMiner(uuid_bytes).call()
    return miner_address
