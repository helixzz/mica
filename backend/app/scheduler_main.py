"""Mica scheduler entry point — runs periodic background tasks.

Intended to run as a standalone process (separate Docker container
or systemd service), not inside the FastAPI backend.
"""

from __future__ import annotations

import asyncio
import logging
import signal

from app.db import AsyncSessionLocal
from app.scheduler import build_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("mica.scheduler.main")


async def main():
    logger.info("Starting Mica scheduler...")
    scheduler = build_scheduler(AsyncSessionLocal)
    scheduler.start()
    logger.info("Scheduler started with %d jobs", len(scheduler.get_jobs()))

    stop_event = asyncio.Event()

    def _shutdown(signum, frame):
        logger.info("Received signal %s, shutting down...", signum)
        stop_event.set()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    await stop_event.wait()
    logger.info("Shutting down scheduler...")
    scheduler.shutdown(wait=True)
    logger.info("Scheduler stopped")


if __name__ == "__main__":
    asyncio.run(main())
