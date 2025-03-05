import numpy as np
from ophyd_async.epics.adcore._core_io import NDPluginBaseIO
from ophyd_async.epics.core import epics_signal_r


class ImagePlugin(NDPluginBaseIO):
    def __init__(self, prefix: str, name: str = "", protocol: str = "ca"):
        self.image_array = epics_signal_r(np.ndarray, f"{protocol}://{prefix}ArrayData")
        super().__init__(prefix=prefix, name=name)
