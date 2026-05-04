from datetime import UTC, date, datetime, time

from admin_api.audit_logs.domainmodel import (
    AuditLogEventDomainModel,
    date_range_to_utc_datetimes,
)
from luxtj.utils import mockutils


class AuditLogService:
    def __init__(self) -> None:
        return

    async def get_list(
        self,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[AuditLogEventDomainModel]:
        # TODO: Implement actual audit log persistence query here
        from_datetime = (
            datetime.combine(from_date, time.min, tzinfo=UTC) if from_date is not None else None
        )
        to_datetime = (
            datetime.combine(to_date, time.max, tzinfo=UTC) if to_date is not None else None
        )
        start_datetime, end_datetime = date_range_to_utc_datetimes(from_datetime, to_datetime)

        num_items = mockutils.random.randint(1, 10)
        audit_logs = [
            AuditLogEventDomainModel.generate_mock(
                from_datetime=start_datetime,
                to_datetime=end_datetime,
            )
            for _ in range(num_items)
        ]
        return sorted(audit_logs, key=lambda audit_log: audit_log.timestamp, reverse=True)
