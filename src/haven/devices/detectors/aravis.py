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


class AravisDetector(HavenDetector, DetectorBase):
    _ophyd_labels_ = {"cameras", "detectors"}
