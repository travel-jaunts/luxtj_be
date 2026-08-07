from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from luxtj.contexts.integration.domain.entities import (
    BookingApi,
    Module,
    OtherApi,
    PaymentGateway,
    SubModule,
)
from luxtj.contexts.integration.infrastructure.persistence.sqlalchemy_models import (
    BookingApiRow,
    ModuleRow,
    OtherApiRow,
    PaymentGatewayRow,
    SubModuleRow,
)


class SqlAlchemyIntegrationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def flush(self) -> None:
        """Persist pending rows so FK parents exist before children are inserted."""
        await self._session.flush()

    async def list_modules(self) -> list[Module]:
        result = await self._session.execute(
            select(ModuleRow).where(ModuleRow.deleted_at.is_(None)).order_by(ModuleRow.name)
        )
        return [row.to_domain() for row in result.scalars().all()]

    async def get_module(self, module_id: UUID) -> Module | None:
        row = await self._session.get(ModuleRow, str(module_id))
        if row is None or row.deleted_at is not None:
            return None
        return row.to_domain()

    async def get_module_by_name(self, name: str) -> Module | None:
        result = await self._session.execute(
            select(ModuleRow).where(ModuleRow.name == name, ModuleRow.deleted_at.is_(None))
        )
        row = result.scalar_one_or_none()
        return row.to_domain() if row else None

    async def add_module(self, entity: Module) -> None:
        self._session.add(
            ModuleRow(
                id=str(entity.id),
                name=entity.name,
                status=entity.status,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
                deleted_at=entity.deleted_at,
            )
        )

    async def save_module(self, entity: Module) -> None:
        row = await self._session.get(ModuleRow, str(entity.id))
        if row is None:
            raise ValueError("Module not found")
        row.apply_domain(entity)

    async def list_sub_modules(self) -> list[SubModule]:
        result = await self._session.execute(select(SubModuleRow).order_by(SubModuleRow.name))
        return [row.to_domain() for row in result.scalars().all()]

    async def get_sub_module(self, sub_module_id: UUID) -> SubModule | None:
        row = await self._session.get(SubModuleRow, str(sub_module_id))
        return row.to_domain() if row else None

    async def get_sub_module_by_name(self, name: str) -> SubModule | None:
        result = await self._session.execute(select(SubModuleRow).where(SubModuleRow.name == name))
        row = result.scalar_one_or_none()
        return row.to_domain() if row else None

    async def add_sub_module(self, entity: SubModule) -> None:
        self._session.add(
            SubModuleRow(
                id=str(entity.id),
                name=entity.name,
                status=entity.status,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
            )
        )

    async def save_sub_module(self, entity: SubModule) -> None:
        row = await self._session.get(SubModuleRow, str(entity.id))
        if row is None:
            raise ValueError("Sub-module not found")
        row.apply_domain(entity)

    async def list_booking_apis(self) -> list[BookingApi]:
        result = await self._session.execute(
            select(BookingApiRow).order_by(BookingApiRow.name)
        )
        return [row.to_domain() for row in result.scalars().all()]

    async def get_booking_api(self, booking_api_id: UUID) -> BookingApi | None:
        row = await self._session.get(BookingApiRow, str(booking_api_id))
        return row.to_domain() if row else None

    async def get_booking_api_by_code(self, sub_module_id: UUID, code: str) -> BookingApi | None:
        result = await self._session.execute(
            select(BookingApiRow).where(
                BookingApiRow.sub_module_id == str(sub_module_id),
                BookingApiRow.code == code,
            )
        )
        row = result.scalar_one_or_none()
        return row.to_domain() if row else None

    async def add_booking_api(self, entity: BookingApi) -> None:
        self._session.add(
            BookingApiRow(
                id=str(entity.id),
                sub_module_id=str(entity.sub_module_id),
                code=entity.code,
                name=entity.name,
                configuration=entity.configuration,
                status=entity.status,
                api_type=entity.api_type,
                currency=entity.currency,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
            )
        )

    async def save_booking_api(self, entity: BookingApi) -> None:
        row = await self._session.get(BookingApiRow, str(entity.id))
        if row is None:
            raise ValueError("Booking API not found")
        row.apply_domain(entity)

    async def list_payment_gateways(self) -> list[PaymentGateway]:
        result = await self._session.execute(
            select(PaymentGatewayRow).order_by(PaymentGatewayRow.name)
        )
        return [row.to_domain() for row in result.scalars().all()]

    async def get_payment_gateway(self, gateway_id: UUID) -> PaymentGateway | None:
        row = await self._session.get(PaymentGatewayRow, str(gateway_id))
        return row.to_domain() if row else None

    async def get_payment_gateway_by_code(self, code: str) -> PaymentGateway | None:
        result = await self._session.execute(
            select(PaymentGatewayRow).where(PaymentGatewayRow.code == code)
        )
        row = result.scalar_one_or_none()
        return row.to_domain() if row else None

    async def add_payment_gateway(self, entity: PaymentGateway) -> None:
        self._session.add(
            PaymentGatewayRow(
                id=str(entity.id),
                code=entity.code,
                name=entity.name,
                configuration=entity.configuration,
                status=entity.status,
                api_type=entity.api_type,
                currency=entity.currency,
                convenience_type=entity.convenience_type,
                convenience_value=entity.convenience_value,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
            )
        )

    async def save_payment_gateway(self, entity: PaymentGateway) -> None:
        row = await self._session.get(PaymentGatewayRow, str(entity.id))
        if row is None:
            raise ValueError("Payment gateway not found")
        row.apply_domain(entity)

    async def list_other_apis(self) -> list[OtherApi]:
        result = await self._session.execute(select(OtherApiRow).order_by(OtherApiRow.name))
        return [row.to_domain() for row in result.scalars().all()]

    async def get_other_api(self, other_api_id: UUID) -> OtherApi | None:
        row = await self._session.get(OtherApiRow, str(other_api_id))
        return row.to_domain() if row else None

    async def get_other_api_by_code(self, code: str) -> OtherApi | None:
        result = await self._session.execute(select(OtherApiRow).where(OtherApiRow.code == code))
        row = result.scalar_one_or_none()
        return row.to_domain() if row else None

    async def add_other_api(self, entity: OtherApi) -> None:
        self._session.add(
            OtherApiRow(
                id=str(entity.id),
                code=entity.code,
                name=entity.name,
                configuration=entity.configuration,
                status=entity.status,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
            )
        )

    async def save_other_api(self, entity: OtherApi) -> None:
        row = await self._session.get(OtherApiRow, str(entity.id))
        if row is None:
            raise ValueError("Other API not found")
        row.apply_domain(entity)
