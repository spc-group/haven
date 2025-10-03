"""
Provide beamline configuration from the iconfig.toml file.

Example TOML configuration file: iconfig_default.toml

"""

__all__ = [
    "load_config",
]

import argparse
import datetime as dt
import logging
import os
import time
import warnings
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from pprint import pprint
from typing import Any

import tomli
from mergedeep import merge

from haven.exceptions import ExpiredFeatureFlag, UndeclaredFeatureFlag

log = logging.getLogger(__name__)


_local_overrides = {}


@dataclass(frozen=True)
class FeatureFlag:
    expires: float | int
    description: str = ""
    default: Any = False


FEATURE_FLAGS = {
    # Declare a feature flags to develop some new feature. Be
    # conservative when deciding on expiration dates.
    "grid_fly_scan_by_line": FeatureFlag(
        expires=dt.datetime(2025, 11, 1).timestamp(),
    ),
    "apstools_2025-3_cycle_support": FeatureFlag(
        expires=dt.datetime(2025, 10, 15).timestamp(),
        description="https://github.com/BCDA-APS/apstools/issues/1122",
        default=True,
    ),
    "undulator_fast_step_scanning_mode": FeatureFlag(
        expires=dt.datetime(2025, 10, 30).timestamp(),
        description="new controls added to the 25-ID undulator for step scanning faster",
    ),
}


class Configuration(Mapping):
    """A mapping of config keys to values.

    Allows complicated lookup by dotted keys:

    .. code-block:: python

        example_config = {
            "spam": {
                "eggs": "cheese"
            }
        }
        config = Configuration(example_config)
        assert config["spam"]["eggs"] == config["spam.eggs"]

    """

    _configs: Sequence[Mapping | Path | str]
    _feature_flags: Mapping[str:Any]

    def __init__(
        self,
        *configs: Sequence[Mapping | Path | str],
        feature_flags: Mapping[str:Any] = FEATURE_FLAGS,
    ):
        self._configs = configs
        self._feature_flags = feature_flags

    def check_feature_flags(self, config):
        feature_flags = self._feature_flags
        flags = config.get("haven.feature_flags", {})
        extra_flags = [
            flag for flag in flags.keys() if flag not in feature_flags.keys()
        ]
        if len(extra_flags) > 0:
            raise UndeclaredFeatureFlag(extra_flags)
        # See if any flags are expired
        now = time.time()
        expired = [name for name, flag in feature_flags.items() if flag.expires < now]
        if len(expired) > 0:
            warnings.warn(
                f"Expired feature flags are declared: {expired}.", ExpiredFeatureFlag
            )

    def _config(self):
        # Load configuration from TOML files
        configs = [
            cfg if isinstance(cfg, Mapping) else load_file(cfg) for cfg in self._configs
        ]
        config = merge({}, *configs, _local_overrides)
        check_deprecated_keys(config)
        self.check_feature_flags(config)
        return config

    def __getitem__(self, key):
        config = self._config()
        extra_parts = []
        _key = key
        while _key != "":
            if _key in config:
                if len(extra_parts) > 0:
                    # Look up the rest of the keys
                    config = config[_key]
                    _key = ".".join(extra_parts[::-1])
                    extra_parts = []
                    continue
                elif isinstance(config[_key], Mapping):
                    # Not a leaf of the config tree
                    return type(self)(config[_key])
                else:
                    # Leaf of the config tree
                    return config[_key]
            try:
                _key, tail = _key.rsplit(".", maxsplit=1)
            except ValueError:
                # We can't split anymore '.', so lookup has failed
                raise KeyError(key)
            extra_parts.append(tail)

    def __iter__(self):
        for obj in self._config():
            yield obj

    def __len__(self):
        return len(self._config)

    def feature_flag(self, key: str) -> Any:
        # Feature flags must be declared so they can be properly
        # managed (expired, etc)
        try:
            flag = self._feature_flags[key]
        except KeyError as exc:
            raise UndeclaredFeatureFlag(key) from exc
        # Now get the feature flag's value if possible
        try:
            return self[f"haven.feature_flags.{key}"]
        except KeyError as exc:
            return self._feature_flags[key].default

    def with_feature_flag(self, flag: str, alternate: Callable, *, eq: Any = True):
        """Call an alternate implementation if a feature flag is set.

        The argument *eq* can be used to only respond on a specific
        value for the flag. By default, any truthy value will trigger
        *alternate* instead of the original function/class.

        Parameters
        ==========
        flag:
          The name of the feature flag to check.
        alternate
          What to call if the feature flag is present.
        eq
          Value against which to compare the feature flag.

        """

        def wrapper(func):
            @wraps(func)
            def inner(*args, **kwargs):
                if self.feature_flag(flag) == eq:
                    return alternate(*args, **kwargs)
                else:
                    return func(*args, **kwargs)

            return inner

        return wrapper


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


def load_config(*configs: Sequence[Path | str | Mapping]) -> Configuration:
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
    return Configuration(*configs)


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
