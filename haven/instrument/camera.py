import logging
import warnings
from typing import Optional, Sequence

from ophyd import (
    CamBase,
    DetectorBase,
    SingleTrigger,
    Kind,
    ADComponent as ADCpt,
    EpicsSignal,
)
from ophyd.areadetector.plugins import ImagePlugin_V34, PvaPlugin_V34, OverlayPlugin


from .instrument_registry import registry
from .._iconfig import load_config


log = logging.getLogger(__name__)


__all__ = ["Camera", "load_cameras"]


class AravisCam(CamBase):
    gain_auto = ADCpt(EpicsSignal, "GainAuto")
    acquire_time_auto = ADCpt(EpicsSignal, "ExposureAuto")


class Camera(SingleTrigger, DetectorBase):
    """
    A gige-vision camera described by EPICS.
    """

    def __init__(self, *args, description=None, **kwargs):
        super().__init__(*args, **kwargs)
        if description is None:
            description = self.prefix
        self.description = description

    cam = ADCpt(AravisCam, "cam1:")
    image = ADCpt(ImagePlugin_V34, "image1:")
    pva = ADCpt(PvaPlugin_V34, "Pva1:")
    overlays = ADCpt(OverlayPlugin, "Over1:")


def load_cameras(config=None) -> Sequence[Camera]:
    """Load cameras from config files and add to the registry.

    Returns
    =======
    Sequence[Camera]
      Sequence of the newly created and registered camera objects.

    """
    if config is None:
        config = load_config()
    # Get configuration details for the cameras
    devices = {k: v for (k, v) in config["camera"].items() if k.startswith("cam")}
    # Load each camera
    cameras = []
    for key, device in devices.items():
        cam = Camera(
            prefix=f"{device['ioc']}:",
            name=device["name"],
            description=device.get("description"),
            labels={"cameras"},
        )
        registry.register(cam)
        cameras.append(cam)
    return cameras
