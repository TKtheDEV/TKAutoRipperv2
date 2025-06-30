from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import deque
import json
import time


@dataclass
class Job:
    # ── immutable metadata ─────────────────────────────────
    job_id: str
    disc_type: str
    disc_label: str
    temp_path: Path
    output_path: Path
    output_path_lock: bool = False
    drive: Optional[str] = None

    # ── timing ────────────────────────────────────────────
    start_time: float = field(default_factory=time.time)
    finish_time: Optional[float] = None  # set when done

    # ── progress & steps ──────────────────────────────────
    steps: List[Dict[str, Any]] = field(default_factory=list)
    step_weights: List[float] = field(default_factory=list)
    step_index: int = 0                 # 0-based current step
    step_progress: int = 0              # 0-100 within current step
    job_progress: int = 0               # 0-100 overall

    # job_status: Queued | Running | Finished | Failed | Cancelled
    job_status: str = "Queued"

    # ── logging & runtime ─────────────────────────────────
    stdout_log: deque = field(default_factory=lambda: deque(maxlen=15))
    runner: "JobRunner | None" = field(default=None, repr=False)

    # ======================================================
    # helpers
    # ======================================================
    # property so we don’t hard-code path logic elsewhere
    def resume_file(self) -> Path:
        return self.temp_path / ".resume.json"

    # called by JobRunner each time stdout arrives
    def append_stdout(self, line: str) -> None:
        self.stdout_log.append(line)

    # ------------------------------------------------------
    def mark_step_done(self) -> None:
        self.steps[self.step_index]["completed"] = True
        self.step_progress = 100
        self.step_index += 1

    def mark_finished(self) -> None:
        self.job_status = "Finished"
        self.job_progress = 100
        self.finish_time = time.time()
        self.save_resume_state(remove=True)

    def mark_failed(self) -> None:
        self.job_status = "Failed"
        self.save_resume_state()

    def mark_cancelled(self) -> None:
        self.job_status = "Cancelled"
        self.save_resume_state()

    # ------------------------------------------------------
    #   (de)serialization
    # ------------------------------------------------------
    def to_dict(self, persist: bool = False) -> Dict[str, Any]:
        data = asdict(self)
        # convert deque & Paths …
        data["stdout_log"] = list(self.stdout_log)
        data["temp_path"]  = str(self.temp_path)
        data["output_path"] = str(self.output_path)
        data.pop("runner", None)

        if persist:
            data["stdout_log"] = []
            data.pop("drive", None)          # ← omit drive in .resume.json
        return data

    # ------------------------------------------------------
    def save_resume_state(self, *, remove: bool = False) -> None:
        """
        Persist or delete the .resume.json file.

        remove=True → delete file (used on success)
        """
        if remove:
            try:
                self.resume_file().unlink()
            except FileNotFoundError:
                pass
            return

        self.temp_path.mkdir(parents=True, exist_ok=True)
        with open(self.resume_file(), "w", encoding="utf-8") as fp:
            json.dump(self.to_dict(persist=True), fp, indent=2)

    # ------------------------------------------------------
    @classmethod
    def from_resume_file(cls, file_path: Path) -> "Job":
        with open(file_path, "r", encoding="utf-8") as fp:
            data = json.load(fp)

        # restore Path objects
        data["temp_path"] = Path(data["temp_path"])
        data["output_path"] = Path(data["output_path"])

        job = cls(**{k: data[k] for k in cls.__annotations__ if k in data})
        job.stdout_log = deque(data.get("stdout_log", []), maxlen=15)
        return job

    # ── Compatibility aliases (old templates expect these) ──
    # You can delete them once all templates use the new names.
    # -------------------------------------------------------
    @property
    def status(self):
        return self.job_status

    @status.setter
    def status(self, value):
        self.job_status = value

    @property
    def progress(self):
        return self.job_progress

    @progress.setter
    def progress(self, value):
        self.job_progress = value