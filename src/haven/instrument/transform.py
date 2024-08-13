"""
Ophyd support for the EPICS transform record


Public Structures

.. autosummary::

    ~UserTransformN
    ~UserTransformsDevice
    ~TransformRecord
"""

from collections import OrderedDict

from ophyd import Component as Cpt

# from ophyd import Device
from ophyd import DynamicDeviceComponent as DDC
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO
from ophyd import FormattedComponent as FC
from ophyd_async.core import Device
from ophyd_async.epics.signal import epics_signal_r, epics_signal_rw

CHANNEL_LETTERS_LIST = "A B C D E F G H I J K L M N O P".split()


class ScanInterval(str, Enum):
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


class AlarmStatus(str, Enum):
    NONE = ""
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
    BAD_SUB = "BAD_SUB"
    UDF = "UDF"
    DISABLE = "DISABLE"
    SIMM = "SIMM"
    READ_ACCESS = "READ_ACCESS"
    WRITE_ACCESS = "WRITE_ACCESS"


class AlarmSeverity(str, Enum):
    NO_ALARM = "NO_ALARM"
    MINOR = "MINOR"
    MAJOR = "MAJOR"
    INVALID = "INVALID"


class InvalidLinkAction(IntEnum):
    IGNORE_ERROR = 0
    DO_NOTHING = 1


class EpicsRecordDeviceCommonAll(Device):
    """
    Many of the fields common to all EPICS records.

    Some fields are not included because they are not interesting to
    an EPICS client or are already provided in other support.
    """

    # Config signals
    def __init__(self, prefix, name=""):
        with self.add_children_as_readables(Config):
            self.description = epics_signal_rw(
                str, f"{prefix}.DESC", name="description"
            )
            self.scanning_rate = epics_signal_rw(
                ScanInterval, f"{prefix}.SCAN", name="scanning_rate"
            )
            self.disable_value = epics_signal_rw(
                int, f"{prefix}.DISV", name="disable_value"
            )
            self.scan_disable_input_link_value = epics_signal_rw(
                int, f"{prefix}.DISA", name="scan_disable_input_link_value"
            )
            self.scan_disable_value_input_link = epics_signal_rw(
                str, f"{prefix}.SDIS", name="scan_disable_value_input_link"
            )
            self.forward_link = epics_signal_rw(
                str, f"{prefix}.FLNK", name="forward_link"
            )
            self.device_type = epics_signal_r(str, f"{prefix}.DTYP", name="device_type")
            self.alarm_status = epics_signal_r(
                AlarmStatus, f"{prefix}.STAT", name="alarm_status"
            )
            self.alarm_severity = epics_signal_r(
                AlarmSeverity, f"{prefix}.SEVR", name="alarm_severity"
            )
            self.new_alarm_status = epics_signal_r(
                AlarmStatus, f"{prefix}.NSTA", name="new_alarm_status"
            )
            self.new_alarm_severity = epics_signal_r(
                AlarmSeverity, f"{prefix}.NSEV", name="new_alarm_severity"
            )
            self.disable_alarm_severity = epics_signal_rw(
                AlarmSeverity, f"{prefix}.DISS", name="disable_alarm_severity"
            )
        # Other signals, not included in read
        self.processing_active = epics_signal_r(
            int, f"{prefix}.PACT", name="processing_active"
        )
        self.process_record = epics_signal_x(
            int, f"{prefix}.PROC", name="process_record"
        )
        self.trace_processing = epics_signal_rw(
            int, f"{prefix}.TPRO", name="trace_processing"
        )

        super().__init__(name=name)


class EpicsSynAppsRecordEnableMixin(Device):
    """Supports ``{PV}Enable`` feature from user databases."""

    def __init__(self, prefix, name=""):
        with self.add_children_as_readables(ConfigSignal):
            enable = epics_signal_rw(int, "Enable", name="enable")
        super().__init__(name=name)

    async def reset(self):
        """set all fields to default values"""
        await asyncio.gather(
            self.enable.set(self.enable.enum_strs[1]),  # Enable
            super().reset()
        )


#############################
# End common synApps support
#############################

class TransformRecordChannel(Device):
    """
    channel of a synApps transform record: A-P

    .. index:: Ophyd Device; synApps transformRecordChannel

    .. autosummary::

        ~reset
    """

    def __init__(self, prefix, letter, name=""):
        self._ch_letter = letter
        with self.add_children_as_readables():
            self.current_value = epics_signal_rw(
                float, "{prefix}.{letter}", name="current_value"
            )
        self.last_value = epics_signal_r(float, "{prefix}.L{letter}", name="last_value")
        self.input_pv = epics_signal_rw(str, "{prefix}.INP{letter}", name="input_pv")
        self.input_pv_valid = epics_signal_r(
            str, "{prefix}.I{letter}V", name="input_pv_valid"
        )
        self.expression_invalid = epics_signal_r(
            str, "{prefix}.C{letter}V", name="expression_invalid"
        )
        self.comment = epics_signal_rw(str, "{prefix}.CMT{letter}", name="comment")
        self.expression = epics_signal_rw(
            str, "{prefix}.CLC{letter}", name="expression"
        )
        self.output_pv = epics_signal_rw(str, "{prefix}.OUT{letter}", name="output_pv")
        self.output_pv_valid = epics_signal_r(
            str, "{prefix}.O{letter}V", name="output_pv_valid"
        )

        super().__init__(name=name)

    async def reset(self):
        """set all fields to default values"""
        await asyncio.gather(
            self.comment.set(self._ch_letter.lower())
            self.input_pv.set("")
            self.expression.set("")
            self.current_value.set(0)
            self.output_pv.set("")
        )

def _channels(channel_list):
    defn = OrderedDict()
    for chan in channel_list:
        defn[chan] = (transformRecordChannel, "", {"letter": chan})
    return defn


class TransformRecord(EpicsRecordDeviceCommonAll):
    """
    EPICS transform record support in ophyd

    .. index:: Ophyd Device; synApps TransformRecord

    .. autosummary::

        ~reset

    :see: https://htmlpreview.github.io/?https://raw.githubusercontent.com/epics-modules/calc/R3-6-1/documentation/TransformRecord.html#Fields
    """

    def __init__(self, prefix, name=""):
        with self.add_children_as_readables(CONFIG):
            self.units = epics_signal_rw(str, f"{prefix}.EGU", name="units")
            self.precision = epics_signal_rw(int, f"{prefix}.PREC", name="precision")
            self.version = epics_signal_r(float, f"{prefix}.VERS", name="version")

            self.calc_option = epics_signal_rw(
                int, f"{prefix}.COPT", name="calc_option"
            )
            self.invalid_link_action = epics_signal_r(
                InvalidLinkAction, f"{prefix}.IVLA", name="invalid_link_action"
            )
            self.input_bitmap = epics_signal_r(
                int, f"{prefix}.MAP", name="input_bitmap"
            )
        with self.add_children_as_readables(HintedSignal):
            self.sensors = DeviceVector(
                {char: TransformRecordChannel(prefix=prefix, letter=char) for char in CHANNEL_LETTERS_LIST}
            )

        super().__init__(prefix=prefix, name=name)

    async def reset(self):
        """set all fields to default values"""
        channels = self.channels.values()
        await asyncio.gather(
            self.scanning_rate.set(ScanInterval.PASSIVE),
            self.description.set(self.name),
            self.units.set(""),
            self.calc_option.set(0),
            self.precision.set(3),
            self.forward_link.set(""),
            *[ch.reset() for ch in channels],
        )
        # Restore the hinted channels
        self.add_readables(channels, HintedSignal)

  
class UserTransformN(EpicsSynAppsRecordEnableMixin, TransformRecord):
    """Single instance of the userTranN database."""


class UserTransformsDevice(Device):
    """
    EPICS synApps XXX IOC setup of userTransforms: ``$(P):userTran$(N)``

    .. index:: Ophyd Device; synApps UserTransformsDevice
    """
    def __init__(self, prefix, name=""):
        # Config attrs
        with self.add_children_as_readables(ConfigSignal):
            self.enable = epics_signal_rw(int, f"{prefix}userTranEnable", name="enable")
        # Read attrs
        with self.add_children_as_readables():
            self.transform1 = UserTransformN("userTran1", name="transform1")
            self.transform1 = UserTransformN("userTran2", name="transform2")
            self.transform1 = UserTransformN("userTran3", name="transform3")
            self.transform1 = UserTransformN("userTran4", name="transform4")
            self.transform1 = UserTransformN("userTran5", name="transform5")
            self.transform1 = UserTransformN("userTran6", name="transform6")
            self.transform1 = UserTransformN("userTran7", name="transform7")
            self.transform1 = UserTransformN("userTran8", name="transform8")
            self.transform1 = UserTransformN("userTran9", name="transform9")
            self.transform1 = UserTransformN("userTran10", name="transform10")

    def reset(self):  # lgtm [py/similar-function]
        """set all fields to default values"""
        await asyncio.gather(
            self.transform1.reset(),
            self.transform2.reset(),
            self.transform3.reset(),
            self.transform4.reset(),
            self.transform5.reset(),
            self.transform6.reset(),
            self.transform7.reset(),
            self.transform8.reset(),
            self.transform9.reset(),
            self.transform10.reset(),
        )
        self.add_readables([
            self.transform1,
            self.transform2,
            self.transform3,
            self.transform4,
            self.transform5,
            self.transform6,
            self.transform7,
            self.transform8,
            self.transform9,
            self.transform10,
        ])


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: (c) 2024, UChicago Argonne, LLC
#
# Distributed under the terms of the Argonne National Laboratory Open Source License.
#
# The full license is in the file LICENSE.txt, distributed with this software.
# -----------------------------------------------------------------------------
