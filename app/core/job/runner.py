from __future__ import annotations

import os
import signal
import subprocess
import threading
from pathlib import Path
from typing import Callable, List, Tuple, Optional

from app.core.drive.manager import drive_tracker
from .job import Job


# ------------------------------------------------------------
def get_job_steps(job: Job) -> List[Tuple[List[str], str, bool, float]]:
    """
    Returns the canonical list of step tuples:
      (command, description, release_drive, weight)
    We import lazily to avoid circulars.
    """
    dtype = job.disc_type.lower()

    if dtype == "cd_audio":
        from app.core.rippers.audio.linux import rip_audio_cd
        return rip_audio_cd(job)

    if dtype in ("cd_rom", "dvd_rom", "bluray_rom"):
        from app.core.rippers.other.linux import rip_generic_disc
        return rip_generic_disc(job)

    if dtype == "dvd_video":
        from app.core.rippers.video.linux import rip_video_disc
        return rip_video_disc(job, "DVD")

    if dtype == "bluray_video":
        from app.core.rippers.video.linux import rip_video_disc
        return rip_video_disc(job, "BLURAY")

    raise ValueError(f"Unsupported disc type: {dtype}")


# ============================================================
class JobRunner:
    """
    Runs a job in a background thread.
    """

    def __init__(
        self,
        job: Job,
        on_output: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.job = job
        self.job.runner = self
        self.on_output = on_output
        self.process: Optional[subprocess.Popen] = None
        self._cancelled = False

    # ---------------------------------------------------------
    def run(self) -> None:
        threading.Thread(target=self._run, daemon=True).start()

    def cancel(self) -> None:
        self._cancelled = True
        if self.process:
            try: os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            except Exception: pass
        self.job.mark_cancelled()

        if self.job.drive:
            drive_tracker.release_drive(self.job.drive)
            subprocess.run(["eject", self.job.drive], check=False)

    # ---------------------------------------------------------
    def _initialize_steps(self) -> None:
        """
        Fill job.steps & step_weights if they are empty (fresh job).
        """
        if self.job.steps:
            return  # already initialised (resume case)

        raw = get_job_steps(self.job)
        self.job.step_weights = [tpl[3] for tpl in raw]  # fourth element
        for idx, (_, desc, _, _) in enumerate(raw, start=1):
            self.job.steps.append(
                {"index": idx, "name": desc, "completed": False}
            )

    # ---------------------------------------------------------
    def _run(self) -> None:
        try:
            self.job.job_status = "Running"
            self._initialize_steps()

            steps = get_job_steps(self.job)

            # skip already-completed steps (resume case)
            current_idx = self.job.step_index
            for i in range(current_idx, len(steps)):
                if self._cancelled:
                    return

                cmd, desc, release_drive, weight = steps[i]
                self.job.step_progress = 0
                self.job.steps[i]["name"] = desc  # keep in sync

                ok = self._run_step(cmd, weight)
                if not ok:
                    self.job.mark_failed()
                    return

                self.job.mark_step_done()
                self.job.save_resume_state()

                # early drive release
                if release_drive and self.job.drive:
                    subprocess.run(["eject", self.job.drive], check=False)
                    drive_tracker.release_drive(self.job.drive)

            self.job.mark_finished()

        except Exception as exc:
            self.job.append_stdout(f"Fatal exception: {exc}")
            self.job.mark_failed()

    # ---------------------------------------------------------
    def _run_step(self, command: List[str], weight: float) -> bool:
        log_path = self.job.temp_path / "log.txt"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(log_path, "a") as lf:
                self.process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    preexec_fn=os.setsid,  # own process-group
                )

                for line in self.process.stdout:
                    if self._cancelled:
                        return False
                    line = line.rstrip()
                    self.job.append_stdout(line)
                    lf.write(line + "\n")
                    lf.flush()
                    if self.on_output:
                        self.on_output(line)

                    # naive in-step progress (bounces to keep UI alive)
                    self.job.step_progress = min(99, self.job.step_progress + 1)
                    self._recalc_job_progress(weight)

                self.process.wait()
                self.job.step_progress = 100
                self._recalc_job_progress(weight)
                return self.process.returncode == 0

        except Exception as exc:
            self.job.append_stdout(f"Exception in subprocess: {exc}")
            return False

    # ---------------------------------------------------------
    def _recalc_job_progress(self, current_weight: float) -> None:
        """
        job_progress = sum(done_weights) + step_progress% * current_weight
        """
        done_fraction = sum(
            w for idx, w in enumerate(self.job.step_weights)
            if idx < self.job.step_index or self.job.steps[idx]["completed"]
        )

        step_fraction = (self.job.step_progress / 100.0) * current_weight
        self.job.job_progress = int((done_fraction + step_fraction) * 100)
