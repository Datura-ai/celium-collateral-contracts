from web3 import Web3
from uuid import UUID
from celium_collateral_contracts.common import (
    get_web3_connection,
    get_account,
    validate_address_format,
    get_miner_collateral,
)
from celium_collateral_contracts.deposit_collateral import deposit_collateral
from celium_collateral_contracts.reclaim_collateral import reclaim_collateral
from celium_collateral_contracts.finalize_reclaim import finalize_reclaim
from celium_collateral_contracts.deny_request import deny_reclaim_request
from celium_collateral_contracts.slash_collateral import slash_collateral
from celium_collateral_contracts.get_collaterals import get_deposit_events
from celium_collateral_contracts.get_reclaim_requests import get_reclaim_process_started_events
from celium_collateral_contracts.get_eligible_executors import get_eligible_executors
from celium_collateral_contracts.map_hotkey_to_ethereum import map_hotkey_to_ethereum


class CollateralContract:
    def __init__(self, network: str, contract_address: str, validator_keystr=None, miner_keystr=None):
        self.w3 = get_web3_connection(network)
        try:
            self.validator_account = get_account(validator_keystr) if validator_keystr else None
            self.validator_address = self.validator_account.address if self.validator_account else None
        except Exception as e:
            self.validator_account = None
            self.validator_address = None
            print(f"Warning: Failed to initialize validator account. Error: {e}")

        try:
            self.miner_account = get_account(miner_keystr) if miner_keystr else None
            self.miner_address = self.miner_account.address if self.miner_account else None
        except Exception as e:
            self.miner_account = None
            self.miner_address = None
            print(f"Warning: Failed to initialize miner account. Error: {e}")

        self.contract_address = contract_address

    def deposit_collateral(self, amount_tao, executor_uuid):
        """Deposit collateral into the contract."""
        return deposit_collateral(
            self.w3,
            self.miner_account,
            amount_tao,
            self.contract_address,
            self.validator_address,
            executor_uuid,
        )

    def reclaim_collateral(self, amount_tao, url, executor_uuid):
        """Initiate reclaiming collateral."""
        return reclaim_collateral(
            self.w3,
            self.miner_account,
            amount_tao,
            self.contract_address,
            url,
            executor_uuid,
        )

    def finalize_reclaim(self, reclaim_request_id):
        """Finalize a reclaim request."""
        return finalize_reclaim(
            self.w3,
            self.validator_account,
            reclaim_request_id,
            self.contract_address,
        )

    def deny_reclaim_request(self, reclaim_request_id, url):
        """Deny a reclaim request."""
        return deny_reclaim_request(
            self.w3,
            self.validator_account,
            reclaim_request_id,
            url,
            self.contract_address,
        )

    def slash_collateral(self, amount_tao, url, executor_uuid):
        """Slash collateral from a miner."""
        return slash_collateral(
            self.w3,
            self.validator_account,
            self.miner_address,
            amount_tao,
            self.contract_address,
            url,
            executor_uuid,
        )

    def get_miner_collateral(self):
        """Get the collateral amount for a miner."""
        return get_miner_collateral(self.w3, self.contract_address, self.miner_address)

    def get_deposit_events(self, block_start, block_end):
        """Fetch deposit events within a block range."""
        return get_deposit_events(
            self.w3,
            self.contract_address,
            block_start,
            block_end,
        )

    def get_eligible_executors(self, executor_uuids):
        """Get the list of eligible executors for a miner."""
        return get_eligible_executors(
            self.w3,
            self.contract_address,
            self.miner_address,
            executor_uuids,
        )

    def get_balance(self, address):
        """Get the balance of an Ethereum address."""
        validate_address_format(address)
        balance = self.w3.eth.get_balance(address)
        return self.w3.from_wei(balance, "ether")

    def get_reclaim_requests(self):
        """Fetch claim requests from the latest 100 blocks."""
        latest_block = self.w3.eth.block_number
        return get_reclaim_process_started_events(self.w3, self.contract_address, latest_block - 100, latest_block)

    def map_hotkey_to_ethereum(self, address, hotkey):
        """Map a Bittensor hotkey to an Ethereum address."""
        return map_hotkey_to_ethereum(
            self.w3,
            self.contract_address,
            address,
            hotkey,
        )

def main():
    import os
    import time

    # Configuration
    network = "test"
    contract_address = "0x3512F750a13aF6EF0e62eCD8d4Badf779ea9033f"
    validator_key = "434469242ece0d04889fdfa54470c3685ac226fb3756f5eaf5ddb6991e1698a3"
    miner_key = "259e0eded00353f71eb6be89d8749ad12bf693cbd8aeb6b80cd3a343c0dc8faf"

    # Initialize CollateralContract instance
    contract = CollateralContract(network, contract_address, validator_key, miner_key)

    # Verify chain ID
    chain_id = contract.w3.eth.chain_id
    print(f"Verified chain ID: {chain_id}")

    # Check balances
    print("Validator Balance:", contract.get_balance(contract.validator_address))
    print("Miner Balance:", contract.get_balance(contract.miner_address))

    # Map hotkey to Ethereum address
    hotkey = "5CdjQSjNefhzH71jmekdYDcM9NJm48Rdbx1cQhemfmdb4UQg"
    ethereum_address = validator_key  # Using the validator key as the Ethereum address
    print(f"Mapping hotkey {hotkey} to Ethereum address {ethereum_address}...")
    try:
        receipt = contract.map_hotkey_to_ethereum(
            address=contract.validator_account,
            hotkey=hotkey,
        )
        print(f"Transaction status: {'Success' if receipt['status'] == 1 else 'Failed'}")
        print(f"Gas used: {receipt['gasUsed']}")
    except Exception as e:
        print(f"Error mapping hotkey: {e}")

    # Deposit collateral
    deposit_tasks = [
        ("3a5ce92a-a066-45f7-b07d-58b3b7986464", 0.0005),
        ("72a1d228-3c8c-45cb-8b84-980071592589", 0.0005),
        ("15c2ff27-0a4d-4987-bbc9-fa009ef9f7d2", 0.0005),
        ("335453ad-246c-4ad5-809e-e2013ca6c07e", 0.0005),
        ("89c66519-244f-4db0-b4a7-756014d6fd24", 0.0005),
        ("af3f1b82-ff98-44c8-b130-d948a2a56b44", 0.0005),
        ("ee3002d9-71f8-4a83-881d-48bd21b6bdd1", 0.0005),
        ("4f42de60-3a41-4d76-9a19-d6d2644eb57f", 0.0005),
        ("7ac4184e-e84f-40cb-b6a0-9cf79a1a573c", 0.0005),
        ("9d14f803-dc8c-405f-99b5-80f12207d4e5", 0.0005),
        ("2a61e295-fd0f-4568-b01c-1c38c21573ac", 0.0005),
        ("e7fd0b3f-4a42-4a5d-bda6-8e2f4b5cb92a", 0.0005),
        ("f2c2a71d-5c44-4ab9-a87e-0ac1f278b6d6", 0.0005),
        ("1ec29b47-3d6b-4cc3-b71d-6c97fcbf1e89", 0.0005),
    ]
    # for uuid_str, amount in deposit_tasks:
    #     print(f"Depositing collateral for executor {uuid_str}...")
    #     contract.deposit_collateral(amount, uuid_str)

    # Verify collateral
    collateral = contract.get_miner_collateral()
    collateral_in_tao = contract.w3.from_wei(collateral, "ether")
    print("[COLLATERAL]:", collateral_in_tao)

    # List eligible executors
    executor_uuids = [uuid for uuid, _ in deposit_tasks]
    eligible_executors = contract.get_eligible_executors(executor_uuids)
    print("Eligible Executors:", eligible_executors)

    # Reclaim collateral
    # reclaim_uuid = "72a1d228-3c8c-45cb-8b84-980071592589"
    # print("Reclaiming collateral...")
    # reclaim_result = contract.reclaim_collateral(0.00001, "please gimme money back", reclaim_uuid)
    # print("Reclaim Result:", reclaim_result)

    # for uuid_str, amount in deposit_tasks:
    #     print("Reclaiming collateral...")
    #     reclaim_result = contract.reclaim_collateral(amount, "please gimme money back", uuid_str)
    #     print("Reclaim Result:", reclaim_result)

    # Fetch reclaim requests
    # latest_block = contract.w3.eth.block_number
    # print(f"Fetching reclaim requests between blocks {latest_block - 100} and {latest_block + 100}...")
    # reclaim_requests = contract.get_reclaim_requests()
    # print("Reclaim Requests:", reclaim_requests)

    # Deny and finalize reclaim requests
    # print("Denying reclaim request...")
    # contract.deny_reclaim_request(reclaim_request_id=2, url="no, i will not")

    # for i in range(65, 66):
    #     print(f"Finalizing reclaim request..., reclaim_request_id = {i}")
    #     try:
    #         contract.finalize_reclaim(reclaim_request_id=i)
    #     except Exception as e:
    #         print(f"Error finalizing reclaim request {i}: {e}")

    # Final collateral check
    final_collateral = contract.get_miner_collateral()
    final_collateral_in_tao = contract.w3.from_wei(final_collateral, "ether")
    print("[FINAL COLLATERAL]:", final_collateral_in_tao)

    # Check transferrable balances
    print("Validator Balance:", contract.get_balance(contract.validator_address))
    print("Miner Balance:", contract.get_balance(contract.miner_address))

    print("✅ Contract lifecycle completed successfully.")

if __name__ == "__main__":
    main()