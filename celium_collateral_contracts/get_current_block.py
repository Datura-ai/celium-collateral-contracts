import argparse
import asyncio

from celium_collateral_contracts.common import get_web3_connection


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--network", default="finney")
    args = parser.parse_args()

    w3 = get_web3_connection(args.network)
    block = await w3.eth.get_block('latest')['number']
    print(block)


if __name__ == "__main__":
    asyncio.run(main())
