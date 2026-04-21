from __future__ import annotations

import base64
import hashlib
import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    raw = os.environ.get("AI_ENCRYPTION_KEY")
    if raw:
        try:
            return Fernet(raw.encode())
        except (ValueError, TypeError):
            pass
    secret = os.environ.get("SECRET_KEY", "mica-dev-secret-key-fallback-for-local-only-usage")
    digest = hashlib.sha256(secret.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        return ""
