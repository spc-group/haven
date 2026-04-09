from pathlib import Path

from ophyd_async.core import UUIDFilenameProvider, YMDPathProvider

from ...iconfig import HavenConfig, load_config


def default_path_provider(path: Path | None = None, config: HavenConfig | None = None):
    if config is None:
        config = load_config()
    if path is None:
        path = Path(config.area_detector_root_path)
    path_provider = YMDPathProvider(
        filename_provider=UUIDFilenameProvider(),
        base_directory_path=path,
        create_dir_depth=-4,
    )
    return path_provider
