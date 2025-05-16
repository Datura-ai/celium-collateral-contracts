import argparse
import sys
from web3 import Web3
from eth_account import Account
from eth_utils import is_hex, to_bytes
from celium_collateral_contracts.common import get_revert_reason, get_web3_connection, get_account, build_and_send_transaction, wait_for_receipt
from substrateinterface.utils.ss58 import ss58_decode

class MapHotkeyError(Exception):
    """Custom exception for mapping hotkey to ethereum address"""
    pass

def decode_custom_error(data: str) -> str:
    """
    Decode custom error data returned by the smart contract.

    Args:
        data: Hex string of the error data.

    Returns:
        str: Decoded error message or raw data if decoding fails.
    """
    try:
        # Replace with the actual error signature and parameter types
        error_signatures = {
            "84ee6c0a": "HotkeyAlreadyMapped(bytes32,address)"
        }
        error_selector = data[:10]
        if error_selector in error_signatures:
            if error_selector == "0x84ee6c0a":  # HotkeyAlreadyMapped
                decoded = decode_abi(["bytes32", "address"], bytes.fromhex(data[10:]))
                return f"{error_signatures[error_selector]}: hotkey={decoded[0].hex()}, existingAddress={decoded[1]}"
        return f"Unrecognized error data: {data}"
    except Exception:
        return f"Unrecognized error data: {data}"

def map_hotkey_to_ethereum(w3: Web3, contract_address: str, sender_account: Account, hotkey: str) -> dict:
    """
    Map a Bittensor hotkey to an Ethereum address.

    Args:
        w3: Web3 instance
        contract_address: Address of the Collateral contract
        sender_account: Account instance of the sender
        hotkey: Bittensor hotkey (as bytes32)

    Returns:
        dict: Transaction receipt
    """
    abi = [
        {
            "inputs": [
                {"internalType": "bytes32", "name": "hotkey", "type": "bytes32"}
            ],
            "name": "mapHotkeyToEthereumAddress",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        }
    ]
    contract = w3.eth.contract(address=contract_address, abi=abi)
    print("Contract ABI loaded successfully.")
    print(f"Contract address: {contract_address}")
    print(f"Hotkey: {hotkey}")
    print(f"Sender account: {sender_account.address}")  # Ensure sender_account is an Account object

    pubkey_hex = ss58_decode(hotkey)
    print(f"pubkey_hex: {pubkey_hex}")
    hotkey_bytes32 = bytes.fromhex(pubkey_hex)
    print(f"hotkey_bytes32: {hotkey_bytes32}")

    ethereum_address = sender_account.address  # Extract Ethereum address from Account object
    print(f"Ethereum address: {ethereum_address}")

    try:
        tx_hash = build_and_send_transaction(
            w3,
            contract.functions.mapHotkeyToEthereumAddress(hotkey_bytes32),  # Pass Ethereum address
            sender_account,
            value=0  # Ensure no Ether is sent with the transaction
        )
        print(f"Transaction hash: {tx_hash.hex()}")
        # Wait for transaction receipt
        receipt = wait_for_receipt(w3, tx_hash)

        if receipt['status'] == 0:
            revert_reason = get_revert_reason(w3, tx_hash, receipt['blockNumber'])
            raise MapHotkeyError(f"Transaction failed for mapping hotkey to address. Revert reason: {revert_reason}")

        return receipt

    except ValueError as e:
        error_data = e.args[0]
        if isinstance(error_data, dict) and 'message' in error_data:
            if "Sender doesn't have enough funds" in error_data['message']:
                raise MapHotkeyError("Insufficient funds in the sender's account to cover the transaction cost.")
            elif "reverted with an unrecognized custom error" in error_data['message']:
                custom_error = decode_custom_error(error_data.get('data', ''))
                raise MapHotkeyError(f"Custom error encountered: {custom_error}")
        raise  # Re-raise other exceptions


def main():
    parser = argparse.ArgumentParser(description="Map a Bittensor hotkey to an Ethereum address.")
    parser.add_argument("--contract_address", required=True, help="Address of the Collateral contract.")
    parser.add_argument("--hotkey", required=True, help="Bittensor hotkey (as bytes32).")
    parser.add_argument("--ethereum_address", required=True, help="Ethereum address to associate with the hotkey.")
    parser.add_argument("--keystr", help="Keystring of the account to use.")
    parser.add_argument("--network", default="finney", help="The Subtensor Network to connect to.")
    args = parser.parse_args()

    w3 = get_web3_connection(args.network)
    account = get_account(args.keystr)
    if not isinstance(account, Account):  # Ensure account is an Account object
        account = Account.from_key(account)  # Convert key string to Account object
    print(f"Using account: {account.address}")

    receipt = map_hotkey_to_ethereum(
        w3=w3,
        contract_address=args.contract_address,
        sender_account=account,  # Pass the Account object
        hotkey=args.hotkey,
    )

    print(f"Transaction status: {'Success' if receipt['status'] == 1 else 'Failed'}")
    print(f"Gas used: {receipt['gasUsed']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
