"""
Provide beamline configuration from the iconfig.toml file.

Example TOML configuration file: iconfig_default.toml

"""

__all__ = [
    "load_config",
]

import argparse
import logging
import os
from collections.abc import Mapping
from pathlib import Path
from pprint import pprint
from typing import Sequence

import tomli
from mergedeep import merge

log = logging.getLogger(__name__)


_local_overrides = {}


class ConfigMapping(Mapping):
    _config: Mapping

    def __init__(self, config: Mapping):
        self._config = config

    def __getitem__(self, key):
        config = self._config
        for part in key.split("."):
            config = config[part]
        # If the value can still be mapped further, then return another config mapping
        if isinstance(config, Mapping):
            config = type(self)(config)
        return config

    def __iter__(self):
        for obj in self._config:
            yield obj

    def __len__(self):
        return len(self._config)


def load_file(file_path: Path):
    """Generate the configs for files as dictionaries."""
    fp = Path(file_path)
    if fp.exists():
        with open(fp, mode="rb") as fp:
            log.debug(f"Loading config file: {fp}")
            config = tomli.load(fp)
            return config
    else:
        log.info(f"Could not find config file, skipping: {fp}")
        return {}


def lookup_file_paths():
    if os.environ.get("HAVEN_CONFIG_FILES", "") != "":
        return [Path(fp) for fp in os.environ["HAVEN_CONFIG_FILES"].split(",")]
    elif os.environ.get("HAVEN_CONFIG_DIR", "") != "":
        return [Path(os.environ["HAVEN_CONFIG_DIR"]) / "iconfig.toml"]
    else:
        return [Path(__file__).parent / "iconfig_testing.toml"]


DEPRECATED_KEYS = [
    # (old_key, new_key)
    ("metadata", "RUN_ENGINE.DEFAULT_METADATA"),
    ("kafka", None),
    ("database", None),
    ("queueserver.control_host", None),
    ("queueserver.control_port", None),
    ("queueserver.info_host", None),
    ("queueserver.info_port", None),
]


def has_key(config, key: str) -> bool:
    """Check if a given dotted key is in a configuration dictionary."""
    for bit in key.split("."):
        try:
            config = config[bit]
        except (KeyError, TypeError):
            return False
    return True


def check_deprecated_keys(config):
    """Error if renamed keys aren't renamed, or warning if old keys are
    still there.

    """
    for old_key, new_key in DEPRECATED_KEYS:
        needs_new_key = new_key is not None and not has_key(config, new_key)
        has_old_key = has_key(config, old_key)
        if has_old_key and needs_new_key:
            # Without migrating the configuration, things will not work properly
            raise ValueError(f"Config key {old_key} has been replaced with {new_key}.")
        elif has_old_key:
            # Shouldn't break the configuration, just doesn't need to be there
            # To-do: wanted to make these warnings, but they weren't getting shown
            raise ValueError(f"Config key '{old_key}' is no longer used")


def load_config(*configs: Sequence[Path | Mapping]) -> ConfigMapping:
    """Load TOML config files.

    Will load files specified in the following locations:

    1. *file_paths* argument
    2. The $HAVEN_CONFIG_FILES environmental variable.
    3. The $HAVEN_CONFIG_DIR/iconfig.toml environmental variable.
    4. iconfig_default.toml file included with Haven.

    """
    if len(configs) == 0:
        # Add config file from environmental variable
        configs = lookup_file_paths()
    # Load configuration from TOML files
    configs = [cfg if isinstance(cfg, Mapping) else load_file(cfg) for cfg in configs]
    config = merge({}, *configs, _local_overrides)
    check_deprecated_keys(config)
    return ConfigMapping(config)


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
    try:
        value = value.strip()
    except AttributeError:
        # It's not a simple string, so pretty print it
        pprint(value)
    else:
        # Simple string, so just print it
        print(value)


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2023, UChicago Argonne, LLC
#
# Distributed under the terms of the 3-Clause BSD License
#
# The full license is in the file LICENSE, distributed with this software.
#
# DISCLAIMER
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# -----------------------------------------------------------------------------
