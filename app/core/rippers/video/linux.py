from typing import List, Tuple
from pathlib import Path
from ...configmanager import config
from ...job.job import Job
from ...integration.makemkv.linux import build_makemkv_cmd
from ...integration.handbrake.linux import build_handbrake_cmd


def rip_video_disc(job: Job, disc_type: str) -> List[Tuple[List[str], str]]:
    """
    Builds ripping steps for DVD or Blu-ray video discs.
    Step 1: makemkvcon to extract MKV
    Step 2: HandBrakeCLI to transcode to final format (optional)
    """
    disc_type_key = disc_type.upper()
    cfg = config.section(disc_type_key)

    temp_mkv_dir = job.temp_path
    progress_path = job.temp_path / "makemkv_progress.txt"
    makemkv_cmd = build_makemkv_cmd(job.drive, temp_mkv_dir, progress_path)

    steps = [(makemkv_cmd, f"Ripping {disc_type} with MakeMKV")]

    if cfg.get("usehandbrake", False):
        preset_path = Path(cfg["handbrakepreset_path"]).expanduser()
        preset_name = cfg["handbrakepreset_name"]
        output_format = cfg["handbrakeformat"]
        flatpak = config.get("Advanced", "HandbrakeFlatpak")

        # Output file assumed to match disc label
        mkv_file = temp_mkv_dir / f"{job.disc_label}.mkv"
        output_file = job.output_path.with_suffix(f".{output_format}")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        hb_cmd = build_handbrake_cmd(
            mkv_file=mkv_file,
            output_path=output_file,
            preset_path=preset_path,
            preset_name=preset_name,
            flatpak=flatpak
        )
        steps.append((hb_cmd, f"Encoding {disc_type} with HandBrake"))

    return steps
