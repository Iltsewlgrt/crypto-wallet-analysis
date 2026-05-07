from __future__ import annotations

from enum import Enum
import re


EVM_ADDRESS_PATTERN = re.compile(r"^0x[a-fA-F0-9]{40}$")
TON_RAW_ADDRESS_PATTERN = re.compile(r"^-?\d:[a-fA-F0-9]{64}$")
TON_USER_FRIENDLY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{48}$")


class AddressFamily(str, Enum):
    EVM = "EVM"
    TON = "TON"
    UNKNOWN = "UNKNOWN"


def detect_address_family(address: str) -> AddressFamily:
    normalized = address.strip()

    if EVM_ADDRESS_PATTERN.fullmatch(normalized):
        return AddressFamily.EVM

    if TON_RAW_ADDRESS_PATTERN.fullmatch(normalized):
        return AddressFamily.TON

    if TON_USER_FRIENDLY_PATTERN.fullmatch(normalized):
        return AddressFamily.TON

    return AddressFamily.UNKNOWN


def is_valid_wallet_address(address: str) -> bool:
    return detect_address_family(address) in {AddressFamily.EVM, AddressFamily.TON}
