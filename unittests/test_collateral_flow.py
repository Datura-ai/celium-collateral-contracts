import sys
import os
import time
import subprocess
import unittest
from eth_account import Account
from web3 import Web3
import uuid
import re

# Update import to use the scripts package
from celium_collateral_contracts.address_conversion import h160_to_ss58


def get_transferrable_balance(w3: Web3, sender: str, recipient: str):
    # Build a dummy transaction to estimate gas
    nonce = w3.eth.get_transaction_count(sender)

    tx = {
        'from': sender,
        'to': recipient,
        'value': 1,
        'nonce': nonce  # include nonce for accuracy
    }

    try:
        gas_estimate = w3.eth.estimate_gas(tx)
    except Exception as e:
        print(f"Gas estimation failed: {e}")
        gas_estimate = 21000  # Fallback to standard ETH transfer gas

    try:
        # For EIP-1559 networks
        fee_history = w3.eth.fee_history(1, 'latest', [50])
        base_fee = fee_history['baseFeePerGas'][-1]
        priority_fee = w3.eth.max_priority_fee
        gas_price = base_fee + priority_fee
    except Exception:
        # For legacy networks
        gas_price = w3.eth.gas_price

    print(f"Gas estimate: {gas_estimate}, Gas price: {gas_price}")
    gas_cost = gas_estimate * gas_price
    balance = w3.eth.get_balance(sender)
    buffer = Web3.to_wei(0.001, 'ether')
    transferrable = max(0, balance - gas_cost - buffer)  # Subtract a small buffer
    return transferrable
    
class TestCollateralContractLifecycle(unittest.TestCase):
    USE_EXISTING_ACCOUNTS = True
    DEPLOY_CONTRACT = False

    # Add a helper to run subprocess commands with a sleep delay
    def run_cmd(self, cmd, env, capture=True, sleep_time=1):
        result = subprocess.run(cmd, capture_output=capture, text=True, env=env) if capture else subprocess.run(cmd, env=env)
        time.sleep(sleep_time)
        return result

    def setUp(self):
        # Use the local RPC URL here
        self.RPC_URL = "https://test.finney.opentensor.ai"
        # self.RPC_URL = "http://127.0.0.1:8545"
        self.w3 = Web3(Web3.HTTPProvider(self.RPC_URL))
        self.assertTrue(self.w3.is_connected(), "Cannot connect to Bittensor RPC")
        print("Connected to Bittensor RPC")

    def test_lifecycle(self):
        os.environ["RPC_URL"] = self.RPC_URL  # Setting the RPC URL for deployment
        env = os.environ.copy() 

        chain_id = self.w3.eth.chain_id
        print(f"Verified chain ID: {chain_id}")

        # Update script paths to match the updated folder structure
        deposit_script = "celium_collateral_contracts/deposit_collateral.py"
        get_miners_collateral_script = "celium_collateral_contracts/get_miners_collateral.py"
        get_eligible_executors_script = "celium_collateral_contracts/get_eligible_executors.py"
        reclaim_collateral_script = "celium_collateral_contracts/reclaim_collateral.py"
        deny_request_script = "celium_collateral_contracts/deny_request.py"
        finalize_reclaim_script = "celium_collateral_contracts/finalize_reclaim.py"
        get_reclaim_requests_script = "celium_collateral_contracts/get_reclaim_requests.py"
        if self.USE_EXISTING_ACCOUNTS:
            validator_address = "0xE1A07A44ac6f8423bA3b734F0cAfC6F87fd385Fc"
            validator_key = "434469242ece0d04889fdfa54470c3685ac226fb3756f5eaf5ddb6991e1698a3"
            miner_address = "0x19F71e76B34A8Dc01944Cf3B76478B45DE05B75b"
            miner_key = "259e0eded00353f71eb6be89d8749ad12bf693cbd8aeb6b80cd3a343c0dc8faf"
            validator_ss58 = h160_to_ss58(validator_address)
            miner_ss58 = h160_to_ss58(miner_address)
            print("Validator SS58:", validator_ss58)
            print("Miner SS58:", miner_ss58)

            # subprocess.run(["btcli", "w", "transfer", "--network", "local", "--dest", validator_ss58, "--amount", "0.5"])
            # time.sleep(3)

            # subprocess.run(["btcli", "w", "transfer", "--network", "local", "--dest", miner_ss58, "--amount", "3.5"])
            # time.sleep(3)

            balance = self.w3.eth.get_balance(validator_address)
            print("Validator Balance:", self.w3.from_wei(balance, 'ether'))
            
            balance = self.w3.eth.get_balance(miner_address)
            print("Miner Balance:", self.w3.from_wei(balance, 'ether'))

        else:
            # === Step 1: Create Validator Account ===
            validator = Account.create("extra entropy collateral contract Cellium")
            validator_address = validator.address
            validator_key = validator.key.hex()
            validator_ss58 = h160_to_ss58(validator_address)
            print("Validator Address:", validator_address)
            print("Validator Key:", validator_key)

            # === Step 2: Create Miner Account ===
            miner = Account.create("extra entropy MINER Cellium")
            miner_address = miner.address
            miner_key = miner.key.hex()
            miner_ss58 = h160_to_ss58(miner_address)
            print("Miner Address:", miner_address)
            print("Miner Key:", miner_key)

            # === Step 3: Fund Validator ===
            subprocess.run(["btcli", "w", "transfer", "--network", "test", "--dest", validator_ss58, "--amount", "0.5"])
            time.sleep(3)

            chain_id = self.w3.eth.chain_id
            print(f"Verified chain ID: {chain_id}")

            balance = self.w3.eth.get_balance(validator_address)
            print("Validator Balance:", self.w3.from_wei(balance, 'ether'))
            # === Step 4: Deploy Contract ===
            os.environ["DEPLOYER_PRIVATE_KEY"] = validator_key  # Setting the deployer's private key
            
            # Validate the required environment variables
            if not os.environ.get("RPC_URL"):
                raise ValueError("RPC_URL environment variable not set.")
            if not os.environ.get("DEPLOYER_PRIVATE_KEY"):
                raise ValueError("DEPLOYER_PRIVATE_KEY environment variable not set.")
            
            # === Step 5: Fund Miner ===
            subprocess.run(["btcli", "w", "transfer", "--network", "test", "--dest", miner_ss58, "--amount", "3.5"])
            time.sleep(3)
            self.assertGreater(self.w3.eth.get_balance(miner_address), 0, "Miner not funded")

            balance = self.w3.eth.get_balance(miner_address)
            print("Miner Balance:", self.w3.from_wei(balance, 'ether'))

         # Deploy using the `forge` command directly
        print("Deploying contract...", self.RPC_URL)
          # Define the arguments for deployment
        netuid = 1  # Example netuid
        min_collateral_increase = 1000000000000000  # Example amount in wei
        deny_timeout = 3600  # Example deny timeout in seconds

        if self.DEPLOY_CONTRACT:
            print("Deploying contract with forge...")
            deploy_result = subprocess.run(
                [
                    "forge", "create", "src/Collateral.sol:Collateral",
                    "--broadcast",
                    "--rpc-url", self.RPC_URL,
                    "--private-key", miner_key,
                    "--constructor-args", str(netuid), str(min_collateral_increase), str(deny_timeout)
                ],
                capture_output=True, text=True
            )
            self.assertIn("Deployed to:", deploy_result.stdout, deploy_result.stderr)
            contract_line = [line for line in deploy_result.stdout.splitlines() if "Deployed to:" in line][0]
            contract_address = contract_line.split(": ")[-1]
            self.assertTrue(Web3.is_address(contract_address))
        else:
            contract_address = "0x3512F750a13aF6EF0e62eCD8d4Badf779ea9033f"

        print("Deployed Contract Address:", contract_address)
        # === Step 6: Miner Deposits Collateral ===
        env["PRIVATE_KEY"] = miner_key

        print("Validator Address:", validator_address)
        print("Validator Key:", validator_key)

        print("Miner Address:", miner_address)
        print("Miner Key:", miner_key)

        executor_uuid = "72a1d228-3c8c-45cb-8b84-980071592589"  # Example UUID
        # Refactored deposit collateral steps as a loop
        deposit_tasks = [
            ("3a5ce92a-a066-45f7-b07d-58b3b7986464", False),
            ("72a1d228-3c8c-45cb-8b84-980071592589", False),
            ("15c2ff27-0a4d-4987-bbc9-fa009ef9f7d2", False),
            ("335453ad-246c-4ad5-809e-e2013ca6c07e", False),
            ("89c66519-244f-4db0-b4a7-756014d6fd24", False),
            ("af3f1b82-ff98-44c8-b130-d948a2a56b44", False),
            ("ee3002d9-71f8-4a83-881d-48bd21b6bdd1", False),
        ]
        # for uuid_str, capture_output in deposit_tasks:
        #     print(f"Starting deposit collateral for executor {uuid_str}...")
        #     result = self.run_cmd(
        #         [
        #             "python", deposit_script,
        #             "--contract-address", contract_address,
        #             "--amount-tao", "0.0001",
        #             "--validator-address", validator_address,
        #             "--executor-uuid", uuid_str
        #         ],
        #         env=env, capture=capture_output
        #     )
        #     if capture_output:
        #         print(result.stdout.strip())

        # === Step 7: Verify Collateral ===
        check = self.run_cmd(
            [
                "python", get_miners_collateral_script,
                "--contract-address", contract_address,
                "--miner-address", miner_address,
                "--network", "test"
            ],
            capture=True, env=env
        )

        print("[COLLATERAL]:", check.stdout.strip())
        print("Deposit collateral finished")

        print("Listing eligible executors before penalty...")

        executors = []
        for uuid_str, capture_output in deposit_tasks:
            executors.append(uuid_str)  # Keep original UUID strings

        executor_uuids_str = ",".join(executors)  # Join UUIDs with commas
        print("executor_uuids_str:", executor_uuids_str)

        result = self.run_cmd(
            [
                "python", get_eligible_executors_script,
                "--contract-address", contract_address,
                "--miner-address", miner_address,
                "--executor-uuids", executor_uuids_str,
                "--network", "test"
            ],
            capture=True,
            env=env
        )
        time.sleep(3)
        print("Result: ", result.stdout.strip())
        # Extract UUIDs from the result log
        result_output = result.stdout.strip()
        if "Eligible Executors:" in result_output:
            eligible_executors = result_output.split("Eligible Executors: ")[1].split(",")
            print("Eligible Executors as list:", eligible_executors)

        # === Step 9: Miner Reclaims Collateral ===
        print("Starting reclaim collateral...")
        result = self.run_cmd(
            [
                "python", reclaim_collateral_script,
                "--contract-address", contract_address,
                "--amount-tao", "0.00001",
                "--reason", "please gimme money back",
                "--executor-uuid", "72a1d228-3c8c-45cb-8b84-980071592589",
                "--network", "test"
            ],
            env=env
        )
        print("Reclaim Result: ", result.stdout.strip())

        # === Step 10: Validator Checks Requests ===
        latest_block = self.w3.eth.block_number
        print(f"All reclaim requests between these blocks: {latest_block - 10}, {latest_block + 10}")

        result = self.run_cmd(
            [
                "python", get_reclaim_requests_script,
                "--contract-address", contract_address,
                "--start-block", str(latest_block - 10),
                "--end-block", str(latest_block + 10),
                "--network", "test"
            ],
            env=env
        )

        deny_reclaim_id = 2
        finalize_reclaim_id = 1
        # === Step 11: Validator Denies Request 1, Finalizes Request 2 ===
        env["PRIVATE_KEY"] = validator_key
        print("Starting deny reclaim request")
        self.run_cmd(
            [
                "python", deny_request_script,
                "--contract-address", contract_address,
                "--reclaim-id", str(deny_reclaim_id),
                "--reason", "no, i will not",
                "--network", "test"
            ],
            env=env
        )

        print("Deny reclaim request finished")

        print("Starting finalize reclaim request")
        self.run_cmd(
            [
                "python", finalize_reclaim_script,
                "--contract-address", contract_address,
                "--reclaim-id", str(finalize_reclaim_id),
                "--network", "test"
            ],
            env=env
        )

        # === Step 12: Final Collateral Check ===
        result = self.run_cmd(
            [
                "python", get_miners_collateral_script,
                "--contract-address", contract_address,
                "--miner-address", miner_address,
                "--network", "test"
            ],
            capture=True, env=env
        )
        print("[FINAL COLLATERAL]:", result.stdout.strip())

        print("Checking account balances before transfer...")
        print("Validator balance:", self.w3.from_wei(self.w3.eth.get_balance(validator_address), 'ether'))
        print("Miner balance:", self.w3.from_wei(self.w3.eth.get_balance(miner_address), 'ether'))

        validator_transferrable = get_transferrable_balance(self.w3, validator_address, "0x0000000000000000000000000000000000000001")
        miner_transferrable = get_transferrable_balance(self.w3, miner_address, "0x0000000000000000000000000000000000000001")
        
        print("validator_transferrable:", validator_transferrable)
        print("miner_transferrable:", miner_transferrable)

        print("Validator transferrable balance:", self.w3.from_wei(validator_transferrable, 'ether'))
        print("Miner transferrable balance:", self.w3.from_wei(miner_transferrable, 'ether'))

        print("Checking account balances after transfer...")

        print("Validator balance:", self.w3.from_wei(self.w3.eth.get_balance(validator_address), 'ether'))
        print("Miner balance:", self.w3.from_wei(self.w3.eth.get_balance(miner_address), 'ether'))

        print("✅ Contract lifecycle test completed successfully.")


if __name__ == "__main__":
    # If running via unittest discovery, custom flags will not be recognized.
    if any(arg.startswith("--use_existing_accounts") or arg.startswith("--deploy_contract")
           for arg in sys.argv[1:]):
        print("WARNING: Custom flags are not supported when using 'python -m unittest'.")
        print("Run this file directly instead, for example:")
        print("  python unittests/test_collateral_flow.py --use_existing_accounts False")

    import argparse
    parser = argparse.ArgumentParser(description="Override test parameters")
    parser.add_argument("--use_existing_accounts", choices=["True", "False"],
                        help="Override USE_EXISTING_ACCOUNTS", default=None)
    parser.add_argument("--deploy_contract", choices=["True", "False"],
                        help="Override DEPLOY_CONTRACT", default=None)
    args, remaining = parser.parse_known_args()
    if args.use_existing_accounts is not None:
        TestCollateralContractLifecycle.USE_EXISTING_ACCOUNTS = (args.use_existing_accounts == "True")
    if args.deploy_contract is not None:
        TestCollateralContractLifecycle.DEPLOY_CONTRACT = (args.deploy_contract == "True")
    sys.argv = [sys.argv[0]] + remaining
    unittest.main()
