from typing import Mapping
from pathlib import Path
import warnings

from ophyd_async.core import Device, YMDPathProvider, UUIDFilenameProvider

from .sim_detector import SimDetector
from ..._iconfig import load_config
from ... import exceptions


def default_path_provider(config=None):
    if config is None:
        config = load_config()
    # Generate a default path provider
    root_dir = Path(config.get("area_detector_root_path", "/tmp"))
    path_provider = YMDPathProvider(
        filename_provider=UUIDFilenameProvider(),
        base_directory_path=root_dir,
        create_dir_depth=-4,
    )
    return path_provider
