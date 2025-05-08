from web3 import Web3
import json

# Connect to local Ethereum node
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
w3.eth.default_account = w3.eth.accounts[0]

# ABI and contract address from deployment
with open('artifacts/contracts/ValueStore.sol/ValueStore.json', 'r') as f:
    artifact = json.load(f)
abi = artifact['abi']

contract_address = "0x0DCd1Bf9A1b36cE34237eEaFef220932846BCD82"  # Update with the correct address
contract = w3.eth.contract(address=contract_address, abi=abi)

# Add entries
tx1 = contract.functions.addEntry(123, "Hello", True).transact()
tx2 = contract.functions.addEntry(456, "World", False).transact()

# Wait for transaction receipts
w3.eth.wait_for_transaction_receipt(tx1)
w3.eth.wait_for_transaction_receipt(tx2)

# Retrieve and print entries
count = contract.functions.getCount().call()
print("count:", count)
for i in range(count):
    entry = contract.functions.getEntry(i).call()
    print(f"Entry {i}: number={entry[0]}, text='{entry[1]}', flag={entry[2]}")

numbers = contract.functions.getNumbers().call()
print("Numbers:", numbers)

executors = contract.functions.getExecutors().call()
print("Known Executor UUIDs:")
for uuid in executors:
    print(uuid.hex())