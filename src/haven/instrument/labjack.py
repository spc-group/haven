from ophyd import (
    Device,
    EpicsSignal,
    EpicsSignalRO,
    Component as Cpt,
    FormattedComponent as FCpt,
)
from apstools.synApps import EpicsRecordInputFields


class AnalogInput(EpicsRecordInputFields):

    differential = FCpt(
        EpicsSignal, "{self.base_prefix}Diff{self.ch_num}", string=True, kind="config"
    )
    high = FCpt(EpicsSignal, "{self.base_prefix}HOPR{self.ch_num}", kind="config")
    low = FCpt(EpicsSignal, "{self.base_prefix}LOPR{self.ch_num}", kind="config")
    temperature_units = FCpt(
        EpicsSignal,
        "{self.base_prefix}TempUnits{self.ch_num}",
        kind="config",
        string=True,
    )
    resolution = FCpt(
        EpicsSignal, "{self.base_prefix}Resolution{self.ch_num}", kind="config"
    )
    range = FCpt(
        EpicsSignal, "{self.base_prefix}Range{self.ch_num}", kind="config", string=True
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
