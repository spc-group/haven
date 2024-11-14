import asyncio

from ophyd_async.core import (
    Device,
    StandardReadable,
    StandardReadableFormat,
    StrictEnum,
    SubsetEnum,
)
from ophyd_async.epics.core import epics_signal_r, epics_signal_rw, epics_signal_x


class AlarmStatus(SubsetEnum):
    NO_ALARM = "NO_ALARM"
    READ = "READ"
    WRITE = "WRITE"
    HIHI = "HIHI"
    HIGH = "HIGH"
    LOLO = "LOLO"
    LOW = "LOW"
    STATE = "STATE"
    COS = "COS"
    COMM = "COMM"
    TIMEOUT = "TIMEOUT"
    HWLIMIT = "HWLIMIT"
    CALC = "CALC"
    SCAN = "SCAN"
    LINK = "LINK"
    SOFT = "SOFT"
    # BAD_SUB = "BAD_SUB"
    # UDF = "UDF"
    # DISABLE = "DISABLE"
    # SIMM = "SIMM"
    # READ_ACCESS = "READ_ACCESS"
    # WRITE_ACCESS = "WRITE_ACCESS"


class AlarmSeverity(StrictEnum):
    NO_ALARM = "NO_ALARM"
    MINOR = "MINOR"
    MAJOR = "MAJOR"
    INVALID = "INVALID"


class EpicsRecordDeviceCommonAll(StandardReadable):
    """
    Many of the fields common to all EPICS records.

    Some fields are not included because they are not interesting to
    an EPICS client or are already provided in other support.
    """

    # More valid options are specific to the record type
    # Subclasses may override this attribute
    class ScanInterval(SubsetEnum):
        PASSIVE = "Passive"
        EVENT = "Event"
        IO_INTR = "I/O Intr"
        SCAN_10 = "10 second"
        SCAN_5 = "5 second"
        SCAN_2 = "2 second"
        SCAN_1 = "1 second"
        SCAN_0_5 = ".5 second"
        SCAN_0_2 = ".2 second"
        SCAN_0_1 = ".1 second"

    # Config signals
    def __init__(self, prefix: str, name: str = ""):
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.description = epics_signal_rw(str, f"{prefix}.DESC")
            self.scanning_rate = epics_signal_rw(self.ScanInterval, f"{prefix}.SCAN")
        # Other signals, not included in read
        self.disable_value = epics_signal_rw(int, f"{prefix}.DISV")
        self.scan_disable_input_link_value = epics_signal_rw(int, f"{prefix}.DISA")
        self.scan_disable_value_input_link = epics_signal_rw(str, f"{prefix}.SDIS")
        self.forward_link = epics_signal_rw(str, f"{prefix}.FLNK")

        self.alarm_status = epics_signal_r(AlarmStatus, f"{prefix}.STAT")
        self.alarm_severity = epics_signal_r(AlarmSeverity, f"{prefix}.SEVR")
        self.new_alarm_status = epics_signal_r(AlarmStatus, f"{prefix}.NSTA")
        self.new_alarm_severity = epics_signal_r(AlarmSeverity, f"{prefix}.NSEV")
        self.disable_alarm_severity = epics_signal_rw(AlarmSeverity, f"{prefix}.DISS")
        self.processing_active = epics_signal_r(int, f"{prefix}.PACT")
        self.process_record = epics_signal_x(f"{prefix}.PROC")
        self.trace_processing = epics_signal_rw(int, f"{prefix}.TPRO")

        super().__init__(name=name)


class EpicsSynAppsRecordEnableMixin(Device):
    """Supports ``{PV}Enable`` feature from user databases."""

    def __init__(self, prefix, name=""):
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.enable = epics_signal_rw(int, "Enable")
        super().__init__(name=name)

    async def reset(self):
        """set all fields to default values"""
        await asyncio.gather(
            self.enable.set(self.enable.enum_strs[1]), super().reset()  # Enable
        )


class EpicsRecordInputFields(EpicsRecordDeviceCommonAll):
    """
    Some fields common to EPICS input records.
    """

    class DeviceType(SubsetEnum):
        SOFT_CHANNEL = "Soft Channel"
        RAW_SOFT_CHANNEL = "Raw Soft Channel"
        ASYNC_SOFT_CHANNEL = "Async Soft Channel"

    def __init__(self, prefix: str, name: str = ""):
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.input_link = epics_signal_rw(str, f"{prefix}.INP")
            self.device_type = epics_signal_r(self.DeviceType, f"{prefix}.DTYP")
        super().__init__(prefix=prefix, name=name)


class EpicsRecordOutputFields(EpicsRecordDeviceCommonAll):
    """
    Some fields common to EPICS output records.
    """

    class DeviceType(SubsetEnum):
        SOFT_CHANNEL = "Soft Channel"
        RAW_SOFT_CHANNEL = "Raw Soft Channel"
        ASYNC_SOFT_CHANNEL = "Async Soft Channel"

    class ModeSelect(SubsetEnum):
        SUPERVISORY = "supervisory"
        CLOSED_LOOP = "closed_loop"

    def __init__(self, prefix: str, name: str = ""):
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.output_link = epics_signal_rw(str, f"{prefix}.OUT")
            self.desired_output_location = epics_signal_rw(str, f"{prefix}.DOL")
            self.output_mode_select = epics_signal_rw(self.ModeSelect, f"{prefix}.OMSL")
            self.device_type = epics_signal_r(self.DeviceType, f"{prefix}.DTYP")
        super().__init__(prefix=prefix, name=name)
