"""HMAC-SHA256 signature verification for bank webhooks."""

import hashlib
import hmac


def compute_signature(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def verify_signature(body: bytes, signature: str | None, secret: str) -> bool:
    if signature is None:
        return False
    expected = compute_signature(body, secret)
    return hmac.compare_digest(expected, signature)
