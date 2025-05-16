from web3 import Web3
import json
import uuid
from map_hotkey_to_ethereum import map_hotkey_to_ethereum
from eth_account import Account
from get_eth_address_from_hotkey import get_eth_address_from_hotkey

def uuid_to_bytes16(uuid_str):
    u = uuid.UUID(uuid_str)
    return "0x" + u.bytes.hex()

# Connect to local Ethereum node
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

w3.eth.default_account = w3.eth.accounts[0]

# ABI and contract address from deployment
with open('artifacts/contracts/Collateral.sol/Collateral.json', 'r') as f:
    artifact = json.load(f)
abi = artifact['abi']

contract_address = "0x82e01223d51Eb87e16A03E24687EDF0F294da6f1"
contract = w3.eth.contract(address=contract_address, abi=abi)

# Check if contract is deployed
def is_contract_deployed(address):
    code = w3.eth.get_code(address)
    return code != b'0x' and code != b''

# Example calls to Collateral contract methods

# Deposit collateral
def deposit_collateral(validator, executor_uuid, amount):
    tx = contract.functions.deposit(validator, executor_uuid).transact({'value': amount})
    receipt = w3.eth.wait_for_transaction_receipt(tx)
    print("Deposit transaction receipt:", receipt)

# Reclaim collateral
def reclaim_collateral(amount, url, url_checksum, executor_uuid):
    tx = contract.functions.reclaimCollateral(amount, url, url_checksum, executor_uuid).transact()
    receipt = w3.eth.wait_for_transaction_receipt(tx)
    print("Reclaim transaction receipt:", receipt)

# Finalize reclaim
def finalize_reclaim(reclaim_request_id):
    tx = contract.functions.finalizeReclaim(reclaim_request_id).transact()
    receipt = w3.eth.wait_for_transaction_receipt(tx)
    print("Finalize reclaim transaction receipt:", receipt)

# Deny reclaim request
def deny_reclaim_request(reclaim_request_id, url, url_checksum):
    tx = contract.functions.denyReclaimRequest(reclaim_request_id, url, url_checksum).transact()
    receipt = w3.eth.wait_for_transaction_receipt(tx)
    print("Deny reclaim transaction receipt:", receipt)

# Slash collateral
def slash_collateral(miner, amount, url, url_checksum, executor_uuid):
    tx = contract.functions.slashCollateral(miner, amount, url, url_checksum, executor_uuid).transact()
    receipt = w3.eth.wait_for_transaction_receipt(tx)
    print("Slash collateral transaction receipt:", receipt)

# Get eligible executors
def get_eligible_executors(miner):
    executors = contract.functions.getEligibleExecutors(miner).call()
    print("Eligible executors:", executors)

# Map hotkey to Ethereum address
def map_hotkey_to_eth_address(hotkey, private_key):
    """
    Map a Bittensor hotkey to an Ethereum address.
    """
    try:
        sender_account = Account.from_key(private_key)  # Convert private key to Account object
        print("sender_account:", sender_account)
        receipt = map_hotkey_to_ethereum(w3, contract_address, sender_account, hotkey)
        print(f"Hotkey mapped to Ethereum address successfully. Transaction receipt: {receipt}")
    except Exception as e:
        print(f"Error mapping hotkey to Ethereum address: {e}")

# Example usage
if __name__ == "__main__":
    if not is_contract_deployed(contract_address):
        print(f"Contract not deployed at address {contract_address}")
    else:
        miner_address = w3.eth.accounts[0]
        print("Miner address:", miner_address)

        # Correctly retrieve miner account details
        try:
            miner_account = {"address": miner_address}
            print("Miner Account Address:", miner_account["address"])
        except Exception as e:
            print("Error retrieving miner account details:", e)

        validator_address = "0xE1A07A44ac6f8423bA3b734F0cAfC6F87fd385Fc"
        executor_uuid = "3a5ce92a-a066-45f7-b07d-58b3b7986464"
        miner_address = w3.eth.accounts[0]
        # miner_address = "0x19F71e76B34A8Dc01944Cf3B76478B45DE05B75b"
        
        print("Miner address:", miner_address)

        balance = w3.eth.get_balance(miner_address)
        print("Miner Balance:", w3.from_wei(balance, 'ether'))

        # Deposit example
        deposit_collateral(validator_address, uuid_to_bytes16(executor_uuid), Web3.to_wei(1, 'ether'))

        try:
            collateral = contract.functions.collaterals(miner_address).call()
            print("Collateral for miner:", Web3.from_wei(collateral, 'ether'), "ETH")
            
        except Exception as e:
            print("Error calling contract function:", e)

        # Map hotkey to Ethereum address
        hotkey = "5CdjQSjNefhzH71jmekdYDcM9NJm48Rdbx1cQhemfmdb4UQg"
        private_key = "0x4c0883a69102937d6231471b5dbb6204fe512961708279a3f3d8f7e7a7e8a6d4"  # Example private key
        map_hotkey_to_eth_address(hotkey, private_key)

        # Call get_eth_address_from_hotkey
        try:
            hotkey = "5CdjQSjNefhzH71jmekdYDcM9NJm48Rdbx1cQhemfmdb4UQg"
            eth_address = get_eth_address_from_hotkey(w3, contract_address, hotkey)
            if eth_address == "0x0000000000000000000000000000000000000000":
                print(f"No Ethereum address mapped to hotkey {hotkey}.")
            else:
                print(f"Ethereum address for hotkey {hotkey}: {eth_address}")
        except Exception as e:
            print(f"Error retrieving Ethereum address for hotkey: {e}")
