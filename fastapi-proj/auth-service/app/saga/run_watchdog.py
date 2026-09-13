import asyncio
import logging
import signal

from app.core.logging import setup_logging
from app.saga.watchdog import SagaWatchdog

logger = logging.getLogger(__name__)


async def main() -> None:
    """Точка входа процесса сторожа саг."""
    setup_logging()

    watchdog = SagaWatchdog()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, watchdog.stop)

    try:
        await watchdog.run_forever()
    finally:
        logger.info("SagaWatchdog process stopped")


if __name__ == "__main__":
    asyncio.run(main())
