"""Holds ion chamber detector descriptions and assignments to EPICS PVs."""

from typing import Sequence, Generator, Dict
import logging
import asyncio
from collections import OrderedDict
import time
import warnings

import epics
from ophyd import (
    Device,
    status,
    Signal,
    EpicsSignal,
    EpicsSignalRO,
    PVPositionerPC,
    PVPositioner,
    PseudoPositioner,
    PseudoSingle,
    Component as Cpt,
    FormattedComponent as FCpt,
    Kind,
    flyers,
)
from ophyd.ophydobj import OphydObject
from ophyd.pseudopos import pseudo_position_argument, real_position_argument
from ophyd.mca import EpicsMCARecord
from ophyd.status import SubscriptionStatus
from apstools.devices import SRS570_PreAmplifier
from pcdsdevices.signal import MultiDerivedSignal, MultiDerivedSignalRO
from pcdsdevices.type_hints import SignalToValue, OphydDataType
import numpy as np

from .scaler_triggered import ScalerTriggered, ScalerSignal, ScalerSignalRO
from .instrument_registry import registry
from .epics import caget
from .device import await_for_connection, aload_devices
from .._iconfig import load_config
from .. import exceptions


log = logging.getLogger(__name__)


__all__ = ["IonChamber", "load_ion_chambers"]



class IonChamberPreAmplifier(SRS570_PreAmplifier):
    """An SRS-570 pre-amplifier driven by an ion chamber.

    Has extra signals for walking up and down the sensitivity
    range. By setting the *sensitivity_level* signal, the offset is
    also set to be 10% of the sensitivity.

    The signal *sensitivity_tweak* can also be used to move by a given
    number of sensitivity levels, e.g. if currently at 50 µA/V,
    setting ``sensitivity_tweak.set(-2)`` would go to 10 µA/V.

    """
    values = ["1", "2", "5", "10", "20", "50", "100", "200", "500"]
    units = ["pA/V", "nA/V", "uA/V", "mA/V"]
    offset_difference = -3  # How many levels higher should the offset be

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sensitivity_tweak.subscribe(self.tweak_sensitivity, run=False)

    def tweak_sensitivity(self, *args, obj: OphydObject, value: int, **kwargs):
        new_level = self.sensitivity_level.get() + value
        self.sensitivity_level.put(new_level)

    def _level_to_value(self, level):
        return self.values[level % len(self.values)]

    def _level_to_unit(self, level):
        return self.units[int(level / len(self.values))]
    
    def _get_sensitivity_level(self, mds: MultiDerivedSignal, items: SignalToValue) -> int:
        "Given a sensitivity value and unit , transform to the desired level."
        value = items[self.sensitivity_value]
        unit = items[self.sensitivity_unit]
        new_gain =  self.values.index(value) + self.units.index(unit) * len(self.values)        
        return new_gain
        
    def _put_sensitivity_level(self, mds: MultiDerivedSignal, value: OphydDataType) -> SignalToValue:
        "Given a sensitivity level, transform to the desired value and unit."
        # Determine new values
        new_level = value
        new_offset = max(new_level + self.offset_difference, 0)
        # Check for out of bounds
        lmin, lmax = (0, 27)
        msg = f"Cannot set {self.name} outside range ({lmin}, {lmax}), received {new_level}."
        if new_level < lmin:
            new_level = lmin
            warnings.warn(msg)
        elif new_level > lmax:
            new_level = lmax
            warnings.warn(msg)
        # Return calculated gain and offset
        result = {
            self.sensitivity_value: self._level_to_value(new_level),
            self.sensitivity_unit: self._level_to_unit(new_level),
            self.offset_value: self._level_to_value(new_offset),
            self.offset_unit: self._level_to_unit(new_offset),
            # set_all=1,
        }
        return result

    sensitivity_level = Cpt(
        MultiDerivedSignal,
        attrs=["sensitivity_value", "sensitivity_unit"],
        calculate_on_get=_get_sensitivity_level,
        calculate_on_put=_put_sensitivity_level,
        kind=Kind.omitted,
    )

    sensitivity_tweak = Cpt(
        Signal,
        kind=Kind.omitted,
    )


# @registry.register
class IonChamber(ScalerTriggered, Device, flyers.FlyerInterface):
    """An ion chamber at a spectroscopy beamline.

    Also includes the pre-amplifier as ``.pre_amp``.

    This class also implements the bluesky/ophyd flyer
    interface. During *kickoff()*, previous data are erased and
    acquisition is started as a multi-channel scaler. It also watches
    for changes in the number of data collected and collects
    timestamps each time a new datum is captured. *complete()* stops
    acquisition. These timestamps, along with the measured data, are
    generated during *collect()*.

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

    stream_name: str = "primary"
    ch_num: int = 0
    ch_char: str
    start_timestamp: float = None
    count: OphydObject = FCpt(
        EpicsSignal, "{scaler_prefix}:scaler1.CNT", trigger_value=1, kind=Kind.omitted
    )
    description: OphydObject = FCpt(
        EpicsSignalRO, "{scaler_prefix}:scaler1.NM{ch_num}", kind=Kind.config
    )
    # Signal chain devices
    preamp = FCpt(IonChamberPreAmplifier, "{preamp_prefix}")
    # Old Scaler mode support
    clock: OphydObject = FCpt(
        EpicsSignal,
        "{scaler_prefix}:scaler1.FREQ",
        kind=Kind.config,
    )
    raw_counts: OphydObject = FCpt(
        ScalerSignalRO, "{scaler_prefix}:scaler1.S{ch_num}", kind=Kind.normal
    )
    offset: OphydObject = FCpt(
        ScalerSignalRO, "{scaler_prefix}:scaler1_{offset_suffix}", kind=Kind.config
    )
    net_counts: OphydObject = FCpt(
        ScalerSignalRO, "{scaler_prefix}:scaler1_netA.{ch_char}", kind=Kind.hinted
    )
    volts: OphydObject = FCpt(
        ScalerSignalRO, "{scaler_prefix}:scaler1_calc{ch_num}.VAL", kind=Kind.normal
    )
    exposure_time: OphydObject = FCpt(
        EpicsSignal, "{scaler_prefix}:scaler1.TP", kind=Kind.normal
    )
    auto_count: OphydObject = FCpt(
        EpicsSignal, "{scaler_prefix}:scaler1.CONT", kind=Kind.omitted
    )
    record_dark_current: OphydObject = FCpt(
        EpicsSignal, "{scaler_prefix}:scaler1_offset_start.PROC", kind=Kind.omitted
    )
    record_dark_time: OphydObject = FCpt(
        EpicsSignal, "{scaler_prefix}:scaler1_offset_time.VAL", kind=Kind.config
    )
    # Multi-channel scaler support
    start_all: OphydObject = FCpt(
        EpicsSignal, "{scaler_prefix}:StartAll", kind=Kind.omitted
    )
    stop_all: OphydObject = FCpt(
        EpicsSignal, "{scaler_prefix}:StopAll", kind=Kind.omitted
    )
    erase_all: OphydObject = FCpt(
        EpicsSignal, "{scaler_prefix}:EraseAll", kind=Kind.omitted
    )
    erase_start: OphydObject = FCpt(
        EpicsSignal,
        "{scaler_prefix}:EraseStart",
        kind=Kind.omitted,
    )
    acquiring: OphydObject = FCpt(
        EpicsSignal, "{scaler_prefix}:Acquiring", kind=Kind.omitted
    )
    channel_advance_source: OphydObject = FCpt(
        EpicsSignal,
        "{scaler_prefix}:ChannelAdvance",
        kind=Kind.config,
    )
    num_channels_to_use: OphydObject = FCpt(
        EpicsSignal,
        "{scaler_prefix}:NuseAll",
        kind=Kind.config,
    )
    max_channels: OphydObject = FCpt(
        EpicsSignal, "{scaler_prefix}:MaxChannels", kind=Kind.config
    )
    current_channel: OphydObject = FCpt(
        EpicsSignal,
        "{scaler_prefix}:CurrentChannel",
        kind=Kind.normal,
    )
    channel_one_source: OphydObject = FCpt(
        EpicsSignal, "{scaler_prefix}:Channel1Source", kind=Kind.config
    )
    count_on_start: OphydObject = FCpt(
        EpicsSignal, "{scaler_prefix}:CountOnStart", kind=Kind.config
    )
    mca: OphydObject = FCpt(
        EpicsMCARecord, "{scaler_prefix}:mca{ch_num}", kind=Kind.omitted
    )
    mca_times: OphydObject = FCpt(
        EpicsMCARecord, "{scaler_prefix}:mca1", kind=Kind.omitted
    )

    # Virtual signals to handle fly-scanning
    timestamps: list = []
    num_bins = Cpt(Signal)

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
        calc_num = int((self.ch_num - 1) / 4)
        calc_char = self.num_to_char(((self.ch_num - 1) % 4) + 1)
        self.offset_suffix = f"offset{calc_num}.{calc_char}"
        # Initialize all the other Device stuff
        super().__init__(prefix=prefix, name=name, *args, **kwargs)
        # Set signal values to stage
        self.stage_sigs[self.auto_count] = 0

    def num_to_char(self, num):
        char = chr(64 + num)
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

    def increase_gain(self) -> status.StatusBase:
        """Increase the gain (descrease the sensitivity) of the ion chamber's
        pre-amp.

        Returns
        =======
        status.StatusBase
          Ophyd status object for the value and gain of the
          sensitivity in the pre-amp.

        """
        return self.change_sensitivity(-1)

    def decrease_gain(self) -> status.StatusBase:
        """Decrease the gain (increase the sensitivity) of the ion chamber's
        pre-amp.

        Returns
        =======
        status.StatusBase
          Ophyd status object for the value and gain of the
          sensitivity in the pre-amp.

        """
        return self.change_sensitivity(1)

    def record_timestamp(self, *, old_value, value, timestamp, **kwargs):
        self.timestamps.append(timestamp)

    def kickoff(self) -> status.StatusBase:
        def check_acquiring(*, old_value, value, **kwargs):
            is_acquiring = bool(value)
            if is_acquiring:
                self.start_timestamp = time.time()
            return is_acquiring

        self.start_timestamp = None
        # Set some configuration PVs on the MCS
        self.count_on_start.set(1).wait()
        # Start acquiring data
        self.erase_start.set(1).wait()
        # Wait for the "Acquiring" to start
        status = SubscriptionStatus(self.acquiring, check_acquiring)
        # Watch for new data being collected so we can save timestamps
        self.timestamps = []
        self.current_channel.subscribe(self.record_timestamp)
        return status

    def complete(self) -> status.StatusBase:
        status = self.stop_all.set(1, settle_time=0.05)
        return status

    def collect(self) -> Generator[Dict, None, None]:
        net_counts_name = self.net_counts.name
        # Use the scaler's clock counter to calculate timestamps
        times = self.mca_times.spectrum.get()
        times = np.divide(times, self.clock.get(), casting="safe")
        times = np.cumsum(times)
        pso_timestamps = times + self.start_timestamp
        # Retrieve data, except for first point (during taxiing)
        data = self.mca.spectrum.get()[1:]
        # Convert timestamps from PSO pulses to pixels
        pixel_timestamps = (pso_timestamps[1:] + pso_timestamps[:-1]) / 2
        # Create data events
        for ts, value in zip(pixel_timestamps, data):
            yield {
                "data": {net_counts_name: value},
                "timestamps": {net_counts_name: ts},
                "time": ts,
            }

    def describe_collect(self) -> Dict[str, Dict]:
        """Describe details for the flyer collect() method"""
        desc = OrderedDict()
        desc.update(self.net_counts.describe())
        return {self.name: desc}


async def make_ion_chamber_device(
    prefix: str, ch_num: int, name: str, preamp_prefix: str
):
    ic = IonChamber(
        prefix=prefix,
        ch_num=ch_num,
        name=name,
        preamp_prefix=preamp_prefix,
        labels={"ion_chambers"},
    )
    try:
        await await_for_connection(ic)
    except TimeoutError as exc:
        raise
        log.warning(
            f"Could not connect to ion chamber: {name} ({prefix}, {preamp_prefix})"
        )
    else:
        log.info(f"Created ion chamber: {name} ({prefix}, {preamp_prefix})")
        registry.register(ic)
        return ic


async def load_ion_chamber(preamp_prefix: str, scaler_prefix: str, ch_num: int):
    # Determine ion_chamber configuration
    preamp_prefix = f"{preamp_prefix}:SR{ch_num-1:02}"
    desc_pv = f"{scaler_prefix}:scaler1.NM{ch_num}"
    # Only use this ion chamber if it has a name
    try:
        name = await caget(desc_pv)
    except asyncio.exceptions.TimeoutError:
        # Scaler channel is unreachable, so skip it
        log.warning(f"Could not connect to ion_chamber: {desc_pv}")
        return
    if name == "":
        log.info(f"Skipping unnamed ion chamber: {desc_pv}")
        return
    # Create the ion chamber device
    return await make_ion_chamber_device(
        prefix=scaler_prefix,
        ch_num=ch_num,
        name=name,
        preamp_prefix=preamp_prefix,
    )


def load_ion_chamber_coros(config=None):
    # Load IOC prefixes from the config file
    if config is None:
        config = load_config()
    # vme_ioc = config["ion_chamber"]["scaler"]["ioc"]
    # scaler_record = config["ion_chamber"]["scaler"]["record"]
    scaler_prefix = config["ion_chamber"]["scaler"]["prefix"]
    preamp_prefix = config["ion_chamber"]["preamp"]["prefix"]
    ion_chambers = []
    # Loop through the configuration sections and create ion chambers co-routines
    for ch_num in config["ion_chamber"]["scaler"]["channels"]:
        yield load_ion_chamber(
            preamp_prefix=preamp_prefix, scaler_prefix=scaler_prefix, ch_num=ch_num
        )


def load_ion_chambers(config=None):
    return asyncio.run(aload_devices(*load_ion_chamber_coros(config=config)))
