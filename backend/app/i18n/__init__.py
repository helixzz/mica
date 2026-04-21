"""Lightweight i18n for backend messages (errors, notifications).

Frontend handles UI strings; backend only translates machine-facing messages.
"""

import json
from functools import lru_cache
from pathlib import Path

from fastapi import Request

from app.config import get_settings

settings = get_settings()
MESSAGES_DIR = Path(__file__).parent / "messages"


@lru_cache(maxsize=8)
def _load_messages(locale: str) -> dict:
    path = MESSAGES_DIR / f"{locale}.json"
    if not path.exists():
        path = MESSAGES_DIR / f"{settings.default_locale}.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def detect_locale(request: Request) -> str:
    """Extract locale from Accept-Language header, validating against supported list."""
    accept = request.headers.get("accept-language", "")
    if not accept:
        return settings.default_locale
    # Parse simple "zh-CN,zh;q=0.9,en;q=0.8" style
    for part in accept.split(","):
        lang = part.split(";")[0].strip()
        if lang in settings.supported_locales:
            return lang
        # Try prefix match: "zh" matches "zh-CN"
        for supported in settings.supported_locales:
            if supported.startswith(lang.split("-")[0]):
                return supported
    return settings.default_locale


def t(key: str, locale: str | None = None, **kwargs) -> str:
    """Translate a key. Uses dot notation: 'auth.invalid_credentials'."""
    locale = locale or settings.default_locale
    messages = _load_messages(locale)
    parts = key.split(".")
    value: dict | str = messages
    for p in parts:
        if isinstance(value, dict):
            value = value.get(p, key)
        else:
            return key
    if isinstance(value, str) and kwargs:
        try:
            return value.format(**kwargs)
        except KeyError:
            return value
    return value if isinstance(value, str) else key
