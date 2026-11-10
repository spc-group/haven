from pathlib import Path

from ophyd_async.core import StaticFilenameProvider

from haven import DataManagementPathProvider, HavenConfig


def test_gets_path_from_config():
    cfg = HavenConfig(
        data_management={
            "station_name": "255IDZ",
            "area_detector_path": "/tmp/ad_files",
        }
    )
    filename_provider = StaticFilenameProvider("test_file.h5")
    provider = DataManagementPathProvider(
        filename_provider=filename_provider, config_provider=lambda: cfg
    )
    assert provider("bdet").directory_path == Path("/tmp/ad_files")
