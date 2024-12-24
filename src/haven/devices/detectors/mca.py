import numpy as np
from ophyd_async.core import Device
from ophyd_async.epics.core import epics_signal_rw_rbv, epics_signal_r


class MCA(Device):
    def __init__(self, prefix: str, name: str = ""):
        self.spectrum = epics_signal_r(np.float64, f"{prefix}ArrayData")
        self.dead_time_percent = epics_signal_r(float, f"{prefix}DeadTime_RBV")
        self.dead_time_factor = epics_signal_r(float, f"{prefix}DTFactor_RBV")
        super().__init__(name=name)
