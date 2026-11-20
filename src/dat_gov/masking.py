"""PII masking and hashing.

Governance concept demonstrated: PII is never copied in clear into Gold.
Crew email / phone / passport / seafarer ID are classified in the contracts,
hashed deterministically (SHA-256, so the same person joins the same way
every run) or masked for display, and Gold marts contain neither.
"""

from __future__ import annotations

import hashlib


def hash_value(value: str | None, salt: str = "northgate-maritime") -> str | None:
    """Deterministic SHA-256 hash (hex) of a PII value; None stays None."""
    if value is None or value == "":
        return None
    return hashlib.sha256(f"{salt}:{value}".encode()).hexdigest()


def mask_email(email: str | None) -> str | None:
    """Keep the domain, mask the local part: j***@example.com."""
    if not email or "@" not in email:
        return email
    local, domain = email.split("@", 1)
    return f"{local[:1]}***@{domain}" if local else f"***@{domain}"


def mask_phone(phone: str | None) -> str | None:
    """Show only the last two digits: +44******42."""
    if not phone:
        return phone
    digits = "".join(c for c in phone if c.isdigit())
    return f"******{digits[-2:]}" if len(digits) >= 2 else "******"


def mask_passport(value: str | None) -> str | None:
    """Show only the last two characters of a passport / seafarer ID."""
    if not value:
        return value
    return f"{'*' * max(len(value) - 2, 0)}{value[-2:]}"


def mask_generic(value: str | None, keep_last: int = 2) -> str | None:
    """Mask all but the last ``keep_last`` characters."""
    if not value:
        return value
    return f"{'*' * max(len(value) - keep_last, 0)}{value[-keep_last:]}"
