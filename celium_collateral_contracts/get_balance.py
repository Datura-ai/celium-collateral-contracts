import argparse
import asyncio

from celium_collateral_contracts.common import get_web3_connection

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("address")
    parser.add_argument("--network", default="finney")
    args = parser.parse_args()

    w3 = get_web3_connection(args.network)
    balance = await w3.eth.get_balance(args.address)

    print("Account Balance:", w3.from_wei(balance, "ether"))
    print("Account Balance (wei):", balance)


if __name__ == "__main__":
    asyncio.run(main())
