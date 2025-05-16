import argparse
import json
from web3 import Web3
from substrateinterface.utils.ss58 import ss58_decode

def get_eth_address_from_hotkey(w3: Web3, contract_address: str, hotkey: str):
    """Retrieve the Ethereum address mapped to a hotkey."""

    # Convert hotkey string to bytes32
    pubkey_hex = ss58_decode(hotkey)
    print(f"pubkey_hex: {pubkey_hex}")
    hotkey_bytes32 = bytes.fromhex(pubkey_hex)
    print(f"hotkey_bytes32: {hotkey_bytes32}")

    # Load ABI from the Collateral contract artifact
    with open('/home/shadeform/datura/celium-collateral-contracts/artifacts/contracts/Collateral.sol/Collateral.json', 'r') as f:
        artifact = json.load(f)
    abi = artifact['abi']

    contract = w3.eth.contract(address=contract_address, abi=abi)
    eth_address = contract.functions.hotkeyToEthereumAddress(hotkey_bytes32).call()

    return eth_address

def main():
    parser = argparse.ArgumentParser(description="Get Ethereum address from hotkey using Collateral smart contract.")
    parser.add_argument("--contract-address", required=True, help="Address of the Collateral smart contract.")
    parser.add_argument("--hotkey", required=True, help="Hotkey to query.")
    parser.add_argument("--provider-url", default="http://127.0.0.1:8545", help="Ethereum node provider URL.")
    args = parser.parse_args()

    eth_address = get_eth_address_from_hotkey(args.contract_address, args.hotkey, args.provider_url)
    if eth_address == "0x0000000000000000000000000000000000000000":
        print(f"No Ethereum address mapped to hotkey {args.hotkey}.")
    else:
        print(f"Ethereum address for hotkey {args.hotkey}: {eth_address}")

if __name__ == "__main__":
    main()
