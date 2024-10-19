from typing import Mapping
from pathlib import Path

from ophyd_async.core import Device, YMDPathProvider, UUIDFilenameProvider

from .sim_detector import SimDetector
from ..instrument_registry import InstrumentRegistry, registry as default_registry
from ..device import connect_devices
from ..._iconfig import load_config
from ... import exceptions


def default_path_provider(config=None):
    if config is None:
        config = load_config()
    # Generate a default path provider
    root_dir = Path(config["area_detector"].get("root_path", "/tmp"))
    path_provider = YMDPathProvider(
        filename_provider=UUIDFilenameProvider(),
        base_directory_path=root_dir,
    )


async def load_area_detectors(
    config: Mapping = None,
    registry: InstrumentRegistry = default_registry,
    connect: bool = True,
    auto_name=True,
) -> list[Device]:

    if config is None:
        config = load_config()
    path_provider = default_path_provider(config)
    # Create the area detectors defined in the configuration
    devices = []
    for name, adconfig in config.get("area_detector", {}).items():
        try:
            DeviceClass = globals().get(adconfig["device_class"])
        except TypeError:
            # Not a sub-dictionary, so move on
            continue
        # Check that it's a valid device class
        if DeviceClass is None:
            msg = f"area_detector.{name}.device_class={adconfig['device_class']}"
            raise exceptions.UnknownDeviceConfiguration(msg)
        # Create the device co-routine
        devices.append(
            DeviceClass(
                prefix=f"{adconfig['prefix']}:",
                path_provider=path_provider,
                name=name,
            )
        )
    # Connect to devices
    if connect:
        devices = await connect_devices(
            devices, mock=not config["beamline"]["is_connected"], registry=registry
        )
    return devices
