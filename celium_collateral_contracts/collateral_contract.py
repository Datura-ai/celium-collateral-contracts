import asyncio
from celium_collateral_contracts.common import (
    get_web3_connection,
    get_account,
    validate_address_format,
    get_executor_collateral,
    get_miner_address_of_executor
)
from celium_collateral_contracts.deposit_collateral import deposit_collateral
from celium_collateral_contracts.reclaim_collateral import reclaim_collateral
from celium_collateral_contracts.finalize_reclaim import finalize_reclaim
from celium_collateral_contracts.deny_request import deny_reclaim_request
from celium_collateral_contracts.slash_collateral import slash_collateral
from celium_collateral_contracts.get_collaterals import get_deposit_events
from celium_collateral_contracts.get_reclaim_requests import get_reclaim_process_started_events

class CollateralContract:
    def __init__(
        self,
        network: str,
        contract_address: str,
        rpc_url: str | None = None,
        owner_key: str | None = None,
        miner_key: str | None = None,
    ):
        try:
            self.w3 = get_web3_connection(network, rpc_url)
        except Exception as e:
            print(f"Warning: Failed to connect bittensor network. Error: {e}")

        try:
            self.owner_account = get_account(owner_key) if owner_key else None
            self.owner_address = self.owner_account.address if self.owner_account else None
        except Exception as e:
            self.owner_account = None
            self.owner_address = None
            print(f"Warning: Failed to initialize owner account. Error: {e}")

        try:
            self.miner_account = get_account(miner_key) if miner_key else None
            self.miner_address = self.miner_account.address if self.miner_account else None
        except Exception as e:
            self.miner_account = None
            self.miner_address = None
            print(f"Warning: Failed to initialize miner account. Error: {e}")

        self.contract_address = contract_address

    async def deposit_collateral(self, amount_tao, executor_uuid):
        """Deposit collateral into the contract."""
        return await deposit_collateral(
            self.w3,
            self.miner_account,
            amount_tao,
            self.contract_address,
            executor_uuid,
        )

    async def reclaim_collateral(self, url, executor_uuid):
        """Initiate reclaiming collateral."""
        return await reclaim_collateral(
            self.w3,
            self.miner_account,            
            self.contract_address,
            url,
            executor_uuid,
        )

    async def finalize_reclaim(self, reclaim_request_id):
        """Finalize a reclaim request."""
        return await finalize_reclaim(
            self.w3,
            self.miner_account,
            reclaim_request_id,
            self.contract_address,
        )

    async def deny_reclaim_request(self, reclaim_request_id, url):
        """Deny a reclaim request."""
        return await deny_reclaim_request(
            self.w3,
            self.owner_account,
            reclaim_request_id,
            url,
            self.contract_address,
        )

    async def slash_collateral(self, url, executor_uuid):
        """Slash collateral from a miner."""
        return await slash_collateral(
            self.w3,
            self.owner_account,
            self.contract_address,
            url,
            executor_uuid,
        )

    async def get_deposit_events(self, block_start, block_end):
        """Fetch deposit events within a block range."""
        return await get_deposit_events(
            self.w3,
            self.contract_address,
            block_start,
            block_end,
        )

    async def get_balance(self, address):
        """Get the balance of an Ethereum address."""
        validate_address_format(address)
        balance = self.w3.eth.get_balance(address)
        return self.w3.from_wei(balance, "ether")

    async def get_reclaim_events(self):
        """Fetch claim requests from the latest 1000 blocks."""
        latest_block = self.w3.eth.block_number
        return await get_reclaim_process_started_events(
            self.w3, self.contract_address, latest_block-1000, latest_block
        )
    
    async def get_executor_collateral(self, executor_uuid):
        """Get the collateral amount for executor UUID."""
        return get_executor_collateral(self.w3, self.contract_address, executor_uuid)


    async def get_miner_address_of_executor(self, executor_uuid):
        return get_miner_address_of_executor(self.w3, self.contract_address, executor_uuid)
    

async def main():
    # Configuration
    network = "local"
    contract_address = "0x91d1b1BF9539Cd535402FDE0FC30417CaF8CC631"
    owner_key = "434469242ece0d04889fdfa54470c3685ac226fb3756f5eaf5ddb6991e1698a3"
    miner_key = "259e0eded00353f71eb6be89d8749ad12bf693cbd8aeb6b80cd3a343c0dc8faf"

    # Initialize CollateralContract instance
    contract = CollateralContract(network, contract_address, owner_key, miner_key)

    # Verify chain ID
    chain_id = contract.w3.eth.chain_id
    print(f"Verified chain ID: {chain_id}")

    # Check balances
    miner_balance = await contract.get_balance(contract.miner_address)
    print("Miner Balance:", miner_balance)

    # Deposit collateral (optional: uncomment to use)
    deposit_tasks = [
        ("3a5ce92a-a066-45f7-b07d-58b3b7986464", 0.005),
        ("72a1d228-3c8c-45cb-8b84-980071592589", 0.005),
        ("15c2ff27-0a4d-4987-bbc9-fa009ef9f7d2", 0.005),
        ("335453ad-246c-4ad5-809e-e2013ca6c07e", 0.005),
        ("89c66519-244f-4db0-b4a7-756014d6fd24", 0.005),
        ("af3f1b82-ff98-44c8-b130-d948a2a56b44", 0.005),
        ("ee3002d9-71f8-4a83-881d-48bd21b6bdd1", 0.005),
        ("4f42de60-3a41-4d76-9a19-d6d2644eb57f", 0.005),
        ("7ac4184e-e84f-40cb-b6a0-9cf79a1a573c", 0.005),
        ("9d14f803-dc8c-405f-99b5-80f12207d4e5", 0.005),
        ("2a61e295-fd0f-4568-b01c-1c38c21573ac", 0.005),
        ("e7fd0b3f-4a42-4a5d-bda6-8e2f4b5cb92a", 0.005),
        ("f2c2a71d-5c44-4ab9-a87e-0ac1f278b6d6", 0.005),
        ("1ec29b47-3d6b-4cc3-b71d-6c97fcbf1e89", 0.005),
    ]

    # Example deposit (uncomment to perform deposits)
    for uuid_str, amount in deposit_tasks:
        print(f"Depositing collateral for executor {uuid_str}...")
        await contract.deposit_collateral(amount, uuid_str)

    # Print executor collateral for each UUID after deposits
    print("\n[EXECUTOR COLLATERAL AFTER DEPOSITS]:")
    for uuid_str, _ in deposit_tasks:
        executor_collateral = await contract.get_executor_collateral(uuid_str)
        print(f"Executor {uuid_str}: {executor_collateral} TAO")

    for uuid_str, _ in deposit_tasks:
        print(f"Reclaiming collateral for executor {uuid_str}...")
        await contract.reclaim_collateral(f"Reclaim collateral from executor: {uuid_str}", uuid_str)
 
    reclaim_requests = await contract.get_reclaim_events()
    print("reclaim_requests", reclaim_requests)
    for reclaim_event in reclaim_requests:
        reclaim_request_id = getattr(reclaim_event, "reclaim_request_id", None)
        print("Reclaim Request Id:", reclaim_request_id)
        if reclaim_request_id is not None:
            try:
                await contract.finalize_reclaim(reclaim_request_id)
            except Exception as e:
                print("Reclaim Error:", str(e))

    for uuid_str, _ in deposit_tasks:
        print(f"Slashing collateral for executor {uuid_str}...")
        try:
            await contract.slash_collateral("slashit", uuid_str)
        except Exception as e:
            print("Slash Error:", str(e))

    # Verify collateral
    for uuid_str, _ in deposit_tasks:
        executor_collateral = await contract.get_executor_collateral(uuid_str)
        print(f"Executor {uuid_str}: {executor_collateral} TAO")

    # Check final balances
    owner_balance = await contract.get_balance(contract.owner_address)
    miner_balance = await contract.get_balance(contract.miner_address)
    print("Owner Balance:", owner_balance)
    print("Miner Balance:", miner_balance)

    print("✅ Contract lifecycle completed successfully.")

if __name__ == "__main__":
    asyncio.run(main())
