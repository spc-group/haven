"""Provide beamline configuration from the iconfig.toml file.

Example TOML configuration file: iconfig_testing.toml

"""

__all__ = [
    "load_config",
]

import datetime as dt
import logging
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Annotated as A

import tomli
from pydantic import BaseModel, ConfigDict, Field, PositiveInt

log = logging.getLogger(__name__)


class ConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def expires(expiration: dt.datetime) -> str | None:
    if dt.datetime.now() > expiration:
        return f"Expired at {expiration}"
    return None


class FeatureFlagConfig(ConfigModel):
    """Declare feature flags to develop some new feature."""

    # Be conservative when deciding on expiration dates.
    undulator_fast_step_scanning_mode: A[
        bool, Field(deprecated=expires(dt.datetime(2026, 6, 1)))
    ] = False


class DataManagementConfig(ConfigModel):
    # API URI's taken from the data management environmental variables
    scheduling_uri: str  # DM_APS_DB_WEB_SERVICE_URL
    data_transfer_uri: str  # DM_DAQ_WEB_SERVICE_URL
    workflow_uri: str  # DM_PROC_WEB_SERVICE_URL
    data_storage_uri: str  # DM_DS_WEB_SERVICE_URL
    catalog_uri: str  # DM_CAT_WEB_SERVICE_URL
    beamline: str  # DM_BEAMLINE_NAME
    station_name: str  # DM_STATION_NAME
    username: str | None = None
    password: str | None = None


class RunEngineMetadata(ConfigModel):
    facility: str = "Advanced Photon Source"
    beamline_id: str = "SPC Beamline (sector unknown)"
    xray_source: str | None = None


class TiledConfig(ConfigModel):
    writer_profile: str
    cache_filepath: str = "/tmp/tiled/http_response_cache.db"
    writer_backup_directory: str | None = None
    writer_batch_size: PositiveInt = 10


class QueueserverConfig(ConfigModel):
    redis_addr: str = "localhost:6379"
    redis_prefix: str = "qs_default"


class RunEngineConfig(ConfigModel):
    use_progress_bar: bool = Field(default=True, serialization_alias="USE_PROGRESS_BAR")
    default_metadata: RunEngineMetadata = Field(
        default=RunEngineMetadata(), serialization_alias="DEFAULT_METADATA"
    )


class FormatterConfig(ConfigModel):
    format: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt: str = "%Y-%m-%d %H:%M:%S"


class HandlerConfig(ConfigModel):
    level: str = "WARNING"
    formatter: str = "standard"
    class_: str = Field(
        alias="class", default="logging.StreamHandler"
    )  # Since "class" is a reserved keyword
    stream: str = "ext://sys.stderr"  # Default is stderr


class LoggerConfig(ConfigModel):
    handlers: Sequence[str] = []
    level: str
    propagate: bool = False


class LoggingConfig(ConfigModel):
    version: int = 1
    incremental: bool = False
    disable_existing_loggers: bool = True
    formatters: Mapping[str, FormatterConfig] = {"standard": FormatterConfig()}
    handlers: Mapping[str, HandlerConfig] = {
        "default": HandlerConfig(level="INFO", formatter="standard")
    }
    loggers: Mapping[str, LoggerConfig] = {
        "": LoggerConfig(handlers=["default"], level="WARNING"),
        "haven": LoggerConfig(handlers=["default"], level="INFO"),
    }


class HavenConfig(ConfigModel):
    area_detector_root_path: str = "/tmp"
    mock_devices: bool = False
    data_management: DataManagementConfig | None = None
    tiled: TiledConfig | None = None
    queueserver: QueueserverConfig = QueueserverConfig()
    run_engine: RunEngineConfig = Field(
        default=RunEngineConfig(), serialization_alias="RUN_ENGINE"
    )
    device_files: Sequence[str] = []
    feature_flags: FeatureFlagConfig = FeatureFlagConfig()  # type: ignore
    logging: LoggingConfig | None = None

    def device_parameters(self):
        """Return the parameters for the devices from "device_files" key."""
        params = {}
        for fp in self.device_files:
            with open(fp, mode="rb") as fd:
                for key, defns in tomli.load(fd).items():
                    params[key] = [*params.get(key, []), *defns]
        return params


def load_file(file_path: Path):
    """Generate the configs for files as dictionaries."""
    with open(file_path, mode="rb") as fd:
        log.debug(f"Loading config file: {fd}")
        config = tomli.load(fd)
        # Resolve relative paths since we know we have the main file
        if "device_files" in config:
            config["device_files"] = [
                str(file_path.parent / fp) for fp in config["device_files"]
            ]
        return config


def default_config_file():
    if os.environ.get("HAVEN_CONFIG", "") != "":
        return Path(os.environ["HAVEN_CONFIG"])
    else:
        raise RuntimeError(
            "Could not find Haven configuration file. "
            "Set `HAVEN_CONFIG` environmental variable with path "
            "to configuration file."
        )


def load_config(
    config: Path | str | Mapping | None = None,
) -> HavenConfig:
    """Load TOML config files.

    Will load files specified in the following locations:

    1. *file_paths* argument
    2. The $HAVEN_CONFIG environmental variable.

    """
    if config is None:
        # Add config file from environmental variable
        try:
            config = default_config_file()
        except RuntimeError as exc:
            config = {}
    # Load the files from disk
    config_dict = config if isinstance(config, Mapping) else load_file(Path(config))
    return HavenConfig(**config_dict)


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
