"""Delivery address book endpoints.

Any signed-in user may list the entries visible to them and maintain their own
private entries. Company-wide entries additionally require ``admin`` or
``procurement_mgr``; that check lives in the service layer because it depends on
the *entry's* owner rather than on the route.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.db import get_db
from app.schemas import (
    DeliveryAddressIn,
    DeliveryAddressOut,
    DeliveryAddressUpdateIn,
)
from app.services import delivery_addresses as address_svc

router = APIRouter()


@router.get("/delivery-addresses", response_model=list[DeliveryAddressOut], tags=["purchase"])
async def list_delivery_addresses(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    include_inactive: Annotated[bool, Query()] = False,
) -> list[DeliveryAddressOut]:
    addresses = await address_svc.list_addresses(db, user, include_inactive=include_inactive)
    return [DeliveryAddressOut.model_validate(a) for a in addresses]


@router.post(
    "/delivery-addresses",
    response_model=DeliveryAddressOut,
    status_code=status.HTTP_201_CREATED,
    tags=["purchase"],
)
async def create_delivery_address(
    payload: DeliveryAddressIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliveryAddressOut:
    address = await address_svc.create_address(db, user, payload)
    return DeliveryAddressOut.model_validate(address)


@router.patch(
    "/delivery-addresses/{address_id}",
    response_model=DeliveryAddressOut,
    tags=["purchase"],
)
async def update_delivery_address(
    address_id: UUID,
    payload: DeliveryAddressUpdateIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliveryAddressOut:
    address = await address_svc.update_address(db, user, address_id, payload)
    return DeliveryAddressOut.model_validate(address)


@router.delete(
    "/delivery-addresses/{address_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["purchase"],
)
async def delete_delivery_address(
    address_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    await address_svc.delete_address(db, user, address_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
