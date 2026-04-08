"""Schema for instrument configuration in Haven.

These schema are defined as pydantic models. Configuration files can
be parsed and passed in to these schema for validation.

New configuration options should be added here, preferably with
sensible defaults where applicable, or `None` as a last resort.

"""

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, PositiveInt, create_model


class ConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


@dataclass(frozen=False)
class FeatureFlag:
    expires: float | int
    description: str = ""
    default: Any = False


FEATURE_FLAGS = {
    # Declare a feature flags to develop some new feature. Be
    # conservative when deciding on expiration dates.
    "undulator_fast_step_scanning_mode": FeatureFlag(
        expires=dt.datetime(2026, 5, 1).timestamp(),
        description="new controls added to the 25-ID undulator for step scanning faster",
    ),
}


# A dynamic config model ensures the schema match the declared feature
# flags
flag_fields = {
    flag_name: (Any, flag.default) for flag_name, flag in FEATURE_FLAGS.items()
}
FeatureFlagConfig = create_model("FeatureFlagConfig", **flag_fields)
print(FeatureFlagConfig)


class BssConfig(ConfigModel):
    uri: str
    beamline: str
    station_name: str
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
    redis_topic: str = "qs_default"


class RunEngineConfig(ConfigModel):
    use_progress_bar: bool = True
    default_metadata: RunEngineMetadata = RunEngineMetadata()


class HavenConfig(ConfigModel):
    area_detector_root_path: str = "/tmp"
    bss: BssConfig | None = None
    tiled: TiledConfig | None = None
    queueserver: QueueserverConfig = QueueserverConfig()
    run_engine: RunEngineConfig = RunEngineConfig()
    device_files: Sequence[str] = ["./devices_common.toml"]
    feature_flags: FeatureFlagConfig = FeatureFlagConfig()  # type: ignore
