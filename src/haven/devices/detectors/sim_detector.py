from ophyd_async.core import PathProvider
from ophyd_async.epics.adsimdetector import SimDetector as SimDetectorBase

from .area_detectors import default_path_provider
from .overlay import OverlayPlugin


class SimDetector(SimDetectorBase):
    _ophyd_labels_ = {"area_detectors", "detectors"}

    def __init__(self, prefix, path_provider: PathProvider | None = None, **kwargs):
        self.overlay = OverlayPlugin(f"{prefix}Over1:")
        if path_provider is None:
            path_provider = default_path_provider()
        super().__init__(prefix=prefix, path_provider=path_provider, **kwargs)
