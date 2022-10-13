"""Holds detector descriptions and assignments to EPICS PVs."""

from ophyd import (
    Device,
    EpicsMotor,
    Component as Cpt,
    FormattedComponent as FCpt,
    Kind,
)
from ophyd.status import DeviceStatus
from apstools.devices import SRS570_PreAmplifier

from .instrument_registry import registry
from .scaler_triggered import ScalerTriggered
from .._iconfig import load_config
from ..signal import Signal, SignalRO
from .. import exceptions


__all__ = ["IonChamber", "I0", "It", "Iref", "If"]


iconfig = load_config()

beamline_prefix = iconfig["beamline"]["pv_prefix"]
scaler_prefix = iconfig["ion_chambers"]["scaler"]["pv_prefix"]
pv_prefix = f"{beamline_prefix}:{scaler_prefix}"


@registry.register
class IonChamber(ScalerTriggered, Device):
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
    raw_counts = FCpt(SignalRO, "{prefix}.S{ch_num}")
    offset = FCpt(SignalRO, "{prefix}_offset0.{ch_char}")
    net_counts = FCpt(SignalRO, "{prefix}_netA.{ch_char}")

    def __init__(self, prefix, ch_num, *args, **kwargs):
        # Set up the channel number for this scaler channel
        if ch_num < 1:
            raise ValueError(f"Scaler channels must be greater than 0: {ch_num}")
        self.ch_num = ch_num
        self.ch_char = chr(64 + ch_num)
        # Initialize all the other Device stuff
        super().__init__(prefix=prefix, *args, **kwargs)

    def increase_gain(self):
        raise NotImplementedError
    
    def decrease_gain(self):
        raise NotImplementedError


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
