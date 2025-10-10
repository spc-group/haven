import importlib
from pathlib import Path

import pytest
from bluesky import RunEngine


@pytest.fixture()
def iconfig_simple(monkeypatch):
    iconfig_dir = Path(__file__).parent / "iconfig"
    monkeypatch.setenv("HAVEN_CONFIG_FILES", str(iconfig_dir / "iconfig_simple.toml"))


@pytest.mark.slow
def test_loads_run_engine(tmp_path, monkeypatch, iconfig_simple, mocker):
    # Set up environment
    profile_dir = tmp_path / "tiled" / "profiles"
    mocker.patch("tiled.profiles.paths", [profile_dir])
    # monkeypatch.setenv('TILED_PROFILES', str(profile_dir))
    # Load the startup module
    repo_dir = Path(__file__).parent.parent.parent
    spec = importlib.util.spec_from_file_location(
        "startup", repo_dir / "src" / "haven" / "startup.py"
    )
    startup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(startup)
    # Check what was loaded
    assert isinstance(startup.RE, RunEngine)
