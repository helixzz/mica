from __future__ import annotations

from decimal import Decimal, InvalidOperation

CURRENCY_SYMBOLS: dict[str, str] = {
    "CNY": "¥",
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "JPY": "¥",
    "KRW": "₩",
    "HKD": "HK$",
    "TWD": "NT$",
}


def currency_symbol(currency: str | None) -> str:
    if not currency:
        return "¥"
    return CURRENCY_SYMBOLS.get(currency.upper(), currency)


def fmt_amount(
    amount: Decimal | float | int | str | None,
    currency: str | None = "CNY",
    *,
    empty: str = "—",
) -> str:
    if amount is None or amount == "":
        return empty
    try:
        d = Decimal(str(amount)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        return empty
    return f"{currency_symbol(currency)}{d:,.2f}"


def fmt_amount_with_code(
    amount: Decimal | float | int | str | None,
    currency: str | None = "CNY",
    *,
    empty: str = "—",
) -> str:
    if amount is None or amount == "":
        return empty
    try:
        d = Decimal(str(amount)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        return empty
    code = (currency or "CNY").upper()
    return f"{currency_symbol(code)}{d:,.2f} {code}"
