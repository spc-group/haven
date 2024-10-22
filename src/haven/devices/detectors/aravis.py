from ophyd_async.epics.adcore import ADBaseIO
from ophyd_async.epics.adaravis import AravisDetector as DetectorBase
from ophyd_async.core import YMDPathProvider, UUIDFilenameProvider, SubsetEnum
from ophyd_async.epics.signal import epics_signal_rw_rbv, epics_signal_r
from ophyd_async.epics.adcore import (
    NDFileHDFIO,
    ADHDFWriter,
    ADBaseDataType,
)

from .area_detectors import HavenDetector


AravisTriggerSource = SubsetEnum["Software", "Line1"]


class AravisDetector(HavenDetector, DetectorBase):
    _ophyd_labels_ = {"cameras", "detectors"}

    def __init__(self, prefix, *args, **kwargs):
        super().__init__(*args, prefix=prefix, **kwargs)
        # Replace a signal that has different enum options
        self.drv.trigger_source = epics_signal_rw_rbv(
            AravisTriggerSource,  # type: ignore
            f"{prefix}cam1:TriggerSource",
        )
        self.set_name(self.name)
        
