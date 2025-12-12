from ophyd_async.core import (
    StandardReadable,
)
from ophyd_async.core import StandardReadableFormat as Format
from ophyd_async.core import (
    StrictEnum,
)
from ophyd_async.epics.core import (
    epics_signal_r,
    epics_signal_rw,
)

from haven.devices.synApps import ScanInterval


class CL3000(StandardReadable):
    """Keyonce CL3000 distance sensor."""

    _ophyd_labels_ = {"detectors"}

    class MeasurementType(StrictEnum):
        MEAS_VALUE_ONLY = "Meas value only"
        MEAS_VALUE_RESULT_INFO = "Meas value + result info"
        MEAS_VALUE_JUDGEMENT = "Meas value + judgement"
        MEAS_RESULT_JUDGEMENT = "Meas + result + judgement"
        COUNT_MEAS_VALUE = "Count + Meas value"
        COUNT_MEAS_RESULT = "Count + Meas + result"
        COUNT_MEAS_JUDGEMENT = "Count + Meas + judgement"
        ALL = "All"

    def __init__(self, prefix, *, name: str = ""):
        with self.add_children_as_readables(Format.HINTED_SIGNAL):
            self.displacement = epics_signal_r(float, f"{prefix}measurement_RBV")

        with self.add_children_as_readables(Format.CONFIG_SIGNAL):
            self.measurement_type = epics_signal_rw(
                self.MeasurementType, f"{prefix}measType"
            )
            self.measurement_rate = epics_signal_rw(
                ScanInterval, f"{prefix}measurement.SCAN"
            )
            self.auto_zeroing = epics_signal_rw(bool, f"{prefix}autoZero")
            self.scaling = epics_signal_rw(
                float, f"{prefix}scaling_RBV", f"{prefix}scaling_set"
            )
            self.offset = epics_signal_rw(
                float, f"{prefix}offset_RBV", f"{prefix}offset_set"
            )

        self.counts = epics_signal_r(int, f"{prefix}Count_RBV")
        self.result = epics_signal_r(int, f"{prefix}resultInfo_RBV")
        self.judgement = epics_signal_r(str, f"{prefix}judgement_RBV")
        super().__init__(name=name)
