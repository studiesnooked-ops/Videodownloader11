import asyncio
import uuid
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class Job:
    job_id: str
    user_id: int
    urls: List[str]
    status: str = "queued"
    result: List[str] = field(default_factory=list)


class JobManager:
    def __init__(self):
        self.jobs: Dict[str, Job] = {}
        self.lock = asyncio.Lock()

    async def create_job(self, user_id: int, urls: List[str]) -> Job:
        job = Job(
            job_id=str(uuid.uuid4()),
            user_id=user_id,
            urls=urls
        )

        async with self.lock:
            self.jobs[job.job_id] = job

        return job

    async def get_job(self, job_id: str) -> Job:
        return self.jobs.get(job_id)
