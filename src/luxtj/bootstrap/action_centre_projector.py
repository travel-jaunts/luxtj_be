import asyncio
import signal

from luxtj.bootstrap import config
from luxtj.bootstrap.persistence import database_resources
from luxtj.contexts.action_centre.infrastructure.projector import ActionCentreOutboxProjector
from luxtj.shared_kernel.infrastructure.logging import get_logger_handle

logger = get_logger_handle(__name__)


async def run_action_centre_outbox_projector() -> None:
    logger.info("Action centre outbox projector process starting")

    async with database_resources(
        config.DATABASE_URL,
        echo=config.DATABASE_ECHO,
    ) as resources:
        projector = ActionCentreOutboxProjector(resources.session_factory)
        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()

        def _request_stop() -> None:
            stop_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _request_stop)
            except NotImplementedError:
                # add_signal_handler is not available on every runtime.
                pass

        await projector.start()
        logger.info("Action centre outbox projector started")

        try:
            await stop_event.wait()
        finally:
            await projector.stop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    loop.remove_signal_handler(sig)
                except NotImplementedError:
                    pass

    logger.info("Action centre outbox projector process stopped")


async def main() -> None:
    if not config.ENABLE_OUTBOX_PROJECTOR:
        logger.info("Action centre outbox projector is disabled via LTJBE_ENABLE_OUTBOX_PROJECTOR")
        return
    await run_action_centre_outbox_projector()


if __name__ == "__main__":
    asyncio.run(main())
