from apstools.synApps import EpicsRecordDeviceCommonAll, EpicsRecordInputFields
from ophyd import Device, EpicsSignal
from ophyd import FormattedComponent as FCpt
from strenum import StrEnum


class AnalogInput(EpicsRecordInputFields, EpicsRecordDeviceCommonAll):
    class DiffStates(StrEnum):
        single_ended = "Single-Ended"
        differential = "Differential"

    differential = FCpt(
        EpicsSignal, "{self.base_prefix}Diff{self.ch_num}", kind="config"
    )
    high = FCpt(EpicsSignal, "{self.base_prefix}HOPR{self.ch_num}", kind="config")
    low = FCpt(EpicsSignal, "{self.base_prefix}LOPR{self.ch_num}", kind="config")
    temperature_units = FCpt(
        EpicsSignal,
        "{self.base_prefix}TempUnits{self.ch_num}",
        kind="config",
    )
    resolution = FCpt(
        EpicsSignal, "{self.base_prefix}Resolution{self.ch_num}", kind="config"
    )
    range = FCpt(
        EpicsSignal,
        "{self.base_prefix}Range{self.ch_num}",
        kind="config",
    )
    mode = FCpt(EpicsSignal, "{self.base_prefix}Mode{self.ch_num}", kind="config")
    enable = FCpt(EpicsSignal, "{self.base_prefix}Enable{self.ch_num}")

    @property
    def base_prefix(self):
        return self.prefix.rstrip("0123456789")

    @property
    def ch_num(self):
        return self.prefix[len(self.base_prefix) :]


class LabJackT7(Device):
    """A labjack T7 data acquisition unit (DAQ)."""

    ...
