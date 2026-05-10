from __future__ import annotations

from enum import Enum
import re


EVM_ADDRESS_PATTERN = re.compile(r"^0x[a-fA-F0-9]{40}$")
TON_RAW_ADDRESS_PATTERN = re.compile(r"^-?\d:[a-fA-F0-9]{64}$")
TON_USER_FRIENDLY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{48}$")

EVM_ADDRESS_SUBSTRING_PATTERN = re.compile(r"0[xX][a-fA-F0-9]{40}")
TON_RAW_ADDRESS_SUBSTRING_PATTERN = re.compile(r"-?\d:[a-fA-F0-9]{64}")
TON_USER_FRIENDLY_SUBSTRING_PATTERN = re.compile(r"[A-Za-z0-9_-]{48}")


class AddressFamily(str, Enum):
    EVM = "EVM"
    TON = "TON"
    UNKNOWN = "UNKNOWN"


_ZERO_WIDTH_CHARS = (
    "\u200b",  # zero width space
    "\u200c",  # zero width non-joiner
    "\u200d",  # zero width joiner
    "\u2060",  # word joiner
    "\ufeff",  # zero width no-break space / BOM
)


def _normalize_address_text(address: str) -> str:
    normalized = address.strip()
    for ch in _ZERO_WIDTH_CHARS:
        if ch in normalized:
            normalized = normalized.replace(ch, "")

    normalized = normalized.strip()

    # Some users copy EVM addresses with uppercase X (0X...).
    if normalized.startswith("0X"):
        normalized = "0x" + normalized[2:]

    return normalized


def detect_address_family(address: str) -> AddressFamily:
    normalized = _normalize_address_text(address)

    if EVM_ADDRESS_PATTERN.fullmatch(normalized):
        return AddressFamily.EVM

    if TON_RAW_ADDRESS_PATTERN.fullmatch(normalized):
        return AddressFamily.TON

    if TON_USER_FRIENDLY_PATTERN.fullmatch(normalized):
        return AddressFamily.TON

    return AddressFamily.UNKNOWN


def extract_wallet_address(text: str) -> str | None:
    """Attempt to extract a supported wallet address from arbitrary user input.

    This makes copy/paste more forgiving (e.g. full explorer URLs, extra spaces,
    or labels like "address: 0x...").
    """

    normalized = _normalize_address_text(text)
    if detect_address_family(normalized) is not AddressFamily.UNKNOWN:
        return normalized

    candidates: list[str] = []
    for pattern in (
        EVM_ADDRESS_SUBSTRING_PATTERN,
        TON_RAW_ADDRESS_SUBSTRING_PATTERN,
        TON_USER_FRIENDLY_SUBSTRING_PATTERN,
    ):
        match = pattern.search(normalized)
        if match:
            candidates.append(match.group(0))

    for candidate in candidates:
        normalized_candidate = _normalize_address_text(candidate)
        if detect_address_family(normalized_candidate) is not AddressFamily.UNKNOWN:
            return normalized_candidate

    return None


def is_valid_wallet_address(address: str) -> bool:
    return detect_address_family(address) in {AddressFamily.EVM, AddressFamily.TON}
