# app/core/job/tracker.py
#
# Adds add_job() so back-end can register a Job that was loaded
# from a .resume.json file.

import threading
from typing import Dict, List, Optional
from pathlib import Path
from .job import Job


class JobTracker:
    def __init__(self):
        self.jobs: Dict[str, Job] = {}
        self.lock = threading.Lock()

    # ------------------------------------------------------
    def add_job(self, job: Job) -> None:
        """Register an existing Job object (used for resume)."""
        with self.lock:
            self.jobs[job.job_id] = job

    # ------------------------------------------------------
    def create_job(
        self,
        disc_type: str,
        drive: str,
        disc_label: str,
        temp_dir: Path,
        output_dir: Path,
        steps_total: int,
    ) -> Job:
        import uuid, time
        job_id = str(uuid.uuid4())
        job = Job(
            job_id=job_id,
            disc_type=disc_type,
            disc_label=disc_label,
            drive=drive,
            temp_path=temp_dir / job_id,
            output_path=output_dir,
            output_path_lock=False,
            start_time=time.time(),
        )
        self.add_job(job)
        return job

    # ------------------------------------------------------
    def get_job(self, job_id: str) -> Optional[Job]:
        return self.jobs.get(job_id)

    def cancel_job(self, job_id: str) -> bool:
        with self.lock:
            job = self.jobs.get(job_id)
            if job:
                job.job_status = "Cancelled"
                return True
            return False

    def list_jobs(self) -> List[Job]:
        return list(self.jobs.values())


job_tracker = JobTracker()
