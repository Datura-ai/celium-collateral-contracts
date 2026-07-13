"""Tests for h160_to_ss58 after the scalecodec -> base58 port.

Expected values were generated with scalecodec.ss58_encode 1.2.11 (the previous
implementation) to guarantee the port is byte-identical.
"""

import pytest

from celium_collateral_contracts.address_conversion import _ss58_encode, h160_to_ss58

# (h160, ss58 with default format 42) — oracle: scalecodec 1.2.11
KNOWN_VECTORS = [
    ("0x0000000000000000000000000000000000000000", "5GU8HU4cLcmjpoXLNxWAHYViwbTQggdqd7ykp99CSWGbsZHG"),
    ("0xffffffffffffffffffffffffffffffffffffffff", "5H888cCjB9owfgqkGnTgiWVcV9EFP4tDBntFS1VWvA1rLoTc"),
    ("0xdEAD000000000000000042069420694206942069", "5DFRQCpursXzi1ssb4UdYs5RVatBie9QgjnvsgCGF6rqWE5x"),
    ("0x9fA2C1F6a1a83E43fa06Cd7DE9c56e6a71A29A29", "5ESxHrFS1q6WNfhsK8U1tC1H1XxrKULfU4qGhZsQ5ENN1Soa"),
]


def test_h160_to_ss58_matches_scalecodec_vectors():
    # Arrange
    for h160, expected in KNOWN_VECTORS:
        # Act
        result = h160_to_ss58(h160)

        # Assert
        assert result == expected


def test_h160_to_ss58_accepts_unprefixed_address():
    # Arrange
    h160, expected = KNOWN_VECTORS[0]

    # Act
    result = h160_to_ss58(h160[2:])

    # Assert
    assert result == expected


def test_ss58_encode_rejects_reserved_formats():
    # Arrange
    address = bytes(32)

    # Act / Assert
    for bad_format in (46, 47, -1, 16384):
        with pytest.raises(ValueError):
            _ss58_encode(address, bad_format)


def test_ss58_encode_rejects_non_32_byte_address():
    # Arrange
    address = bytes(20)

    # Act / Assert
    with pytest.raises(ValueError):
        _ss58_encode(address, 42)
