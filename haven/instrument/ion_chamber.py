"""Holds detector descriptions and assignments to EPICS PVs."""

from ophyd import (
    Device,
    EpicsMotor,
    EpicsSignal,
    EpicsSignalRO,
    Component as Cpt,
    FormattedComponent as FCpt,
    Kind,
)
from ophyd.status import DeviceStatus
from ophyd.scaler import ScalerCH
from apstools.devices import SRS570_PreAmplifier

from .instrument_registry import registry
from .._iconfig import load_config


__all__ = ["IonChamber", "I0", "It", "Iref", "If"]


iconfig = load_config()

beamline_prefix = iconfig["beamline"]["pv_prefix"]
scaler_prefix = iconfig["ion_chambers"]["scaler"]["pv_prefix"]
pv_prefix = f"{beamline_prefix}:{scaler_prefix}"


@registry.register
class IonChamber(Device):
    """An ion chamber at a spectroscopy beamline.

    Also includes the pre-amplifier as ``.pre_amp``.

    Attributes
    ==========

    prefix
      The PV prefix of the overall scaler.
    scaler_ch
      The number (1-index) of the channel on the scaler. 1 is the
      timer, so your channel number should start at 2.

    """

    ch_num: int = 0
    raw_counts = FCpt(EpicsSignalRO, "{prefix}.S{ch_num}")
    offset = FCpt(EpicsSignalRO, "{prefix}_offset0.{ch_char}")
    net_counts = FCpt(EpicsSignalRO, "{prefix}_netA.{ch_char}")
    count = Cpt(EpicsSignal, ".CNT", trigger_value=1, kind=Kind.omitted)
    _statuses = {}

    def __init__(self, prefix, ch_num, *args, **kwargs):
        if ch_num < 1:
            raise ValueError(f"Scaler channels must be greater than 0: {ch_num}")
        self.ch_num = ch_num
        self.ch_char = chr(64 + ch_num)
        # Initialize all the other Device stuff
        super().__init__(prefix, *args, **kwargs)

    def trigger(self, *args, **kwargs):
        # Figure out if there's already a trigger active
        previous_status = self._statuses.get(self.prefix)
        is_idle = previous_status is None or previous_status.done
        # Trigger the detector if not already running, and update the status dict
        if is_idle:
            new_status = super().trigger(*args, **kwargs)
            self._statuses[self.prefix] = new_status
        else:
            new_status = previous_status
        return new_status


I0 = IonChamber(
    pv_prefix,
    ch_num=2,
    name="I0",
    labels={
        "ion_chamber",
    },
)


It = IonChamber(
    pv_prefix,
    ch_num=3,
    name="It",
    labels={
        "ion_chamber",
    },
)


Iref = IonChamber(
    pv_prefix,
    ch_num=4,
    name="Iref",
    labels={
        "ion_chamber",
    },
)


If = IonChamber(
    pv_prefix,
    ch_num=5,
    name="If",
    labels={
        "ion_chamber",
    },
)
