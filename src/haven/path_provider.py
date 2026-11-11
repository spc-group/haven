from collections.abc import Callable
from pathlib import Path

from ophyd_async.core import (
    FilenameProvider,
    PathInfo,
    PathProvider,
)
from ophyd_async.core._path_providers import generate_directory_uri

from .iconfig import HavenConfig, load_config


class DataManagementPathProvider(PathProvider):
    """All files will be within a data management experiment folder.

    The path to the folder should be stored in the Haven configuration
    with the key 'data_management.area_detector_path'.

    'data_management.area_detector_uri' can also be set to provide a
    client-side directory URI for these files when reading the results
    (e.g. Tiled).

    """

    def __init__(
        self,
        filename_provider: FilenameProvider,
        config_provider: Callable[[], HavenConfig] = load_config,
    ) -> None:
        self._filename_provider = filename_provider
        self._load_config = config_provider

    def __call__(self, datakey_name: str | None = None) -> PathInfo:
        filename = self._filename_provider(datakey_name)
        # Make sure the directory path key has been set in the config
        config = getattr(self._load_config(), "data_management", None)
        dir_path = getattr(config, "area_detector_path", None)
        if dir_path is None:
            raise ValueError(
                "Configuration key 'data_management.area_detector_path' not set."
            )
        else:
            dir_path = Path(dir_path) / datakey_name
        dir_uri = getattr(config, "area_detector_uri", None)

        return PathInfo(
            directory_path=dir_path,
            filename=filename,
            create_dir_depth=-1,
            directory_uri=dir_uri or generate_directory_uri(dir_path),
        )
