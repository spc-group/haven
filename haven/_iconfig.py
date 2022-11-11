"""
Provide information from the iconfig.toml file.

Example TOML configuration file::

    # simple key:value pairs

    ADSIM_IOC_PREFIX: "bdpad:"
    GP_IOC_PREFIX: "bdp:"
    catalog: bdp2022
"""

__all__ = [
    "load_config",
]

import logging
from typing import Sequence
import pathlib

from mergedeep import merge
import tomli

log = logging.getLogger(__name__)


CONFIG_FILES = [
    pathlib.Path(__file__).parent / "iconfig_default.toml",
    pathlib.Path("~/bluesky/").expanduser() / "iconfig.toml",
    pathlib.Path("~/bluesky/instrument").expanduser() / "iconfig.toml",
]


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


def load_config(file_paths: Sequence[pathlib.Path] = CONFIG_FILES):
    config = {}
    merge(config, *load_files(file_paths))
    return config
