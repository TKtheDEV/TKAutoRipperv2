from typing import List, Tuple
from pathlib import Path
from ...configmanager import config
from ...job.job import Job
from ...integration.dd.linux import build_iso_dump_cmd
from ...integration.zstd.linux import build_zstd_cmd


def rip_generic_disc(job: Job) -> List[Tuple[List[str], str]]:
    """
    Constructs ripping steps for ROM-type discs: dump ISO, optionally compress,
    and copy/move to final output path.
    """
    other_cfg = config.section("OTHER")
    use_compression = other_cfg.get("usecompression", True)
    compression = other_cfg.get("compression", "zstd").lower()

    iso_name = f"{job.disc_label}.iso"
    raw_iso_path = job.temp_path / iso_name

    steps = []

    # Step 1: ISO dump with pv + dd
    dd_cmd = build_iso_dump_cmd(job.drive, raw_iso_path)
    steps.append((dd_cmd, "Creating ISO image from disc"))

    job.output_path_lock = True
    Path(job.output_path).mkdir(parents=True, exist_ok=True)

    # Step 2: Optional compression or copy to final output
    if use_compression and compression == "zstd":
        final_path = job.output_path.with_suffix(".iso.zst")
        zstd_cmd = build_zstd_cmd(raw_iso_path, final_path)
        steps.append((zstd_cmd, "Compressing ISO with zstd"))

    elif use_compression and compression == "bz2":
        final_path = job.output_path.with_suffix(".iso.bz2")
        bz2_cmd = ["bzip2", str(raw_iso_path)]
        steps.append((bz2_cmd, "Compressing ISO with bzip2"))

    else:
        final_path = job.output_path.with_suffix(".iso")
        copy_cmd = ["cp", str(raw_iso_path), str(final_path)]
        steps.append((copy_cmd, "Copying ISO to final output location"))

    return steps
