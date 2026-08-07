from datetime import datetime
from uuid import UUID, uuid4

from luxtj.utils import timeutils


class Module:
    def __init__(
        self,
        *,
        id: UUID,
        name: str,
        status: bool,
        created_at: datetime,
        updated_at: datetime,
        deleted_at: datetime | None = None,
    ) -> None:
        self.id = id
        self.name = name
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.deleted_at = deleted_at

    @classmethod
    def create(cls, *, name: str, now: datetime | None = None) -> "Module":
        ts = now or timeutils.datetime_now()
        return cls(id=uuid4(), name=name, status=True, created_at=ts, updated_at=ts)

    def set_status(self, status: bool, *, now: datetime | None = None) -> None:
        self.status = status
        self.updated_at = now or timeutils.datetime_now()


class SubModule:
    def __init__(
        self,
        *,
        id: UUID,
        name: str,
        status: bool,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self.id = id
        self.name = name
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def create(cls, *, name: str, now: datetime | None = None) -> "SubModule":
        ts = now or timeutils.datetime_now()
        return cls(id=uuid4(), name=name, status=False, created_at=ts, updated_at=ts)

    def set_status(self, status: bool, *, now: datetime | None = None) -> None:
        self.status = status
        self.updated_at = now or timeutils.datetime_now()


class BookingApi:
    def __init__(
        self,
        *,
        id: UUID,
        sub_module_id: UUID,
        code: str,
        name: str,
        configuration: dict | None,
        status: bool,
        api_type: str | None,
        currency: str | None,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self.id = id
        self.sub_module_id = sub_module_id
        self.code = code
        self.name = name
        self.configuration = configuration or {"configs": {}}
        self.status = status
        self.api_type = api_type
        self.currency = currency
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def create(
        cls,
        *,
        sub_module_id: UUID,
        code: str,
        name: str,
        now: datetime | None = None,
    ) -> "BookingApi":
        ts = now or timeutils.datetime_now()
        return cls(
            id=uuid4(),
            sub_module_id=sub_module_id,
            code=code,
            name=name,
            configuration={"configs": {}},
            status=False,
            api_type=None,
            currency=None,
            created_at=ts,
            updated_at=ts,
        )

    def update_settings(
        self,
        *,
        status: bool | None = None,
        api_type: str | None = None,
        currency: str | None = None,
        configs: dict[str, str] | None = None,
        now: datetime | None = None,
    ) -> None:
        if status is not None:
            self.status = status
        if api_type is not None:
            self.api_type = api_type
        if currency is not None:
            self.currency = currency
        if configs is not None:
            self.configuration = {"configs": dict(configs)}
        self.updated_at = now or timeutils.datetime_now()

    def credential_configs(self) -> dict[str, str]:
        raw = self.configuration or {}
        configs = raw.get("configs") if isinstance(raw, dict) else {}
        return {str(k): str(v) for k, v in (configs or {}).items()}

    def runtime_configuration(self) -> dict:
        """Adapter view: credential JSON + first-class columns (registry Layer B)."""
        return {
            "configs": self.credential_configs(),
            "api_type": self.api_type,
            "currency": self.currency,
        }


class PaymentGateway:
    def __init__(
        self,
        *,
        id: UUID,
        code: str,
        name: str,
        configuration: dict | None,
        status: bool,
        api_type: str | None,
        currency: str | None,
        convenience_type: str | None,
        convenience_value: str | None,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self.id = id
        self.code = code
        self.name = name
        self.configuration = configuration or {"configs": {}}
        self.status = status
        self.api_type = api_type
        self.currency = currency
        self.convenience_type = convenience_type
        self.convenience_value = convenience_value
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def create(cls, *, code: str, name: str, now: datetime | None = None) -> "PaymentGateway":
        ts = now or timeutils.datetime_now()
        return cls(
            id=uuid4(),
            code=code,
            name=name,
            configuration={"configs": {}},
            status=False,
            api_type=None,
            currency=None,
            convenience_type=None,
            convenience_value=None,
            created_at=ts,
            updated_at=ts,
        )

    def update_settings(
        self,
        *,
        status: bool | None = None,
        api_type: str | None = None,
        currency: str | None = None,
        convenience_type: str | None = None,
        convenience_value: str | None = None,
        configs: dict[str, str] | None = None,
        now: datetime | None = None,
    ) -> None:
        if status is not None:
            self.status = status
        if api_type is not None:
            self.api_type = api_type
        if currency is not None:
            self.currency = currency
        if convenience_type is not None:
            self.convenience_type = convenience_type
        if convenience_value is not None:
            self.convenience_value = convenience_value
        if configs is not None:
            self.configuration = {"configs": dict(configs)}
        self.updated_at = now or timeutils.datetime_now()

    def credential_configs(self) -> dict[str, str]:
        raw = self.configuration or {}
        configs = raw.get("configs") if isinstance(raw, dict) else {}
        return {str(k): str(v) for k, v in (configs or {}).items()}

    def runtime_configuration(self) -> dict:
        """Adapter view: credential JSON + first-class columns (registry Layer B)."""
        return {
            "configs": self.credential_configs(),
            "api_type": self.api_type,
            "currency": self.currency,
            "convenience_type": self.convenience_type,
            "convenience_value": self.convenience_value,
        }


class OtherApi:
    def __init__(
        self,
        *,
        id: UUID,
        code: str,
        name: str,
        configuration: dict | None,
        status: bool,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self.id = id
        self.code = code
        self.name = name
        self.configuration = configuration or {"configs": {}}
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def create(cls, *, code: str, name: str, now: datetime | None = None) -> "OtherApi":
        ts = now or timeutils.datetime_now()
        return cls(
            id=uuid4(),
            code=code,
            name=name,
            configuration={"configs": {}},
            status=False,
            created_at=ts,
            updated_at=ts,
        )

    def update_settings(
        self,
        *,
        status: bool | None = None,
        configs: dict[str, str] | None = None,
        now: datetime | None = None,
    ) -> None:
        if status is not None:
            self.status = status
        if configs is not None:
            self.configuration = {"configs": dict(configs)}
        self.updated_at = now or timeutils.datetime_now()

    def credential_configs(self) -> dict[str, str]:
        raw = self.configuration or {}
        configs = raw.get("configs") if isinstance(raw, dict) else {}
        return {str(k): str(v) for k, v in (configs or {}).items()}
