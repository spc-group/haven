from pathlib import Path

from ophyd_async.core import UUIDFilenameProvider, YMDPathProvider

from ..._iconfig import load_config


class HavenDetector:
    def __init__(self, *args, writer_path=None, **kwargs):
        # Create a path provider based on the path given
        if writer_path is None:
            writer_path = default_path()
        path_provider = YMDPathProvider(
            filename_provider=UUIDFilenameProvider(),
            base_directory_path=writer_path,
            create_dir_depth=-4,
        )
        super().__init__(*args, path_provider=path_provider, **kwargs)


def default_path(config=None):
    if config is None:
        config = load_config()
    # Generate a default path provider
    root_dir = Path(config.get("area_detector_root_path", "/tmp"))
    return root_dir
