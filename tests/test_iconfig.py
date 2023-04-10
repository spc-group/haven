import os
from pathlib import Path
import importlib

from haven import _iconfig
from haven._iconfig import load_config, print_config_value


def test_default_values():
    config = load_config()
    assert "beamline" in config.keys()


def test_loading_a_file():
    test_file = Path(__file__).resolve().parent / "test_iconfig.toml"
    config = load_config(file_paths=(test_file,))
    assert config["beamline"]["pv_prefix"] == "spam"


def test_config_files_from_env():
    # Set the environmental variable with the path to a test TOML file
    test_file = Path(__file__).resolve().parent / "test_iconfig.toml"
    os.environ["HAVEN_CONFIG_FILES"] = str(test_file)
    # Load the configuration
    importlib.reload(_iconfig)
    config = _iconfig.load_config()
    # Check that the test file was loaded
    assert config["beamline"]["pv_prefix"] == "spam"


def test_merging_dicts():
    """Do the entries from multiple dictioneries merge properly?"""
    this_dir = Path(__file__).resolve().parent
    default_files = [
        this_dir.parent / "haven" / "iconfig_default.toml",
        this_dir / "iconfig_testing.toml",
    ]
    test_file = this_dir / "test_iconfig.toml"
    config = load_config(file_paths=(*default_files, test_file))
    assert "description" in config["camera"]["camA"].keys()


def test_haven_config_cli(capsys):
    """Test the function used as a CLI way to get config values."""
    print_config_value(["monochromator.ioc"])
    # Check stdout for config value
    captured = capsys.readouterr()
    assert captured.out == "mono_ioc\n"
