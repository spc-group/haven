import re

from ophyd_async.core import StandardReadable, StandardReadableFormat
from ophyd_async.epics.core import epics_signal_r

__all__ = ["PumpController", "TelevacIonGauge"]


class PumpController(StandardReadable):
    """A QPC ion pump controller.

    PVs taken from
    https://github.com/epics-modules/vac/blob/master/vacApp/Db/QPCstreams.db

    """

    _ophyd_labels_ = {"vacuum"}

    def __init__(self, prefix, name=""):
        # Work out which position the controller is in
        regex = r":[qm]pc+\d+([a-z])"
        match = re.search(regex, prefix)
        if match is None:
            raise ValueError(f"prefix {prefix} does not match expected pattern {regex}")
        position = ord(match.group(1)) - 96
        # Create signals
        with self.add_children_as_readables(StandardReadableFormat.HINTED_SIGNAL):
            self.pressure = epics_signal_r(float, f"{prefix}Pressure")
        with self.add_children_as_readables():
            self.current = epics_signal_r(float, f"{prefix}Current")
            self.voltage = epics_signal_r(float, f"{prefix}Voltage")
            self.status = epics_signal_r(str, f"{prefix}Status")
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.size = epics_signal_r(float, f"{prefix}PumpSize")
            self.description = epics_signal_r(str, f"{prefix}Pump{position}Name")
            self.model = epics_signal_r(str, f"{prefix}Model")
        super().__init__(name=name)


class TelevacIonGauge(StandardReadable):
    _ophyd_labels_ = {"vacuum"}

    def __init__(self, prefix, name=""):
        with self.add_children_as_readables():
            self.pressure = epics_signal_r(float, f"{prefix}.VAL")
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.device_type = epics_signal_r(str, f"{prefix}.TYPE")
        super().__init__(name=name)
