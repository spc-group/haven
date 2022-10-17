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
# from ..signal import Signal, SignalRO
from ophyd import EpicsSignal as Signal, EpicsSignalRO as SignalRO
from .. import exceptions


__all__ = ["IonChamber", "I0", "It", "Iref", "If"]


iconfig = load_config()

ioc_prefix = iconfig["ion_chambers"]["scaler"]["ioc"]
record_prefix = iconfig["ion_chambers"]["scaler"]["record"]
pv_prefix = f"{ioc_prefix}:{record_prefix}"


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


@registry.register
class IonChamberWithOffset(IonChamber):
    offset = FCpt(SignalRO, "{prefix}_offset0.{ch_char}")
    net_counts = FCpt(SignalRO, "{prefix}_netA.{ch_char}")


for name, config in load_config()["ion_chambers"].items():
    # Define ion chambers
    if name != "scaler":
        IonChamber(
            prefix=pv_prefix,
            ch_num=config["scaler_channel"],
            name=name,
            labels={"ion_chambers"},
        )
