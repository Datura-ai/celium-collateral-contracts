from uuid import UUID
from web3 import Web3
from web3.contract import Contract
from eth_account import Account
from datetime import datetime

from celium_collateral_contracts.common import (
    get_web3_connection,
    get_account,
    get_contract,
    validate_address_format,
    build_and_send_transaction,
    wait_for_receipt,
    get_revert_reason,
    calculate_md5_checksum,
)
from celium_collateral_contracts.deposit_collateral import DepositCollateralError
from celium_collateral_contracts.reclaim_collateral import ReclaimCollateralError
from celium_collateral_contracts.finalize_reclaim import FinalizeReclaimError
from celium_collateral_contracts.deny_request import DenyReclaimRequestError
from celium_collateral_contracts.slash_collateral import SlashCollateralError
from celium_collateral_contracts.get_collaterals import DepositEvent
from celium_collateral_contracts.get_reclaim_requests import ReclaimProcessStartedEvent, ReclaimRequest


dateTimeFormat = '%Y-%m-%d %H:%M:%S UTC'


class CollateralContract:
    w3: Web3
    contract_address: str
    contract: Contract
    owner_account: Account | None
    owner_address: str | None
    miner_account: Account | None
    miner_address: str | None

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
            self.contract_address = contract_address
            self.contract = get_contract(self.w3, contract_address)
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

    def get_uuid_bytes(self, uuid: UUID | str):
        if isinstance(uuid, str):
            try:
                # Try to parse as UUID string
                uuid_bytes = UUID(uuid).bytes
            except Exception:
                # If not a UUID, try to decode as hex
                uuid_bytes = bytes.fromhex(uuid.replace('0x', ''))
            # Pad or trim to 16 bytes
        else:
            uuid_bytes = uuid.bytes

        uuid_bytes = uuid_bytes[:16] if len(uuid_bytes) > 16 else uuid_bytes.ljust(16, b'\0')
        return uuid_bytes

    async def check_minimum_collateral(self, amount_wei):
        """Check if the amount meets minimum collateral requirement."""
        min_collateral = await self.contract.functions.MIN_COLLATERAL_INCREASE().call()
        if amount_wei < min_collateral:
            raise ValueError(
                f"Error: Amount {Web3.from_wei(amount_wei, 'ether')} TAO is less than "
                f"minimum required {Web3.from_wei(min_collateral, 'ether')} TAO"
            )
        return min_collateral

    async def deposit_collateral(self, amount_tao, executor_uuid):
        """Deposit collateral into the contract."""
        amount_wei = self.w3.to_wei(amount_tao, "ether")
        await self.check_minimum_collateral(amount_wei)

        executor_uuid_bytes = self.get_uuid_bytes(executor_uuid)

        tx_hash = await build_and_send_transaction(
            self.w3,
            self.contract.functions.deposit(executor_uuid_bytes),
            self.miner_account,
            value=amount_wei,
            gas_limit=200000,  # Higher gas limit for this function
        )

        receipt = await wait_for_receipt(self.w3, tx_hash)
        if receipt['status'] == 0:
            revert_reason = await get_revert_reason(self.w3, tx_hash, receipt['blockNumber'])
            raise DepositCollateralError(f"Transaction failed for depositing collateral. Revert reason: {revert_reason}")
        deposit_events = self.contract.events.Deposit().process_receipt(receipt)
        if not deposit_events:
            return None, receipt
        deposit_event = deposit_events[0]

        return deposit_event, receipt

    async def reclaim_collateral(self, url, executor_uuid):
        """Reclaim collateral from the contract.

        Args:
            url (str): URL for reclaim information
            executor_uuid (str): Executor UUID for the reclaim operation

        Returns:
            dict: Transaction receipt with reclaim event details

        Raises:
            Exception: If the transaction fails
        """
        # Calculate MD5 checksum if URL is valid
        md5_checksum = "0" * 32
        if url.startswith(("http://", "https://")):
            print("Calculating MD5 checksum of URL content...")
            md5_checksum = calculate_md5_checksum(url)
            print(f"MD5 checksum: {md5_checksum}")

        executor_uuid_bytes = self.get_uuid_bytes(executor_uuid)

        tx_hash = await build_and_send_transaction(
            self.w3,
            self.contract.functions.reclaimCollateral(
                executor_uuid_bytes,
                url,
                bytes.fromhex(md5_checksum)
            ),
            self.miner_account,
            gas_limit=200000,  # Higher gas limit for this function
        )

        receipt = await wait_for_receipt(self.w3, tx_hash)
        if receipt['status'] == 0:
            revert_reason = await get_revert_reason(self.w3, tx_hash, receipt['blockNumber'])
            raise ReclaimCollateralError(f"Transaction failed for reclaiming collateral. Revert reason: {revert_reason}")
        reclaim_event = self.contract.events.ReclaimProcessStarted().process_receipt(
            receipt,
        )[0]

        print("Event details:")
        print(f"  Reclaim ID: {reclaim_event['args']['reclaimRequestId']}")
        print(f"  Executor ID: {reclaim_event['args']['executorId']}")
        print(f"  Miner Address: {reclaim_event['args']['miner']}")
        print(
            f"  Amount: "
            f"{self.w3.from_wei(reclaim_event['args']['amount'], 'ether')} TAO",
        )
        print(
            f"  Expiration Time: {reclaim_event['args']['expirationTime']}")
        print(f"  URL: {reclaim_event['args']['url']}")
        print(
            f"  URL Content MD5: "
            f"{reclaim_event['args']['urlContentMd5Checksum'].hex()}",
        )
        print(
            f"  Transaction hash: {receipt['transactionHash'].hex()}")
        print(f"  Block number: {receipt['blockNumber']}")

        return receipt, reclaim_event

    async def get_reclaim_by_id(self, reclaim_id):
        """Fetch reclaim information using reclaim_id."""
        reclaim = await self.contract.functions.reclaims(reclaim_id).call()

        return ReclaimRequest(
            reclaim_request_id=reclaim_id,
            executor_uuid=str(UUID(bytes=reclaim[0])),
            miner=reclaim[1],
            amount=float(self.w3.from_wei(reclaim[2], "ether")),
            expiration_time=datetime.utcfromtimestamp(reclaim[3]).strftime(dateTimeFormat),
        )

    async def finalize_reclaim(self, reclaim_request_id):
        """Finalize a reclaim request on the contract.

        Args:
            reclaim_request_id: ID of the reclaim request to finalize

        Returns:
            tuple: (reclaim_event, receipt)

        Raises:
            FinalizeReclaimError: If the transaction fails for any reason
        """
        reclaim_info = await self.get_reclaim_by_id(reclaim_request_id)
        if reclaim_info.amount == 0:
            raise FinalizeReclaimError(f"Reclaim request {reclaim_request_id} has already been finalized")

        tx_hash = await build_and_send_transaction(
            self.w3,
            self.contract.functions.finalizeReclaim(reclaim_request_id),
            self.miner_account,
            gas_limit=200000,
        )
        receipt = await wait_for_receipt(self.w3, tx_hash)

        if receipt['status'] == 0:
            # Try to get revert reason
            revert_reason = await get_revert_reason(self.w3, tx_hash, receipt['blockNumber'])
            raise FinalizeReclaimError(f"Transaction failed for finalizing reclaim request {reclaim_request_id}. Revert reason: {revert_reason}")

        reclaim_events = self.contract.events.Reclaimed().process_receipt(receipt)
        if not reclaim_events:
            # This case happens if the miner was slashed and couldn't withdraw.
            # The transaction itself is successful, but no Reclaimed event is emitted.
            print(f"Finalize reclaim transaction successful for request {reclaim_request_id}, but no Reclaimed event emitted. This likely means the miner was slashed and the reclaim was cancelled.")
            return None, receipt
        reclaim_event = reclaim_events[0]

        if reclaim_event:
            print("Event details:")
            print(f"  Reclaim ID: {reclaim_event['args']['reclaimRequestId']}")
            print(f"  Executor ID: {reclaim_event['args']['executorId']}")
            print(
                f"  Amount: {self.w3.from_wei(reclaim_event['args']['amount'], 'ether')} TAO")
            print(f"  Transaction hash: {receipt['transactionHash'].hex()}")
            print(f"  Block number: {receipt['blockNumber']}")
        else:
            print(f"Transaction hash: {receipt['transactionHash'].hex()}")
            print(f"Block number: {receipt['blockNumber']}")

        return reclaim_event, receipt

    async def deny_reclaim_request(self, reclaim_request_id, url):
        """Deny a reclaim request on the contract.

        Args:
            reclaim_request_id: ID of the reclaim request to deny
            url: URL containing the reason for denial
            contract_address: Address of the contract

        Returns:
            tuple: (deny_event, receipt)
        """

        # Calculate MD5 checksum of the URL content
        md5_checksum = "0" * 32
        if url.startswith(("http://", "https://")):
            print("Calculating MD5 checksum of URL content...")
            md5_checksum = calculate_md5_checksum(url)
            print(f"MD5 checksum: {md5_checksum}")

        tx_hash = await build_and_send_transaction(
            self.w3,
            self.contract.functions.denyReclaimRequest(
                reclaim_request_id, url, bytes.fromhex(md5_checksum)
            ),
            self.owner_account,
            gas_limit=200000,
        )

        receipt = await wait_for_receipt(self.w3, tx_hash)
        if receipt['status'] == 0:
            # Get revert reason for failed transaction
            revert_reason = await get_revert_reason(self.w3, tx_hash, receipt['blockNumber'])
            raise DenyReclaimRequestError(
                f"Transaction failed for denying reclaim request {reclaim_request_id}. Revert reason: {revert_reason}"
            )
        deny_event = self.contract.events.Denied().process_receipt(receipt)[0]

        return deny_event, receipt

    async def slash_collateral(self, executor_uuid, slash_amount_tao, url):
        """Slash collateral from a miner.

        Args:
            executor_uuid (str): Executor UUID for the slashing operation
            slash_amount_tao (float): Amount to slash in TAO
            url (str): URL containing information about the slash

        Returns:
            dict: Transaction receipt with slash event details

        Raises:
            Exception: If the transaction fails
        """
        # Calculate MD5 checksum if URL is valid
        md5_checksum = "0" * 32
        if url.startswith(("http://", "https://")):
            print("Calculating MD5 checksum of URL content...")
            md5_checksum = calculate_md5_checksum(url)
            print(f"MD5 checksum: {md5_checksum}")

        executor_uuid_bytes = self.get_uuid_bytes(executor_uuid)
        slash_amount_wei = self.w3.to_wei(slash_amount_tao, "ether")

        tx_hash = await build_and_send_transaction(
            self.w3,
            self.contract.functions.slashCollateral(
                executor_uuid_bytes,
                slash_amount_wei,
                url,
                bytes.fromhex(md5_checksum),
            ),
            self.owner_account,
            gas_limit=200000,  # Higher gas limit for this function
        )

        receipt = await wait_for_receipt(self.w3, tx_hash)
        if receipt['status'] == 0:
            revert_reason = await get_revert_reason(self.w3, tx_hash, receipt['blockNumber'])
            raise SlashCollateralError(f"Transaction failed for slashing collateral. Revert reason: {revert_reason}")
        slash_event = self.contract.events.Slashed().process_receipt(receipt)[0]

        return receipt, slash_event

    async def get_deposit_events(self, block_start, block_end):
        """Fetch deposit events within a block range."""
        checksum_address = self.w3.to_checksum_address(self.contract_address)

        event_signature = "Deposit(bytes16,address,uint256)"
        event_topic = self.w3.keccak(text=event_signature).hex()

        filter_params = {
            "fromBlock": hex(block_start),
            "toBlock": hex(block_end),
            "address": checksum_address,
            "topics": [event_topic]
        }

        logs = await self.w3.eth.get_logs(filter_params)

        formatted_events = []
        for log in logs:
            account_address = "0x" + log["topics"][1].hex()[-40:]
            account = self.w3.to_checksum_address(account_address)

            decoded_event = self.contract.events.Deposit().process_log(log)

            formatted_events.append(
                DepositEvent(
                    account=account,
                    miner=decoded_event['args']['miner'],
                    executor_uuid=str(UUID(bytes=decoded_event['args']['executorId'])),
                    amount=float(self.w3.from_wei(decoded_event['args']['amount'], "ether")),
                    block_number=log["blockNumber"],
                    transaction_hash=log["transactionHash"].hex(),
                )
            )

        return formatted_events

    async def get_balance(self, address):
        """Get the balance of an Ethereum address."""
        validate_address_format(address)
        balance = await self.w3.eth.get_balance(address)
        return self.w3.from_wei(balance, "ether")

    async def get_reclaim_events(self) -> list[ReclaimProcessStartedEvent]:
        """Fetch claim requests from the latest 1000 blocks."""
        latest_block = await self.w3.eth.block_number
        block_num_low = latest_block - 1000
        block_num_high = latest_block
        checksum_address = self.w3.to_checksum_address(self.contract_address)

        event_signature = "ReclaimProcessStarted(uint256,bytes16,address,uint256,uint64,string,bytes16)"
        event_topic = self.w3.keccak(text=event_signature).hex()

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

        logs = await self.w3.eth.get_logs(filter_params)

        formatted_events = []
        for log in logs:
            reclaim_request_id = int(log["topics"][1].hex(), 16)

            decoded_event = self.contract.events.ReclaimProcessStarted().process_log(log)
            reclaim_info = await self.get_reclaim_by_id(reclaim_request_id)
            if reclaim_info.amount == 0:
                continue

            formatted_events.append(
                ReclaimProcessStartedEvent(
                    reclaim_request_id=reclaim_request_id,
                    amount=reclaim_info.amount,
                    expiration_time=reclaim_info.expiration_time,
                    executor_uuid=reclaim_info.executor_uuid,
                    url=decoded_event['args']['url'],
                    url_content_md5_checksum=decoded_event['args']['urlContentMd5Checksum'].hex(),
                    block_number=log["blockNumber"],
                ))

        return formatted_events

    async def get_executor_collateral(self, executor_uuid):
        """Get the collateral amount for executor UUID."""
        uuid_bytes = self.get_uuid_bytes(executor_uuid)
        executor_collateral = await self.contract.functions.collaterals(uuid_bytes).call()
        return self.w3.from_wei(executor_collateral, "ether")

    async def get_miner_address_of_executor(self, executor_uuid):
        uuid_bytes = self.get_uuid_bytes(executor_uuid)
        return await self.contract.functions.executorToMiner(uuid_bytes).call()

    async def get_burn_address(self):
        """Get the burn address configured in the contract."""
        return await self.contract.functions.BURN_ADDRESS().call()

    async def get_trustee_address(self):
        """Get the trustee address configured in the contract."""
        return await self.contract.functions.TRUSTEE().call()
