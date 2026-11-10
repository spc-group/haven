import uuid
from pathlib import Path

from ophyd_async.core import UUIDFilenameProvider, YMDPathProvider

from ...iconfig import HavenConfig, load_config
from ...path_provider import DataManagementPathProvider


def default_path_provider(path: Path | None = None, config: HavenConfig | None = None):
    if config is None:
        config = load_config()
    if path is None:
        path = Path(config.area_detector_root_path)
    path_provider = YMDPathProvider(
        filename_provider=UUIDFilenameProvider(uuid_call_func=uuid.uuid7),
        base_directory_path=path,
        create_dir_depth=-4,
    )
    return path_provider


def data_management_path_provider(
    path: Path | None = None, config: HavenConfig | None = None
):
    if config is None:
        config = load_config()
    path_provider = DataManagementPathProvider(
        filename_provider=UUIDFilenameProvider(uuid_call_func=uuid.uuid7),
    )
    return path_provider
