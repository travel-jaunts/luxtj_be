from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from luxtj.contexts.integration.domain.entities import (
    BookingApi,
    Module,
    OtherApi,
    PaymentGateway,
    SubModule,
)


class IntegrationBase(DeclarativeBase):
    pass


class ModuleRow(IntegrationBase):
    __tablename__ = "modules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    status: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_domain(self) -> Module:
        return Module(
            id=UUID(self.id),
            name=self.name,
            status=self.status,
            created_at=self.created_at,
            updated_at=self.updated_at,
            deleted_at=self.deleted_at,
        )

    def apply_domain(self, entity: Module) -> None:
        self.name = entity.name
        self.status = entity.status
        self.updated_at = entity.updated_at
        self.deleted_at = entity.deleted_at


class SubModuleRow(IntegrationBase):
    __tablename__ = "sub_modules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    status: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def to_domain(self) -> SubModule:
        return SubModule(
            id=UUID(self.id),
            name=self.name,
            status=self.status,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    def apply_domain(self, entity: SubModule) -> None:
        self.name = entity.name
        self.status = entity.status
        self.updated_at = entity.updated_at


class BookingApiRow(IntegrationBase):
    __tablename__ = "booking_apis"
    __table_args__ = (UniqueConstraint("sub_module_id", "code", name="uq_booking_apis_sub_module_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    sub_module_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sub_modules.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    configuration: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    api_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def to_domain(self) -> BookingApi:
        return BookingApi(
            id=UUID(self.id),
            sub_module_id=UUID(self.sub_module_id),
            code=self.code,
            name=self.name,
            configuration=self.configuration,
            status=self.status,
            api_type=self.api_type,
            currency=self.currency,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    def apply_domain(self, entity: BookingApi) -> None:
        self.name = entity.name
        self.configuration = entity.configuration
        self.status = entity.status
        self.api_type = entity.api_type
        self.currency = entity.currency
        self.updated_at = entity.updated_at


class PaymentGatewayRow(IntegrationBase):
    __tablename__ = "payment_gateways"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    configuration: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    api_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    convenience_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    convenience_value: Mapped[str | None] = mapped_column(Numeric(18, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def to_domain(self) -> PaymentGateway:
        value = None if self.convenience_value is None else str(self.convenience_value)
        return PaymentGateway(
            id=UUID(self.id),
            code=self.code,
            name=self.name,
            configuration=self.configuration,
            status=self.status,
            api_type=self.api_type,
            currency=self.currency,
            convenience_type=self.convenience_type,
            convenience_value=value,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    def apply_domain(self, entity: PaymentGateway) -> None:
        self.name = entity.name
        self.configuration = entity.configuration
        self.status = entity.status
        self.api_type = entity.api_type
        self.currency = entity.currency
        self.convenience_type = entity.convenience_type
        self.convenience_value = entity.convenience_value
        self.updated_at = entity.updated_at


class OtherApiRow(IntegrationBase):
    __tablename__ = "other_apis"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    configuration: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def to_domain(self) -> OtherApi:
        return OtherApi(
            id=UUID(self.id),
            code=self.code,
            name=self.name,
            configuration=self.configuration,
            status=self.status,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    def apply_domain(self, entity: OtherApi) -> None:
        self.name = entity.name
        self.configuration = entity.configuration
        self.status = entity.status
        self.updated_at = entity.updated_at
