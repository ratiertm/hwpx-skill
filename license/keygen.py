"""License key generation and validation."""
import secrets
import hmac
import hashlib
from . import config


def generate_key() -> str:
    """Generate a signed license key: HWPX-XXXX-XXXX-XXXX"""
    raw = secrets.token_hex(6).upper()  # 12 hex chars
    parts = [raw[i:i+4] for i in range(0, 12, 4)]
    body = f"{config.KEY_PREFIX}-{'-'.join(parts)}"

    # Append HMAC checksum (4 chars)
    sig = hmac.new(
        config.HMAC_SECRET.encode(),
        body.encode(),
        hashlib.sha256,
    ).hexdigest()[:4].upper()

    return f"{body}-{sig}"


def verify_key_format(key: str) -> bool:
    """Verify key format and HMAC signature."""
    parts = key.split("-")
    if len(parts) != 5 or parts[0] != config.KEY_PREFIX:
        return False

    body = "-".join(parts[:4])
    sig = parts[4]

    expected = hmac.new(
        config.HMAC_SECRET.encode(),
        body.encode(),
        hashlib.sha256,
    ).hexdigest()[:4].upper()

    return hmac.compare_digest(sig, expected)
