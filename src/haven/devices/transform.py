"""Ophyd support for the EPICS transform record."""

import asyncio

# from ophyd import Device
from ophyd_async.core import (
    Device,
    StandardReadable,
    StandardReadableFormat,
    StrictEnum,
    SubsetEnum,
)
from ophyd_async.epics.core import epics_signal_r, epics_signal_rw

from .synApps import EpicsRecordDeviceCommonAll, EpicsSynAppsRecordEnableMixin

CHANNEL_LETTERS_LIST = "A B C D E F G H I J K L M N O P".split()


#############################
# End common synApps support
#############################


class TransformRecordChannel(StandardReadable):
    """
    channel of a synApps transform record: A-P

    .. index:: Ophyd Device; synApps transformRecordChannel

    .. autosummary::

        ~reset
    """

    class PVValidity(SubsetEnum):
        EXT_PV_NC = "Ext PV NC"
        EXT_PV_OK = "Ext PV OK"
        LOCAL_PV = "Local PV"
        CONSTANT = "Constant"

    def __init__(self, prefix, letter, name=""):
        self._ch_letter = letter
        with self.add_children_as_readables():
            self.current_value = epics_signal_rw(float, f"{prefix}.{letter}")
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.input_pv = epics_signal_rw(str, f"{prefix}.INP{letter}")
            self.comment = epics_signal_rw(str, f"{prefix}.CMT{letter}")
            self.expression = epics_signal_rw(
                str,
                f"{prefix}.CLC{letter}",
            )
        self.output_pv = epics_signal_rw(str, f"{prefix}.OUT{letter}")
        self.last_value = epics_signal_r(float, f"{prefix}.L{letter}")
        self.input_pv_valid = epics_signal_r(self.PVValidity, f"{prefix}.I{letter}V")
        self.expression_invalid = epics_signal_r(int, f"{prefix}.C{letter}V")
        self.output_pv_valid = epics_signal_r(
            self.PVValidity,
            f"{prefix}.O{letter}V",
        )

        super().__init__(name=name)

    async def reset(self):
        """set all fields to default values"""
        await asyncio.gather(
            self.comment.set(self._ch_letter.lower()),
            self.input_pv.set(""),
            self.expression.set(""),
            self.current_value.set(0),
            self.output_pv.set(""),
        )


class TransformRecord(EpicsRecordDeviceCommonAll):
    """
    EPICS transform record support in ophyd

    .. index:: Ophyd Device; synApps TransformRecord

    .. autosummary::

        ~reset

    :see: https://htmlpreview.github.io/?https://raw.githubusercontent.com/epics-modules/calc/R3-6-1/documentation/TransformRecord.html#Fields
    """

    class CalcOption(StrictEnum):
        CONDITIONAL = "Conditional"
        ALWAYS = "Always"

    class InvalidLinkAction(SubsetEnum):
        IGNORE_ERROR = "Ignore error"
        DO_NOTHING = "Do Nothing"

    def __init__(self, prefix, name=""):
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.units = epics_signal_rw(
                str,
                f"{prefix}.EGU",
            )
            self.precision = epics_signal_rw(int, f"{prefix}.PREC")
            self.version = epics_signal_r(
                float,
                f"{prefix}.VERS",
            )

            self.calc_option = epics_signal_rw(
                self.CalcOption,
                f"{prefix}.COPT",
            )
            self.invalid_link_action = epics_signal_r(
                self.InvalidLinkAction,
                f"{prefix}.IVLA",
            )
            self.input_bitmap = epics_signal_r(
                int, f"{prefix}.MAP", name="input_bitmap"
            )
        with self.add_children_as_readables():
            for letter in CHANNEL_LETTERS_LIST:
                setattr(
                    self,
                    f"channel_{letter}",
                    TransformRecordChannel(prefix=prefix, letter=letter),
                )

        super().__init__(prefix=prefix, name=name)

    async def reset(self):
        """set all fields to default values"""
        channels = [getattr(self, letter) for letter in CHANNEL_LETTERS_LIST]
        await asyncio.gather(
            self.scanning_rate.set(self.ScanInterval.PASSIVE),
            self.description.set(self.name),
            self.units.set(""),
            self.calc_option.set(0),
            self.precision.set(3),
            self.forward_link.set(""),
            *[ch.reset() for ch in channels],
        )
        # Restore the hinted channels
        self.add_readables(channels, StandardReadableFormat.HINTED_SIGNAL)


class UserTransformN(EpicsSynAppsRecordEnableMixin, TransformRecord):
    """Single instance of the userTranN database."""


class UserTransformsDevice(Device):
    """
    EPICS synApps XXX IOC setup of userTransforms: ``$(P):userTran$(N)``

    .. index:: Ophyd Device; synApps UserTransformsDevice
    """

    def __init__(self, prefix, name=""):
        # Config attrs
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.enable = epics_signal_rw(int, f"{prefix}userTranEnable", name="enable")
        # Read attrs
        with self.add_children_as_readables():
            self.transform1 = UserTransformN("userTran1")
            self.transform1 = UserTransformN("userTran2")
            self.transform1 = UserTransformN("userTran3")
            self.transform1 = UserTransformN("userTran4")
            self.transform1 = UserTransformN("userTran5")
            self.transform1 = UserTransformN("userTran6")
            self.transform1 = UserTransformN("userTran7")
            self.transform1 = UserTransformN("userTran8")
            self.transform1 = UserTransformN("userTran9")
            self.transform1 = UserTransformN("userTran10")

    async def reset(self):  # lgtm [py/similar-function]
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
        self.add_readables(
            [
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
            ]
        )


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: (c) 2024, UChicago Argonne, LLC
#
# Distributed under the terms of the Argonne National Laboratory Open Source License.
#
# The full license is in the file LICENSE.txt, distributed with this software.
# -----------------------------------------------------------------------------
