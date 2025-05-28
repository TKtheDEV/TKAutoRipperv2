from typing import List, Tuple
from ...configmanager import config
from ...integration.abcde.linux import run_abcde
from ...job.job import Job


def rip_audio_cd(job: Job) -> List[Tuple[List[str], str]]:
    """
    Returns the abcde ripping step for an audio CD job.

    :param job: The Job instance
    :return: A list with a single tuple: (command, step description)
    """
    cd_config = config.section("CD")
    command = run_abcde(
        drive_path=job.drive,
        output_format=cd_config["outputformat"],
        config_path=cd_config["configpath"],
        additional_options=cd_config["additionaloptions"]
    )
    return [(command, "Ripping & Encoding Audio CD")]
