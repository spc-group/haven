from ophyd_async.core import SubsetEnum
from ophyd_async.epics.adaravis import AravisDetector as DetectorBase
from ophyd_async.epics.core import epics_signal_rw_rbv

from .area_detectors import HavenDetector


class AravisTriggerSource(SubsetEnum):
    SOFTWARE = "Software"
    LINE1 = "Line1"


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
