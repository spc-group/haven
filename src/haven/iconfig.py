"""Provide beamline configuration from the iconfig.toml file.

Example TOML configuration file: iconfig_testing.toml

"""

__all__ = [
    "load_config",
]

import logging
import os
import time
import warnings
from collections.abc import Callable, Mapping
from functools import wraps
from pathlib import Path
from typing import Any

import tomli
from pydantic import BaseModel

from haven.exceptions import ExpiredFeatureFlag, UndeclaredFeatureFlag

from .iconfig_schema import FEATURE_FLAGS, HavenConfig

log = logging.getLogger(__name__)


class Configuration(HavenConfig):
    """A mapping of config keys to values with validation.

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

    _config: Mapping | Path | str
    _feature_flags: Mapping[str, Any]

    def __init__(
        self,
        config: Mapping | Path | str,
        feature_flags: Mapping[str, Any] = FEATURE_FLAGS,
        model_class: BaseModel = HavenConfig,
    ):
        self._config = config
        self._feature_flags = feature_flags
        self._model_class = model_class

    def check_feature_flags(self, config):
        feature_flags = self._feature_flags
        flags = config.get("feature_flags", {})
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

    def _model(self):
        # Load configuration from TOML files
        config = _load_config_dict(self._config)
        check_deprecated_keys(config)
        model = self._model_class(**config)
        self.check_feature_flags(config)
        return model

    def __getitem__(self, key):
        model = self._model()
        extra_parts = []
        _key = key
        while _key != "":
            if hasattr(model, _key):
                if len(extra_parts) > 0:
                    # Look up the rest of the keys
                    model = getattr(model, _key)
                    _key = ".".join(extra_parts[::-1])
                    extra_parts = []
                    continue
                elif isinstance(getattr(model, _key), BaseModel):
                    # Not a leaf of the config tree
                    return getattr(model, _key).model_dump()
                else:
                    # Leaf of the config tree
                    return getattr(model, _key)
            try:
                _key, tail = _key.rsplit(".", maxsplit=1)
            except ValueError:
                # We can't split anymore '.', so lookup has failed
                raise KeyError(key)
            extra_parts.append(tail)

    def __iter__(self):
        model = self._model()
        return iter(model.model_dump().keys())

    # def __len__(self):
    #     return len(self._config)

    def feature_flag(self, key: str) -> Any:
        # Feature flags must be declared so they can be properly
        # managed (expired, etc)
        try:
            flag = self._feature_flags[key]
        except KeyError as exc:
            raise UndeclaredFeatureFlag(key) from exc
        # Now get the feature flag's value if possible
        return self[f"feature_flags.{key}"]

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
        with open(fp, mode="rb") as fd:
            log.debug(f"Loading config file: {fd}")
            config = tomli.load(fd)
            return config
    else:
        log.info(f"Could not find config file, skipping: {fp}")
        return {}


def default_config_file():
    if os.environ.get("HAVEN_CONFIG_FILE", "") != "":
        return Path(os.environ["HAVEN_CONFIG_FILE"])
    elif os.environ.get("HAVEN_CONFIG_DIR", "") != "":
        return Path(os.environ["HAVEN_CONFIG_DIR"]) / "iconfig.toml"
    else:
        raise RuntimeError(
            "Could not find Haven configuration file. "
            "Set `HAVEN_CONFIG_FILE` environmental variable with path "
            "to configuration file."
        )


DEPRECATED_KEYS = [
    # (old_key, new_key)
    ("metadata", "RUN_ENGINE.DEFAULT_METADATA"),
    ("kafka", None),
    ("database", None),
    ("queueserver.control_host", None),
    ("queueserver.control_port", None),
    ("queueserver.info_host", None),
    ("queueserver.info_port", None),
    ("soft_glue_delay", "soft_glue_flyer_controller"),
    ("monochromator", "axilon_monochromator"),
    ("haven.features.grid_fly_scan_by_line", None),
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


def _load_config_dict(config: Path | str | Mapping):
    return config if isinstance(config, Mapping) else load_file(Path(config))


def load_config(config: Path | str | Mapping | None = None) -> Configuration:
    """Load TOML config files.

    Will load files specified in the following locations:

    1. *file_paths* argument
    2. The $HAVEN_CONFIG_FILES environmental variable.
    3. The $HAVEN_CONFIG_DIR/iconfig.toml environmental variable.
    4. iconfig_default.toml file included with Haven.

    """
    if config is None:
        # Add config file from environmental variable
        try:
            config = default_config_file()
        except RuntimeError as exc:
            log.warning(exc)
            config = {}
    return Configuration(config)


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2026, UChicago Argonne, LLC
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
