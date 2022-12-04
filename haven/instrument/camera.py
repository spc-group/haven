from typing import Optional

from ophyd.areadetector.cam import CamBase

from .instrument_registry import registry
from .._iconfig import load_config


class Camera(CamBase):
    def __init__(
        self, prefix: str, name: str, description: Optional[str] = None, *args, **kwargs
    ):
        if description is None:
            description = name
        self.description = description
        super().__init__(prefix, name=name, *args, **kwargs)


def load_cameras(config=None):
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
        registry.register(cam)
        cameras.append(cam)
    return cameras
