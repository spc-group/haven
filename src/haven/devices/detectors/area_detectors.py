from collections.abc import Mapping
from pathlib import Path

from ophyd_async.core import UUIDFilenameProvider, YMDPathProvider

from ..._iconfig import load_config


def default_path_provider(path: Path | None = None, config: Mapping | None = None):
    if config is None:
        config = load_config()
    if path is None:
        path = Path(config.get("area_detector_root_path", "/tmp"))
    path_provider = YMDPathProvider(
        filename_provider=UUIDFilenameProvider(),
        base_directory_path=path,
        create_dir_depth=-4,
    )
    return path_provider
