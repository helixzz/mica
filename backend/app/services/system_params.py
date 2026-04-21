from __future__ import annotations

import asyncio
import copy
import json
from decimal import Decimal, InvalidOperation
from typing import cast
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, JSONValue, SystemParameter, User

_MISSING = object()
_FLOAT_LIKE = (int, float, str)


class SystemParamsService:
    """Cached read-through, write-through invalidation."""

    def __init__(self) -> None:
        self._cache: dict[str, JSONValue] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def _load_param(self, session: AsyncSession, key: str) -> SystemParameter | None:
        return (
            await session.execute(select(SystemParameter).where(SystemParameter.key == key))
        ).scalar_one_or_none()

    async def _require_param(self, session: AsyncSession, key: str) -> SystemParameter:
        param = await self._load_param(session, key)
        if param is None:
            raise HTTPException(404, f"system_parameter.not_found:{key}")
        return param

    async def get_param(self, session: AsyncSession, key: str) -> SystemParameter | None:
        return await self._load_param(session, key)

    def _json_value(self, value: JSONValue | object) -> str:
        try:
            return json.dumps(value, ensure_ascii=False)
        except TypeError:
            return json.dumps(str(value), ensure_ascii=False)

    def _to_decimal(self, value: JSONValue | object, key: str) -> Decimal:
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise HTTPException(400, f"system_parameter.invalid_numeric:{key}") from exc

    def _normalize_value(self, key: str, data_type: str, value: JSONValue | object) -> JSONValue:
        if data_type == "int":
            if isinstance(value, bool):
                raise HTTPException(400, f"system_parameter.invalid_type:{key}:int")
            if isinstance(value, int):
                return value
            if isinstance(value, str):
                try:
                    return int(value)
                except ValueError as exc:
                    raise HTTPException(400, f"system_parameter.invalid_type:{key}:int") from exc
            raise HTTPException(400, f"system_parameter.invalid_type:{key}:int")
        if data_type == "float":
            if isinstance(value, bool):
                raise HTTPException(400, f"system_parameter.invalid_type:{key}:float")
            if not isinstance(value, _FLOAT_LIKE):
                raise HTTPException(400, f"system_parameter.invalid_type:{key}:float")
            try:
                return float(value)
            except (TypeError, ValueError) as exc:
                raise HTTPException(400, f"system_parameter.invalid_type:{key}:float") from exc
        if data_type == "bool":
            if not isinstance(value, bool):
                raise HTTPException(400, f"system_parameter.invalid_type:{key}:bool")
            return value
        if data_type == "string":
            if not isinstance(value, str):
                raise HTTPException(400, f"system_parameter.invalid_type:{key}:string")
            return value
        if data_type == "decimal":
            return str(self._to_decimal(value, key))
        raise HTTPException(400, f"system_parameter.invalid_data_type:{data_type}")

    def _validate_bounds(
        self,
        key: str,
        data_type: str,
        value: JSONValue,
        min_value: JSONValue | None,
        max_value: JSONValue | None,
    ) -> None:
        if data_type not in {"int", "float", "decimal"}:
            return
        numeric_value = self._to_decimal(value, key)
        if min_value is not None and numeric_value < self._to_decimal(min_value, key):
            raise HTTPException(400, f"system_parameter.below_min:{key}")
        if max_value is not None and numeric_value > self._to_decimal(max_value, key):
            raise HTTPException(400, f"system_parameter.above_max:{key}")

    async def get(
        self, session: AsyncSession, key: str, default: JSONValue | object = None
    ) -> JSONValue | object:
        cached = self._cache.get(key, _MISSING)
        if cached is not _MISSING:
            return copy.deepcopy(cached)

        async with self._lock:
            cached = self._cache.get(key, _MISSING)
            if cached is not _MISSING:
                return copy.deepcopy(cached)
            param = await self._load_param(session, key)
            if param is None:
                return default
            self._cache[key] = copy.deepcopy(param.value)
            return copy.deepcopy(param.value)

    async def get_int_or(self, session: AsyncSession, key: str, default: int) -> int:
        value = await self.get(session, key, default)
        if isinstance(value, bool) or not isinstance(value, int):
            return default
        return value

    async def get_int(self, session: AsyncSession, key: str) -> int:
        value = await self.get(session, key, _MISSING)
        if value is _MISSING or isinstance(value, bool) or not isinstance(value, int):
            raise HTTPException(500, f"system_parameter.invalid_int:{key}")
        return value

    async def get_decimal(self, session: AsyncSession, key: str) -> Decimal:
        value = await self.get(session, key, _MISSING)
        if value is _MISSING:
            raise HTTPException(500, f"system_parameter.invalid_decimal:{key}")
        try:
            return Decimal(str(cast(JSONValue, value)))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise HTTPException(500, f"system_parameter.invalid_decimal:{key}") from exc

    async def get_all(
        self, session: AsyncSession, category: str | None = None
    ) -> list[SystemParameter]:
        stmt = select(SystemParameter).order_by(SystemParameter.category, SystemParameter.key)
        if category:
            stmt = stmt.where(SystemParameter.category == category)
        return list((await session.execute(stmt)).scalars().all())

    async def _write_audit_log(
        self,
        session: AsyncSession,
        *,
        key: str,
        old_value: JSONValue,
        new_value: JSONValue,
        updated_by_id: str,
        event_type: str,
    ) -> None:
        actor = await session.get(User, UUID(updated_by_id))
        session.add(
            AuditLog(
                actor_id=UUID(updated_by_id),
                actor_name=actor.display_name if actor else None,
                event_type=event_type,
                resource_type="system_parameter",
                resource_id=key,
                metadata_json={
                    "key": key,
                    "old_value": old_value,
                    "new_value": new_value,
                },
                comment=(
                    f"system_parameter.{key} changed from "
                    f"{self._json_value(old_value)} to {self._json_value(new_value)}"
                ),
            )
        )

    async def _apply_update(
        self,
        session: AsyncSession,
        key: str,
        value: JSONValue | object,
        updated_by_id: str,
        *,
        event_type: str,
    ) -> SystemParameter:
        param = await self._require_param(session, key)
        new_value = self._normalize_value(key, param.data_type, value)
        self._validate_bounds(key, param.data_type, new_value, param.min_value, param.max_value)
        old_value = copy.deepcopy(param.value)
        param.value = new_value
        param.updated_by_id = UUID(updated_by_id)
        await self._write_audit_log(
            session,
            key=key,
            old_value=old_value,
            new_value=new_value,
            updated_by_id=updated_by_id,
            event_type=event_type,
        )
        await session.flush()
        self.invalidate(key)
        return param

    async def update(
        self, session: AsyncSession, key: str, value: JSONValue | object, updated_by_id: str
    ) -> SystemParameter:
        return await self._apply_update(
            session,
            key,
            value,
            updated_by_id,
            event_type="admin.system_parameter.updated",
        )

    async def reset(self, session: AsyncSession, key: str, updated_by_id: str) -> SystemParameter:
        param = await self._require_param(session, key)
        return await self._apply_update(
            session,
            key,
            copy.deepcopy(param.default_value),
            updated_by_id,
            event_type="admin.system_parameter.reset",
        )

    def invalidate(self, key: str | None = None) -> None:
        if key is None:
            self._cache.clear()
            return
        _ = self._cache.pop(key, None)


system_params = SystemParamsService()
