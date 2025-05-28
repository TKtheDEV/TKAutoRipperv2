import os
import signal
import subprocess
import threading
from typing import Callable, Optional, List, Tuple
from pathlib import Path
from .job import Job


def get_job_steps(job: Job) -> List[Tuple[List[str], str]]:
    """
    Resolves the correct ripper function based on disc_type and returns steps.
    Each step is a tuple: (command: List[str], description: str)
    """
    disc_type = job.disc_type.lower()

    if disc_type == "cd_audio":
        from app.core.rippers.audio.linux import rip_audio_cd
        return rip_audio_cd(job)

    elif disc_type in ("cd_rom", "dvd_rom", "bluray_rom"):
        from app.core.rippers.other.linux import rip_generic_disc
        return rip_generic_disc(job)

    elif disc_type == "dvd_video":
        from app.core.rippers.video.linux import rip_video_disc
        return rip_video_disc(job, "DVD")

    elif disc_type == "bluray_video":
        from app.core.rippers.video.linux import rip_video_disc
        return rip_video_disc(job, "BLURAY")

    else:
        raise ValueError(f"Unsupported disc type: {disc_type}")


class JobRunner:
    def __init__(self, job: Job, on_output: Optional[Callable[[str], None]] = None):
        self.job = job
        self.job.runner = self
        self.on_output = on_output
        self.process: Optional[subprocess.Popen] = None
        self._cancelled = False

    def run(self):
        thread = threading.Thread(target=self._run_steps, daemon=True)
        thread.start()

    def cancel(self):
        self._cancelled = True
        if self.process:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            except Exception as e:
                print(f"Error killing process group: {e}")
        self.job.mark_failed()

    def resume(self):
        self._cancelled = False
        self.run()

    def _run_steps(self):
        try:
            steps = get_job_steps(self.job)
            self.job.steps_total = len(steps)
            weights = [1 / len(steps)] * len(steps)

            for i, (cmd, desc) in enumerate(steps):
                if self._cancelled:
                    return
                self.job.update_step(desc, i + 1)
                weight = weights[i]
                success = self._run_step(cmd, desc, weight)
                if not success:
                    self.job.mark_failed()
                    return

            self.job.mark_finished()

        except Exception as e:
            self.job.append_stdout(f"Fatal exception in JobRunner: {e}")
            self.job.mark_failed()

    def _run_step(self, command: List[str], description: str, weight: float) -> bool:
        log_path = self.job.temp_path / "log.txt"
        os.makedirs(self.job.temp_path, exist_ok=True)

        try:
            with open(log_path, "a") as log_file:
                self.process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    preexec_fn=os.setsid  # Only works on Unix
                )

                for line in self.process.stdout:
                    line = line.strip()
                    self.job.append_stdout(line)
                    log_file.write(line + "\n")
                    log_file.flush()
                    if self.on_output:
                        self.on_output(line)

                    self.job.step_progress += 1
                    # Basic progress estimate
                    self.job.progress = min(
                        100,
                        int(((self.job.step - 1) / self.job.steps_total +
                            (self.job.step_progress / 10) / self.job.steps_total) * 100)
                    )

                self.process.wait()
                return self.process.returncode == 0

        except Exception as e:
            self.job.append_stdout(f"Exception during step: {e}")
            return False
