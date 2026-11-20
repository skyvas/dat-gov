"""PII masking helpers.

Governance idea demonstrated here: direct identifiers must never reach
Gold. Silver keeps them (classified and tagged, for operational use by
authorised roles); Gold either drops them or carries only a masked /
hashed form. Masking is deterministic so the same person always maps to
the same token, which lets analysts join Gold tables without ever seeing
the raw value.
"""

from __future__ import annotations

import hashlib
import re

_SALT = "northbridge-university-dat-gov-v1"


def hash_value(value: str | None) -> str | None:
    """Deterministic SHA-256 hash of a value (with a fixed project salt).

    Returns None for None/empty input. The same input always yields the
    same output, and the output cannot be reversed to the input.
    """
    if value is None or str(value).strip() == "":
        return None
    return hashlib.sha256(f"{_SALT}|{value}".encode("utf-8")).hexdigest()


def mask_email(email: str | None) -> str | None:
    """Keep the domain, mask the local part: ``j***@example.edu``."""
    if not email or "@" not in str(email):
        return None
    local, domain = str(email).rsplit("@", 1)
    return f"{local[:1]}***@{domain}" if local else f"***@{domain}"


def mask_phone(phone: str | None) -> str | None:
    """Keep only the last 4 digits: ``***-***-1234``."""
    if not phone:
        return None
    digits = re.sub(r"\D", "", str(phone))
    return f"***-***-{digits[-4:]}" if len(digits) >= 4 else "***-***-****"


def mask_gov_id(gov_id: str | None) -> str | None:
    """Government IDs are never shown, even masked — only a hash is kept."""
    return hash_value(gov_id)


def is_pii_column(column: str) -> bool:
    """True for the direct-identifier columns used across this project."""
    return column in {"email", "phone", "gov_id", "first_name", "last_name"}
