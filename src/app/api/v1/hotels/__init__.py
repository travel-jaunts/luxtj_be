from typing import Dict, Any, Annotated, Optional
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func, select
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Request, Depends

from app.core.logging import get_logger
from app.core.database import get_db, Base


router = APIRouter(prefix="/hotels", tags=["hotels"])
logger = get_logger(__name__)


class HotelNotFoundError(Exception):
    def __init__(self, hotel_id: int) -> None:
        self.hotel_id = hotel_id
        super().__init__(f"Hotel with id={hotel_id} not found.")


class HotelUpdateEmptyError(Exception):
    def __init__(self) -> None:
        super().__init__("At least one field must be provided for update.")


class Hotel(Base):
    __tablename__ = "hotels"
    __table_args__ = {"schema": "s_luxtj"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    stars: Mapped[int] = mapped_column(Integer, nullable=False)
    price_per_night: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class HotelRepository:
    """Pure data-access layer. No business logic — only DB interactions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: dict) -> Hotel:
        hotel = Hotel(**data)
        self._session.add(hotel)
        await self._session.commit()
        await self._session.refresh(hotel)
        return hotel

    async def get_by_id(self, hotel_id: int) -> Optional[Hotel]:
        return await self._session.get(Hotel, hotel_id)

    async def list_filtered(
        self,
        city: Optional[str],
        country: Optional[str],
        min_stars: Optional[int],
        max_price: Optional[float],
        offset: int,
        limit: int,
    ) -> tuple[list[Hotel], int]:
        query = select(Hotel)

        if city:
            query = query.where(Hotel.city.ilike(f"%{city}%"))
        if country:
            query = query.where(Hotel.country.ilike(f"%{country}%"))
        if min_stars is not None:
            query = query.where(Hotel.stars >= min_stars)
        if max_price is not None:
            query = query.where(Hotel.price_per_night <= max_price)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self._session.execute(count_query)).scalar_one()

        result = await self._session.execute(query.offset(offset).limit(limit))
        hotels = list(result.scalars().all())

        return hotels, total

    async def update(self, hotel: Hotel, changes: dict) -> Hotel:
        for field, value in changes.items():
            setattr(hotel, field, value)
        await self._session.commit()
        await self._session.refresh(hotel)
        return hotel

    async def delete(self, hotel: Hotel) -> int:
        hotel_id = hotel.id
        await self._session.delete(hotel)
        await self._session.commit()
        return hotel_id


def get_hotel_repository(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> HotelRepository:
    return HotelRepository(session)


from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ── Request Payloads ──────────────────────────────────────────────────────────


class HotelCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    address: str = Field(..., min_length=1, max_length=500)
    city: str = Field(..., min_length=1, max_length=100)
    country: str = Field(..., min_length=1, max_length=100)
    stars: int = Field(..., ge=1, le=5)
    price_per_night: float = Field(..., gt=0)
    description: Optional[str] = Field(None, max_length=2000)


class HotelUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    address: Optional[str] = Field(None, min_length=1, max_length=500)
    city: Optional[str] = Field(None, min_length=1, max_length=100)
    country: Optional[str] = Field(None, min_length=1, max_length=100)
    stars: Optional[int] = Field(None, ge=1, le=5)
    price_per_night: Optional[float] = Field(None, gt=0)
    description: Optional[str] = Field(None, max_length=2000)

    @field_validator("*", mode="before")
    @classmethod
    def at_least_one_field(cls, v):
        return v


class HotelGetRequest(BaseModel):
    id: int = Field(..., gt=0)


class HotelDeleteRequest(BaseModel):
    id: int = Field(..., gt=0)


class HotelListRequest(BaseModel):
    city: Optional[str] = None
    country: Optional[str] = None
    min_stars: Optional[int] = Field(None, ge=1, le=5)
    max_price: Optional[float] = Field(None, gt=0)
    offset: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)


# ── Response Payloads ─────────────────────────────────────────────────────────


class HotelResponse(BaseModel):
    id: int
    name: str
    address: str
    city: str
    country: str
    stars: int
    price_per_night: float
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class HotelListResponse(BaseModel):
    items: list[HotelResponse]
    total: int
    offset: int
    limit: int


class DeleteResponse(BaseModel):
    id: int
    deleted: bool = True


class HotelService:
    """Orchestrates business rules and translates between schemas and models."""

    def __init__(self, repository: HotelRepository) -> None:
        self._repo = repository

    async def create_hotel(self, payload: HotelCreateRequest) -> HotelResponse:
        hotel = await self._repo.create(payload.model_dump(exclude_none=False))
        return HotelResponse.model_validate(hotel)

    async def get_hotel(self, hotel_id: int) -> HotelResponse:
        hotel = await self._repo.get_by_id(hotel_id)
        if hotel is None:
            raise HotelNotFoundError(hotel_id)
        return HotelResponse.model_validate(hotel)

    async def list_hotels(self, filters: HotelListRequest) -> HotelListResponse:
        hotels, total = await self._repo.list_filtered(
            city=filters.city,
            country=filters.country,
            min_stars=filters.min_stars,
            max_price=filters.max_price,
            offset=filters.offset,
            limit=filters.limit,
        )
        return HotelListResponse(
            items=[HotelResponse.model_validate(h) for h in hotels],
            total=total,
            offset=filters.offset,
            limit=filters.limit,
        )

    async def update_hotel(self, hotel_id: int, payload: HotelUpdateRequest) -> HotelResponse:
        changes = payload.model_dump(exclude_none=True)
        if not changes:
            raise HotelUpdateEmptyError()

        hotel = await self._repo.get_by_id(hotel_id)
        if hotel is None:
            raise HotelNotFoundError(hotel_id)

        updated = await self._repo.update(hotel, changes)
        return HotelResponse.model_validate(updated)

    async def delete_hotel(self, hotel_id: int) -> DeleteResponse:
        hotel = await self._repo.get_by_id(hotel_id)
        if hotel is None:
            raise HotelNotFoundError(hotel_id)

        deleted_id = await self._repo.delete(hotel)
        return DeleteResponse(id=deleted_id)


def get_hotel_service(
    repository: Annotated[HotelRepository, Depends(get_hotel_repository)],
) -> HotelService:
    return HotelService(repository)


# =================================================================================================
@router.post("/search")
async def get_hotels(request: Request, service: HotelService = Depends(get_hotel_service)):
    data = await service.list_hotels(
        filters=HotelListRequest(min_stars=1, max_price=10000, offset=0, limit=10)
    )
    return {
        "status": "ok",
        "data": {
            "hotels": [
                {
                    "id": item.id,
                    "name": item.name,
                    "location": f"{item.city}, {item.country}",
                    "rating": item.stars,
                    "price_per_night": item.price_per_night,
                }
                for item in data.items
            ]
        },
    }


@router.post("/create")
async def create_hotel(
    payload: HotelCreateRequest, service: HotelService = Depends(get_hotel_service)
):
    return await service.create_hotel(payload)


@router.post("/update/{hotel_id}")
async def update_hotel(
    hotel_id: int, payload: HotelUpdateRequest, service: HotelService = Depends(get_hotel_service)
):
    return await service.update_hotel(hotel_id, payload)


@router.post("/delete/{hotel_id}", response_model=DeleteResponse)
async def delete_hotel(hotel_id: int, service: HotelService = Depends(get_hotel_service)):
    return await service.delete_hotel(hotel_id)
