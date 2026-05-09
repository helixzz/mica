from __future__ import annotations

import json
import logging
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.system_params import system_params

logger = logging.getLogger(__name__)

_DEFAULT_RATES: dict[str, float] = {
    "USD_CNY": 7.25,
    "EUR_CNY": 7.85,
    "JPY_CNY": 0.048,
    "GBP_CNY": 9.20,
    "HKD_CNY": 0.93,
}


async def get_rates(db: AsyncSession) -> dict[str, float]:
    raw = await system_params.get(db, "currency.exchange_rates", _DEFAULT_RATES)
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            logger.warning("currency.exchange_rates is not valid JSON, using defaults")
            return dict(_DEFAULT_RATES)
    if not isinstance(raw, dict):
        return dict(_DEFAULT_RATES)
    rates: dict[str, float] = {}
    for k, v in raw.items():
        try:
            rates[str(k)] = float(v)
        except (TypeError, ValueError):
            continue
    return rates


async def convert_amount(
    db: AsyncSession,
    amount: Decimal | float | int,
    from_currency: str,
    to_currency: str,
) -> Decimal:
    amount_d = Decimal(str(amount))
    if from_currency == to_currency:
        return amount_d
    rates = await get_rates(db)
    pair = f"{from_currency}_{to_currency}"
    rate = rates.get(pair)
    if rate is not None:
        return (amount_d * Decimal(str(rate))).quantize(Decimal("0.01"))
    inverse_pair = f"{to_currency}_{from_currency}"
    inverse_rate = rates.get(inverse_pair)
    if inverse_rate is not None:
        return (amount_d / Decimal(str(inverse_rate))).quantize(Decimal("0.01"))
    return amount_d
