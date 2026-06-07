"""
Production-grade async queue manager (Render-safe).
Supports:
- per-user limits
- job timeout tracking
- safe cancellation
- stuck job recovery
- concurrency control
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

logger = logging.getLogger("bot.queue")


# ───────────────────────── JOB MODEL ─────────────────────────

@dataclass
class DownloadJob:
    job_id: str
    user_id: int
    urls: List[str]
    chat_id: int
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    cancelled: bool = False
    failed: bool = False


# ───────────────────────── QUEUE MANAGER ─────────────────────────

class QueueManager:

    def __init__(
        self,
        max_workers: int = 3,
        max_user_jobs: int = 2,
        job_timeout: int = 3600
    ):
        self.max_workers = max_workers
        self.max_user_jobs = max_user_jobs
        self.job_timeout = job_timeout

        self._semaphore = asyncio.Semaphore(max_workers)

        self._active: Dict[str, DownloadJob] = {}
        self._queued: Dict[str, DownloadJob] = {}

        self._user_active = defaultdict(int)
        self._user_queued = defaultdict(int)
        self._completed_today = defaultdict(int)

        self._last_reset_date = date.today()
        self._lock = asyncio.Lock()

    # ───────────────── DAILY RESET ─────────────────

    def _reset_daily_if_needed(self):
        today = date.today()
        if today != self._last_reset_date:
            self._completed_today.clear()
            self._last_reset_date = today

    # ───────────────── VALIDATION ─────────────────

    def can_accept(self, user_id: int) -> bool:
        """Check per-user limit before queueing."""
        return self._user_active[user_id] < self.max_user_jobs

    # ───────────────── ACQUIRE ─────────────────

    async def acquire(self, job: DownloadJob) -> bool:

        async with self._lock:

            if not self.can_accept(job.user_id):
                logger.warning("User %s exceeded job limit", job.user_id)
                return False

            self._queued[job.job_id] = job
            self._user_queued[job.user_id] += 1

        await self._semaphore.acquire()

        async with self._lock:

            self._queued.pop(job.job_id, None)
            self._user_queued[job.user_id] = max(
                0, self._user_queued[job.user_id] - 1
            )

            if job.cancelled:
                self._semaphore.release()
                return False

            job.started_at = time.time()
            self._active[job.job_id] = job
            self._user_active[job.user_id] += 1

        return True

    # ───────────────── RELEASE ─────────────────

    async def release(self, job: DownloadJob):

        async with self._lock:

            self._active.pop(job.job_id, None)
            self._user_active[job.user_id] = max(
                0, self._user_active[job.user_id] - 1
            )

            self._reset_daily_if_needed()
            self._completed_today[job.user_id] += 1

        self._semaphore.release()

    # ───────────────── CANCEL USER ─────────────────

    def cancel_user_jobs(self, user_id: int) -> int:
        count = 0

        for job in list(self._queued.values()):
            if job.user_id == user_id:
                job.cancelled = True
                count += 1

        for job in list(self._active.values()):
            if job.user_id == user_id:
                job.cancelled = True
                count += 1

        logger.info("Cancelled %d jobs for user %s", count, user_id)
        return count

    # ───────────────── STUCK JOB CLEANER ─────────────────

    async def cleanup_stuck_jobs(self):
        """Removes jobs stuck longer than timeout."""
        now = time.time()

        async with self._lock:
            for job_id, job in list(self._active.items()):
                if job.started_at and (now - job.started_at > self.job_timeout):
                    logger.warning("Job %s timed out", job_id)
                    job.failed = True
                    job.cancelled = True

    # ───────────────── STATS ─────────────────

    def get_stats(self, user_id: Optional[int] = None) -> Dict[str, Any]:

        self._reset_daily_if_needed()

        return {
            "global_active": len(self._active),
            "global_queued": len(self._queued),
            "max_workers": self.max_workers,

            "user_active": self._user_active.get(user_id, 0) if user_id else 0,
            "user_queued": self._user_queued.get(user_id, 0) if user_id else 0,
            "user_completed": self._completed_today.get(user_id, 0) if user_id else 0,

            "max_per_user": self.max_user_jobs,
        }

    # ───────────────── SHUTDOWN ─────────────────

    async def shutdown(self):

        logger.info(
            "Queue shutdown: active=%d queued=%d",
            len(self._active),
            len(self._queued)
        )

        for job in self._queued.values():
            job.cancelled = True

        for job in self._active.values():
            job.cancelled = True
