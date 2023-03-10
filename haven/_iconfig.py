"""
Provide beamline configuration from the iconfig.toml file.

Example TOML configuration file: iconfig_default.toml

"""

__all__ = [
    "load_config",
]

import os
import logging
from typing import Sequence
import pathlib
import argparse
from functools import lru_cache

from mergedeep import merge
import tomli

log = logging.getLogger(__name__)


CONFIG_FILES = [
    pathlib.Path(__file__).parent / "iconfig_default.toml",
    pathlib.Path("~/bluesky/").expanduser() / "iconfig.toml",
    pathlib.Path("~/bluesky/instrument").expanduser() / "iconfig.toml",
]

# Add config file from environmental variable
try:
    CONFIG_FILES.extend(
        [pathlib.Path(fp.strip()) for fp in os.environ["HAVEN_CONFIG_FILES"].split(",")]
    )
except KeyError:
    pass


def load_files(file_paths: Sequence[pathlib.Path]):
    """Generate the configs for files as dictionaries."""
    for fp in file_paths:
        if fp.exists():
            with open(fp, mode="rb") as fp:
                log.info(f"Loading config file: {fp}")
                config = tomli.load(fp)
                yield config

        else:
            log.debug(f"Could not find config file, skipping: {fp}")


@lru_cache()
def load_config(file_paths: Sequence[pathlib.Path] = CONFIG_FILES):
    """Load TOML config files."""
    config = {}
    merge(config, *load_files(file_paths))
    return config


def print_config_value(args: Sequence[str] = None):
    """Print a config value from TOML files.

    Parameters
    ----------
    key
      The path to the value to retrieve from config files. Sections
      should be separated by dots, e.g. "shutter.A.open_pv"

    """
    # Set up command line arguments
    parser = argparse.ArgumentParser(
        prog="haven_config",
        description="Retrieve a value from Haven's config files.",
    )
    parser.add_argument("key", help="The dot-separated key to look up.")
    args = parser.parse_args(args=args)
    # Get the keys from the config file
    value = load_config()
    for part in args.key.split("."):
        value = value[part]
    print(value.strip())
