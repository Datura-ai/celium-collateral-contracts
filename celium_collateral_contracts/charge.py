from web3 import Web3

# Connect to local EVM node
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))

# Replace with your target private key
target_private_key = "0x4c0883a69102937d6231471b5dbb6204fe512961708279a3f3d8f7e7a7e8a6d4"
target_account = w3.eth.account.from_key(target_private_key)
target_address = target_account.address

# Use a pre-funded Hardhat/Ganache account
sender_account = w3.eth.accounts[0]

# Build and send transaction
tx = {
    'to': target_address,
    'from': sender_account,
    'value': w3.to_wei(1000, 'ether'),
    'gas': 21000,
    'nonce': w3.eth.get_transaction_count(sender_account),
    'gasPrice': w3.eth.gas_price
}

tx_hash = w3.eth.send_transaction(tx)  # Send the transaction directly without signing

print("✅ Sent 1000 ETH to:", target_address)
print("📦 Tx Hash:", tx_hash.hex())
print("🔎 New balance:", w3.from_wei(w3.eth.get_balance(target_address), 'ether'), "ETH")
