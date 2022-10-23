"""Holds ion chamber detector descriptions and assignments to EPICS PVs."""

from typing import Sequence
import logging
import math

from ophyd import (
    Device,
    status,
    EpicsMotor,
    EpicsSignal,
    PVPositionerPC,
    PseudoPositioner,
    PseudoSingle,
    Component as Cpt,
    FormattedComponent as FCpt,
    Kind,
)
from ophyd.pseudopos import pseudo_position_argument, real_position_argument
from ophyd.status import DeviceStatus
from apstools.devices import SRS570_PreAmplifier

from .instrument_registry import registry
from .scaler_triggered import ScalerTriggered
from .._iconfig import load_config

# from ..signal import Signal, SignalRO
from ophyd import EpicsSignal as Signal, EpicsSignalRO as SignalRO
from .. import exceptions


log = logging.getLogger(__name__)


__all__ = ["IonChamber", "I0", "It", "Iref", "If"]


iconfig = load_config()

ioc_prefix = iconfig["ion_chamber"]["scaler"]["ioc"]
record_prefix = iconfig["ion_chamber"]["scaler"]["record"]
pv_prefix = f"{ioc_prefix}:{record_prefix}"


class SensitivityPositioner(PVPositionerPC):
    setpoint = Cpt(EpicsSignal, ".VAL")
    readback = Cpt(EpicsSignal, ".VAL")


class SensitivityLevelPositioner(PseudoPositioner):
    values = [1, 2, 5, 10, 20, 50, 100, 200, 500]
    units = ["pA/V", "nA/V", "µA/V", "mA/V"]

    sens_level = Cpt(PseudoSingle, limits=(0, 27))

    # Sensitivity settings
    sens_value = Cpt(SensitivityPositioner, ":sens_num")
    sens_unit = Cpt(SensitivityPositioner, ":sens_unit")

    @pseudo_position_argument
    def forward(self, target_gain_level):
        "Given a target energy, transform to the mono and ID energies."
        new_level = target_gain_level.sens_level
        new_value = new_level % len(self.values)
        new_unit = int(new_level / len(self.values))
        return self.RealPosition(
            sens_value=new_value,
            sens_unit=new_unit,
        )

    @real_position_argument
    def inverse(self, sensitivity):
        "Given a position in mono and ID energy, transform to the target energy."
        new_gain = sensitivity.sens_value + sensitivity.sens_unit * len(self.values)
        return self.PseudoPosition(sens_level=new_gain)


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
    sensitivity = FCpt(SensitivityLevelPositioner, "{preamp_prefix}", kind="config")
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

    # @property
    # def sensitivity(self):
    #     return self.gain_level.sensitivities[self.gain_level.sensitivity.get()]

    # @property
    # def sensitivity_unit(self):
    #     return self.sensitivity.unit[self.sensitivity.unit.get()]

    # def _change_sensitivity(self, step: int) -> Sequence[status.Status]:
    #     # Determine the new sensitivity value
    #     target = self._sensitivity.get() + step
    #     new_value = target % len(self.sensitivities)
    #     # Determine the new units to use (if rollover is needed)
    #     old_unit = self._sensitivity_unit.get()
    #     new_unit = old_unit + math.floor(target / len(self.sensitivities))
    #     # Check that the new values are not off the end of the chart
    #     value_too_low = new_unit < 0
    #     max_unit = len(self.sensitivity_units) - 1
    #     value_too_high = (
    #         new_unit == max_unit
    #     ) and new_value > 0  # 1 mA/V is as high as it goes
    #     if value_too_low or value_too_high:
    #         raise exceptions.GainOverflow(self)
    #     # Set the new values
    #     status_value = self._sensitivity.set(new_value, timeout=1)
    #     status_unit = self._sensitivity_unit.set(new_unit, timeout=1)
    #     log.info(f"Setting new gain for {self._sensitivity}: {new_value}")
    #     log.info(f"Setting new gain unit for {self._sensitivity_unit}: {new_unit}")
    #     return [status_value, status_unit]

    def change_sensitivity(self, step) -> status.Status:
        new_sens_level = self.sensitivity.sens_level.readback.get() + step
        try:
            status = self.sensitivity.sens_level.set(new_sens_level)
        except ValueError:
            raise exceptions.GainOverflow(self)
        return status

    def increase_gain(self) -> Sequence[status.Status]:
        """Increase the gain (descrease the sensitivity) of the ion chamber's
        pre-amp.

        Returns
        =======
        statuses
          Ophyd status objects for the value and gain of the
          sensitivity in the pre-amp.

        """
        return self.change_sensitivity(-1)
        # new_gain = self.gain_level.gain_level.get().readback - 1
        # return self.gain_level.gain_level.set(new_gain)

    def decrease_gain(self) -> Sequence[status.Status]:
        """Decrease the gain (increase the sensitivity) of the ion chamber's
        pre-amp.

        Returns
        =======
        statuses
          Ophyd status objects for the value and gain of the
          sensitivity in the pre-amp.

        """
        return self.change_sensitivity(1)
        # new_gain = self.gain_level.gain_level.get().readback + 1
        # return self.gain_level.gain_level.set(new_gain)


@registry.register
class IonChamberWithOffset(IonChamber):
    offset = FCpt(SignalRO, "{prefix}_offset0.{ch_char}")
    net_counts = FCpt(SignalRO, "{prefix}_netA.{ch_char}")


conf = load_config()
preamp_ioc = conf["ion_chamber"]["preamp"]["ioc"]
for name, config in conf["ion_chamber"].items():
    # Define ion chambers
    if name not in ["scaler", "preamp"]:
        preamp_prefix = f"{preamp_ioc}:{config['preamp_record']}"
        ic = IonChamber(
            prefix=pv_prefix,
            ch_num=config["scaler_channel"],
            name=name,
            preamp_prefix=preamp_prefix,
            labels={"ion_chamber"},
        )
        log.info(f"Created ion chamber: {ic}")
