#!/usr/bin/env python3
"""
Address Conversion Utilities

This module provides functions for converting between different address formats
used in blockchain systems. It supports conversion between SS58 addresses (used
in Substrate-based chains) and H160 addresses (Ethereum-style addresses).
"""
import hashlib

import base58

_SS58_CHECKSUM_PREFIX = b"SS58PRE"


def _ss58_encode(address_bytes: bytes, ss58_format: int) -> str:
    # base58 + blake2b port of scalecodec.ss58_encode for 32-byte public keys
    if ss58_format < 0 or ss58_format > 16383 or ss58_format in (46, 47):
        raise ValueError("Invalid value for ss58_format")

    if len(address_bytes) != 32:
        raise ValueError("Expected a 32-byte address")

    if ss58_format < 64:
        format_bytes = bytes([ss58_format])
    else:
        format_bytes = bytes(
            [
                ((ss58_format & 0b0000_0000_1111_1100) >> 2) | 0b0100_0000,
                (ss58_format >> 8) | ((ss58_format & 0b0000_0000_0000_0011) << 6),
            ]
        )

    payload = format_bytes + address_bytes
    checksum = hashlib.blake2b(_SS58_CHECKSUM_PREFIX + payload).digest()[:2]

    return base58.b58encode(payload + checksum).decode()


# https://github.com/opentensor/evm-bittensor/blob/main/examples/address-mapping.js
def h160_to_ss58(h160_address: str, ss58_format: int = 42) -> str:
    """
    Convert H160 (Ethereum address to SS58 address.

    Args:
        h160_address (str): The H160 address to convert ('0x' prefixed or not)

    Returns:
        str: The ss58 address
    """
    if h160_address.startswith("0x"):
        h160_address = h160_address[2:]

    address_bytes = bytes.fromhex(h160_address)

    prefixed_address = bytes("evm:", "utf-8") + address_bytes

    checksum = hashlib.blake2b(prefixed_address, digest_size=32).digest()

    return _ss58_encode(checksum, ss58_format=ss58_format)
