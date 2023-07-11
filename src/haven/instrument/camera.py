import logging
import warnings
from typing import Optional, Sequence

from ophyd import (
    CamBase,
    SingleTrigger,
    Kind,
    ADComponent as ADCpt,
    EpicsSignal,
    do_not_wait_for_lazy_connection,
)
from ophyd.areadetector.base import EpicsSignalWithRBV as SignalWithRBV
from ophyd.areadetector.plugins import (
    ImagePlugin_V34,
    PvaPlugin_V34,
    OverlayPlugin,
    ROIPlugin_V34,
)


from .instrument_registry import registry
from .area_detector import DetectorBase, StatsPlugin_V34, SimDetector, AsyncCamMixin
from .device import await_for_connection
from .._iconfig import load_config
from .. import exceptions


log = logging.getLogger(__name__)


__all__ = ["AravisDetector", "load_cameras"]


class AravisCam(AsyncCamMixin, CamBase):
    gain_auto = ADCpt(EpicsSignal, "GainAuto")
    acquire_time_auto = ADCpt(EpicsSignal, "ExposureAuto")


class AravisDetector(SingleTrigger, DetectorBase):
    """
    A gige-vision camera described by EPICS.
    """

    cam = ADCpt(AravisCam, "cam1:")
    image = ADCpt(ImagePlugin_V34, "image1:")
    pva = ADCpt(PvaPlugin_V34, "Pva1:")
    overlays = ADCpt(OverlayPlugin, "Over1:")
    roi1 = ADCpt(ROIPlugin_V34, "ROI1:", kind=Kind.config)
    roi2 = ADCpt(ROIPlugin_V34, "ROI2:", kind=Kind.config)
    roi3 = ADCpt(ROIPlugin_V34, "ROI3:", kind=Kind.config)
    roi4 = ADCpt(ROIPlugin_V34, "ROI4:", kind=Kind.config)
    stats1 = ADCpt(StatsPlugin_V34, "Stats1:", kind=Kind.normal)
    stats2 = ADCpt(StatsPlugin_V34, "Stats2:", kind=Kind.normal)
    stats3 = ADCpt(StatsPlugin_V34, "Stats3:", kind=Kind.normal)
    stats4 = ADCpt(StatsPlugin_V34, "Stats4:", kind=Kind.normal)
    stats5 = ADCpt(StatsPlugin_V34, "Stats5:", kind=Kind.normal)


async def make_camera_device(
    DeviceClass, prefix: str, name: str, description: str, labels: set[str]
) -> DetectorBase:
    """Create camera device and add it to the registry.

    Returns
    =======
    device
      The newly created and registered camera object.

    """
    device = DeviceClass(
        prefix=prefix,
        name=name,
        description=description,
        labels=labels,
    )
    # Make sure we can connect
    try:
        await await_for_connection(device)
    except TimeoutError as e:
        log.warning(f"Could not connect to camera: {name}: {e}.")
        return None
    else:
        registry.register(device)
        return device


def load_camera_coros(config=None) -> Sequence[DetectorBase]:
    """Create co-routines for loading cameras from config files.

    Returns
    =======
    coros
      A set of co-routines that can be awaited to load the cameras.

    """
    if config is None:
        config = load_config()
    # Get configuration details for the cameras
    devices = {
        k: v
        for (k, v) in config["camera"].items()
        if hasattr(v, "keys") and "prefix" in v.keys()
    }
    # Load each camera
    for key, cam_config in devices.items():
        class_name = cam_config.get("device_class", "AravisDetector")
        camera_name = cam_config.get("name", key)
        description = cam_config.get("description", cam_config.get("name", key))
        DeviceClass = globals().get(class_name)
        # Check that it's a valid device class
        if DeviceClass is None:
            msg = f"camera.{key}.device_class={cam_config['device_class']}"
            raise exceptions.UnknownDeviceConfiguration(msg)
        yield make_camera_device(
            DeviceClass=DeviceClass,
            prefix=f"{cam_config['prefix']}:",
            name=camera_name,
            description=description,
            labels={"cameras"},
        )
