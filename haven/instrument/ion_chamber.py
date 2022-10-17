"""Holds ion chamber detector descriptions and assignments to EPICS PVs."""

from typing import Sequence

from ophyd import (
    Device,
    status,
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
    sensitivities = [1, 2, 5, 10, 20, 50, 100, 200, 500]
    sensitivity_units = ["pA/V", "nA/V", "µA/V", "mA/V"]
    raw_counts = FCpt(SignalRO, "{prefix}.S{ch_num}")
    _sensitivity = FCpt(Signal, "{preamp_prefix}:sens_num")
    _sensitivity_unit = FCpt(Signal, "{preamp_prefix}:sens_unit")

    def __init__(self, prefix, ch_num, name, preamp_prefix=None, *args, **kwargs):
        # Set up the channel number for this scaler channel
        if ch_num < 1:
            raise ValueError(f"Scaler channels must be greater than 0: {ch_num}")
        self.ch_num = ch_num
        self.ch_char = chr(64 + ch_num)
        # Save an epics path to the preamp
        if preamp_prefix is None:
            preamp_prefix = prefix
        self.preamp_prefix = preamp_prefix
        # Initialize all the other Device stuff
        super().__init__(prefix=prefix, name=name, *args, **kwargs)

    @property
    def sensitivity(self):
        return self.sensitivities[self._sensitivity.get()]

    @property
    def sensitivity_unit(self):
        return self.sensitivity_units[self._sensitivity_unit.get()]

    def _change_sensitivity(self, step: int) -> Sequence[status.Status]:
        # Determine the new sensitivity value
        target = self._sensitivity.get() + step
        new_value = target % len(self.sensitivities)
        # Determine the new units to use (if rollover is needed)
        old_unit = self._sensitivity_unit.get()
        new_unit = old_unit + int(target / len(self.sensitivities))
        # Set the new values
        status_value = self._sensitivity.set(new_value)
        status_unit = self._sensitivity_unit.set(new_unit)
        return [status_value, status_unit]
    
    def increase_gain(self) -> Sequence[status.Status]:
        """Increase the gain (descrease the sensitivity) of the ion chamber's
        pre-amp.

        Returns
        =======
        statuses
          Ophyd status objects for the value and gain of the
          sensitivity in the pre-amp.

        """
        return self._change_sensitivity(step=-1)
    
    def decrease_gain(self) -> Sequence[status.Status]:
        """Decrease the gain (increase the sensitivity) of the ion chamber's
        pre-amp.

        Returns
        =======
        statuses
          Ophyd status objects for the value and gain of the
          sensitivity in the pre-amp.

        """
        return self._change_sensitivity(step=1)


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
