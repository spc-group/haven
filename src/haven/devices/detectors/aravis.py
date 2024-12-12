from ophyd_async.core import SubsetEnum
from ophyd_async.epics.adaravis import AravisDetector as DetectorBase
from ophyd_async.epics.signal import epics_signal_rw_rbv, epics_signal_r
from numpy.typing import NDArray
import numpy as np

from .area_detectors import HavenDetector

AravisTriggerSource = SubsetEnum["Software", "Line1"]


AravisPixelFormat = SubsetEnum["Mono8"]


class AravisDetector(HavenDetector, DetectorBase):
    _ophyd_labels_ = {"cameras", "detectors"}

    def __init__(self, prefix, *args, **kwargs):
        super().__init__(*args, prefix=prefix, **kwargs)
        self.image_array = epics_signal_r(NDArray[np.int16], f"{prefix}image1:ArrayData")
        self.drv.pixel_format = epics_signal_rw_rbv(
            AravisPixelFormat,
            f"{prefix}cam1:PixelFormat",
        )
        # Replace a signal that has different enum options
        self.drv.trigger_source = epics_signal_rw_rbv(
            AravisTriggerSource,  # type: ignore
            f"{prefix}cam1:TriggerSource",
        )
        self.set_name(self.name)
