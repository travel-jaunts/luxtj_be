import asyncio
import logging
from datetime import timedelta

from luxtj.contexts.account.infrastructure.persistence.sqlalchemy_repository import (
    SqlAlchemyRefreshSessionRepository,
)
from luxtj.shared_kernel.infrastructure.persistence.sqlalchemy import (
    AsyncSessionFactory,
    session_scope,
)
from luxtj.utils import timeutils

logger = logging.getLogger(__name__)


async def refresh_session_cleanup_loop(
    session_factory: AsyncSessionFactory,
    *,
    interval_seconds: int,
    retention_seconds: int,
) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        before = timeutils.datetime_now() - timedelta(seconds=retention_seconds)
        try:
            async with session_scope(session_factory) as session:
                deleted = await SqlAlchemyRefreshSessionRepository(session).delete_expired_revoked(
                    before=before
                )
            if deleted:
                logger.info("Deleted %s expired revoked account refresh sessions", deleted)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Account refresh-session cleanup failed")
