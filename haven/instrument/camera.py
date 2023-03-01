import logging
import warnings
from typing import Optional, Sequence

from ophyd.areadetector.cam import CamBase

from .instrument_registry import registry
from .._iconfig import load_config


log = logging.getLogger(__name__)


__all__ = ["Camera", "load_cameras"]


class Camera(CamBase):
    """One of the beamline's GigE Vision cameras.

    Parameters
    ==========
    prefix:
      The process variable prefix for the camera.
    name:
      The bluesky-compatible device name.
    description:
      The human-readable description of this device. If omitted,
      *name* will be used.

    """

    def __init__(
        self, prefix: str, name: str, description: Optional[str] = None, *args, **kwargs
    ):
        if description is None:
            description = name
        self.description = description
        super().__init__(prefix, name=name, *args, **kwargs)


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
    for (key, device) in devices.items():
        cam = Camera(
            prefix=f"{device['ioc']}:",
            name=device["name"],
            description=device["description"],
            labels={"cameras"},
        )
        try:
            cam.wait_for_connection()
        except TimeoutError:
            msg = f"Could not connect to camera {name} ({device['ioc']})"
            log.warning(msg)
            warnings.warn(msg)
        else:
            registry.register(cam)
            cameras.append(cam)
    return cameras
