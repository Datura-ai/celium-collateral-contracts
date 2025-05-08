from web3 import Web3
import json
import uuid

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

contract_address = "0xc6e7DF5E7b4f2A278906862b61205850344D4e7d"
contract = w3.eth.contract(address=contract_address, abi=abi)

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

# Example usage
if __name__ == "__main__":
    validator_address = "0x0000000000000000000000000000000000000001"
    executor_uuid = "3a5ce92a-a066-45f7-b07d-58b3b7986464"
    miner_address = w3.eth.accounts[1]

    # Deposit example
    deposit_collateral(validator_address, uuid_to_bytes16(executor_uuid), Web3.to_wei(1, 'ether'))

    # # Reclaim example
    # reclaim_collateral(Web3.to_wei(0.5, 'ether'), "http://example.com/reclaim", b"checksum1234", executor_uuid)

    # # Finalize reclaim example
    # finalize_reclaim(1)

    # # Deny reclaim example
    # deny_reclaim_request(1, "http://example.com/deny", b"checksum5678")

    # # Slash collateral example
    # slash_collateral(miner_address, Web3.to_wei(0.1, 'ether'), "http://example.com/slash", b"checksum91011", executor_uuid)

    # # Get eligible executors example
    get_eligible_executors(miner_address)
