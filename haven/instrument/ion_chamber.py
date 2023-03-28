"""Holds ion chamber detector descriptions and assignments to EPICS PVs."""

from typing import Sequence
import logging

import epics
from ophyd import (
    Device,
    status,
    EpicsSignal,
    EpicsSignalRO,
    PVPositionerPC,
    PVPositioner,
    PseudoPositioner,
    PseudoSingle,
    Component as Cpt,
    FormattedComponent as FCpt,
    Kind,
)
from ophyd.ophydobj import OphydObject
from ophyd.pseudopos import pseudo_position_argument, real_position_argument

from .scaler_triggered import ScalerTriggered, ScalerSignal, ScalerSignalRO
from .instrument_registry import registry
from .._iconfig import load_config
from .. import exceptions


log = logging.getLogger(__name__)


__all__ = ["IonChamber", "load_ion_chambers"]


class SensitivityPositioner(PVPositionerPC):
    setpoint = Cpt(EpicsSignal, ".VAL", kind=(Kind.config | Kind.normal))
    readback = Cpt(EpicsSignal, ".VAL", kind=(Kind.config | Kind.normal))
    readback_string = Cpt(
        EpicsSignal, ".VAL", kind=(Kind.config | Kind.normal), string=True
    )


class SetAllPositioner(PVPositionerPC):
    setpoint = Cpt(EpicsSignal, "")
    readback = Cpt(EpicsSignal, "")


class SensitivityLevelPositioner(PseudoPositioner):
    values = [1, 2, 5, 10, 20, 50, 100, 200, 500]
    units = ["pA/V", "nA/V", "µA/V", "mA/V"]
    offset_difference = -3  # How many levels higher should the offset be

    sens_level = Cpt(PseudoSingle, limits=(0, 27),
                     labels={"ion_chamber_sensitivities",
                             "ion_chamber_gains"})

    # Sensitivity settings
    sens_unit = Cpt(
        SensitivityPositioner, ":sens_unit", kind=Kind.config, settle_time=0.1
    )
    sens_value = Cpt(
        SensitivityPositioner, ":sens_num", kind=Kind.config, settle_time=0.1
    )
    offset_unit = Cpt(
        SensitivityPositioner, ":offset_unit", kind=Kind.config, settle_time=0.1
    )
    offset_value = Cpt(
        SensitivityPositioner, ":offset_num", kind=Kind.config, settle_time=0.1
    )
    set_all = Cpt(
        SetAllPositioner,
        ":init.PROC",
        kind=Kind.omitted,
        settle_time=0.1,
        limits=(0, 1),
    )

    def _level_to_num(self, level):
        return level % len(self.values)

    def _level_to_unit(self, level):
        return int(level / len(self.values))

    @pseudo_position_argument
    def forward(self, target_gain_level):
        "Given a target energy, transform to the desired target gain level."
        new_level = target_gain_level.sens_level
        new_offset = max(new_level + self.offset_difference, 0)
        real_position = self.RealPosition(
            sens_value=self._level_to_num(new_level),
            sens_unit=self._level_to_unit(new_level),
            offset_value=self._level_to_num(new_offset),
            offset_unit=self._level_to_unit(new_offset),
            set_all=1,
        )
        return real_position

    @real_position_argument
    def inverse(self, sensitivity):
        "Given a position in mono and ID energy, transform to the target energy."
        new_gain = sensitivity.sens_value + sensitivity.sens_unit * len(self.values)
        return self.PseudoPosition(sens_level=new_gain)


# @registry.register
class IonChamber(ScalerTriggered, Device):
    """An ion chamber at a spectroscopy beamline.

    Also includes the pre-amplifier as ``.pre_amp``.

    Parameters
    ==========
    prefix
      The PV prefix of the overall scaler.
    ch_num
      The number (1-index) of the channel on the scaler. 1 is the
      timer, so your channel number should start at 2.
    name
      The bluesky-compatible name for this device.
    preamp_prefix
      The process variable prefix to the pre-amp that controls this
      ion chamber (e.g. "25idc:SR01").
    scaler_prefix
      The process variable prefix for the scaler that measures this
      ion chamber.

    Attributes
    ==========
    ch_num
      The channel number on the scaler, starting at 2 (1 is the timer).
    count
      The trigger to count scaler pulses.
    raw_counts
      The counts coming from the scaler without any correction.
    volts
      The volts produced by the pre-amp, calculated from scaler
      counts.
    exposure_time
      Positioner for setting the count time on the scaler.
    sensitivity
      The positioner for changing the pre-amp gain/sensitivity.

    """

    ch_num: int = 0
    ch_char: str
    count: OphydObject = FCpt(
        EpicsSignal, "{scaler_prefix}.CNT", trigger_value=1, kind=Kind.omitted
    )
    raw_counts: OphydObject = FCpt(ScalerSignalRO, "{prefix}.S{ch_num}", kind="hinted")
    offset: OphydObject = FCpt(ScalerSignalRO, "{prefix}_{offset_suffix}", kind=Kind.config)
    net_counts: OphydObject = FCpt(ScalerSignalRO, "{prefix}_netA.{ch_char}", kind=Kind.hinted)
    volts: OphydObject = FCpt(
        ScalerSignalRO, "{prefix}_calc{ch_num}.VAL", kind="hinted"
    )
    exposure_time: OphydObject = FCpt(EpicsSignal, "{scaler_prefix}.TP", kind="normal")
    sensitivity: OphydObject = FCpt(
        SensitivityLevelPositioner, "{preamp_prefix}", kind="config"
    )
    auto_count: OphydObject = FCpt(EpicsSignal, "{scaler_prefix}.CONT", kind="config")
    record_dark_current: OphydObject = FCpt(EpicsSignal, "{scaler_prefix}_offset_start.PROC", kind="omitted")
    record_dark_time: OphydObject = FCpt(EpicsSignal, "{scaler_prefix}_offset_time.VAL", kind="config")

    _default_read_attrs = [
        "raw_counts",
        "volts",
        "exposure_time",
        "net_counts",
    ]

    def __init__(
        self,
        prefix: str,
        ch_num: int,
        name: str,
        preamp_prefix: str = None,
        scaler_prefix: str = None,
        *args,
        **kwargs,
    ):
        # Set up the channel number for this scaler channel
        if ch_num < 1:
            raise ValueError(f"Scaler channels must be greater than 0: {ch_num}")
        self.ch_num = ch_num
        self.ch_char = self.num_to_char(ch_num)
        # Determine which prefix to use for the scaler
        if scaler_prefix is not None:
            self.scaler_prefix = scaler_prefix
        else:
            self.scaler_prefix = prefix
        # Save an epics path to the preamp
        if preamp_prefix is None:
            preamp_prefix = prefix
        self.preamp_prefix = preamp_prefix
        # Determine the offset PV since it follows weird numbering conventions
        calc_num = int((self.ch_num-1) / 4)
        calc_char = self.num_to_char(((self.ch_num-1) % 4)+1)
        self.offset_suffix = f"offset{calc_num}.{calc_char}"
        # Initialize all the other Device stuff
        super().__init__(prefix=prefix, name=name, *args, **kwargs)
        # Set signal values to stage
        self.stage_sigs[self.auto_count] = 0

    def num_to_char(self, num):
        char = chr(64 + num)
        print(num, char)
        return char

    def change_sensitivity(self, step: int) -> status.StatusBase:
        """Change the gain on the pre-amp by the given number of steps.

        Parameters
        ==========
        step
          How many levels to change the sensitivity. Positive numbers
          increase the gain, negative numbers decrease the gain.

        Returns
        =======
        status.StatusBase
          The status that will be marked complete once the sensitivity
          is changed.

        """
        new_sens_level = self.sensitivity.sens_level.readback.get() + step
        try:
            status = self.sensitivity.sens_level.set(new_sens_level)
        except ValueError as e:
            raise exceptions.GainOverflow(f"{self.name} -> {e}")
        return status

    def increase_gain(self) -> Sequence[status.StatusBase]:
        """Increase the gain (descrease the sensitivity) of the ion chamber's
        pre-amp.

        Returns
        =======
        Sequence[status.StatusBase]
          Ophyd status objects for the value and gain of the
          sensitivity in the pre-amp.

        """
        return self.change_sensitivity(-1)

    def decrease_gain(self) -> Sequence[status.StatusBase]:
        """Decrease the gain (increase the sensitivity) of the ion chamber's
        pre-amp.

        Returns
        =======
        Sequence[status.StatusBase]
          Ophyd status objects for the value and gain of the
          sensitivity in the pre-amp.

        """
        return self.change_sensitivity(1)


def load_ion_chambers(config=None):
    # Load IOC prefixes from the config file
    if config is None:
        config = load_config()
    vme_ioc = config["ion_chamber"]["scaler"]["ioc"]
    scaler_record = config["ion_chamber"]["scaler"]["record"]
    scaler_pv_prefix = f"{vme_ioc}:{scaler_record}"
    preamp_ioc = config["ion_chamber"]["preamp"]["ioc"]
    # Loop through the configuration sections and create the ion chambers
    for ch_num in config["ion_chamber"]["scaler"]["channels"]:
        # Determine ion_chamber configuration
        preamp_prefix = f"{preamp_ioc}:SR{ch_num-1:02}"
        desc_pv = f"{scaler_pv_prefix}.NM{ch_num}"
        # Only use this ion chamber if it has a name
        name = epics.caget(desc_pv)
        if name == "":
            continue
        # Create the ion chamber
        ic = IonChamber(
            prefix=scaler_pv_prefix,
            ch_num=ch_num,
            name=name,
            preamp_prefix=preamp_prefix,
            labels={"ion_chambers"},
        )
        registry.register(ic)
        log.info(f"Created ion chamber: {ic.name} ({ic.prefix}, ch {ic.ch_num})")
