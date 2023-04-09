import logging
import warnings
from typing import Optional, Sequence

from ophyd import CamBase, DetectorBase, SingleTrigger, Kind, ADComponent
from ophyd.areadetector.plugins import (
    ImagePlugin_V34,
    PvaPlugin_V34,
)


from .instrument_registry import registry
from .._iconfig import load_config


log = logging.getLogger(__name__)


__all__ = ["Camera", "load_cameras"]


class Camera(SingleTrigger, DetectorBase):
    """
    A gige-vision camera described by EPICS.
    """

    cam = ADComponent(CamBase, "cam1:")
    image = ADComponent(ImagePlugin_V34, "image1:")
    pva = ADComponent(PvaPlugin_V34, "Pva1:")


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
            labels={"cameras", "area_detectors"},
        )
        registry.register(cam)
        cameras.append(cam)
    return cameras
