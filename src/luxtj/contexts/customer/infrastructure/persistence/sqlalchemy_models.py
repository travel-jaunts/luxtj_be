from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from luxtj.contexts.customer.domain.bucket_list import BucketList, BucketListItem
from luxtj.contexts.customer.domain.enums import BucketDestinationKindEnum


class CustomerBase(DeclarativeBase):
    pass


class CustomerBucketListRow(CustomerBase):
    __tablename__ = "customer_bucket_lists"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @classmethod
    def from_domain(cls, bucket_list: BucketList) -> CustomerBucketListRow:
        return cls(
            id=str(bucket_list.id),
            account_id=str(bucket_list.account_id),
            created_at=bucket_list.created_at,
            updated_at=bucket_list.updated_at,
        )

    def update_from_domain(self, bucket_list: BucketList) -> None:
        self.updated_at = bucket_list.updated_at

    def to_domain(self, items: list[BucketListItem]) -> BucketList:
        return BucketList(
            id=UUID(self.id),
            account_id=UUID(self.account_id),
            created_at=self.created_at,
            updated_at=self.updated_at,
            items=items,
        )


class CustomerBucketListItemRow(CustomerBase):
    __tablename__ = "customer_bucket_list_items"
    __table_args__ = (
        UniqueConstraint(
            "bucket_list_id",
            "destination_kind",
            "normalized_destination_name",
            "is_active",
            name="uq_customer_bucket_active_destination",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    bucket_list_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("customer_bucket_lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    destination_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    destination_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_destination_name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_country: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ideal_days: Mapped[int] = mapped_column(Integer, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @classmethod
    def from_domain(
        cls,
        *,
        bucket_list_id: UUID,
        item: BucketListItem,
    ) -> CustomerBucketListItemRow:
        return cls(
            id=str(item.id),
            bucket_list_id=str(bucket_list_id),
            destination_kind=item.destination_kind.value,
            destination_name=item.destination_name,
            normalized_destination_name=item.normalized_destination_name,
            parent_country=item.parent_country,
            ideal_days=item.ideal_days,
            display_order=item.display_order,
            notes=item.notes,
            is_active=item.is_active,
            created_at=item.created_at,
            updated_at=item.updated_at,
            deleted_at=item.deleted_at,
        )

    def update_from_domain(self, item: BucketListItem) -> None:
        self.destination_kind = item.destination_kind.value
        self.destination_name = item.destination_name
        self.normalized_destination_name = item.normalized_destination_name
        self.parent_country = item.parent_country
        self.ideal_days = item.ideal_days
        self.display_order = item.display_order
        self.notes = item.notes
        self.is_active = item.is_active
        self.updated_at = item.updated_at
        self.deleted_at = item.deleted_at

    def to_domain(self) -> BucketListItem:
        return BucketListItem(
            id=UUID(self.id),
            destination_kind=BucketDestinationKindEnum(self.destination_kind),
            destination_name=self.destination_name,
            normalized_destination_name=self.normalized_destination_name,
            parent_country=self.parent_country,
            ideal_days=self.ideal_days,
            display_order=self.display_order,
            notes=self.notes,
            created_at=self.created_at,
            updated_at=self.updated_at,
            deleted_at=self.deleted_at,
        )
