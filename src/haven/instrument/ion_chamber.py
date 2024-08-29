"""Holds ion chamber detector descriptions and assignments to EPICS PVs."""

import asyncio
import logging
import math
import time
import warnings
from collections import OrderedDict
from numbers import Number
from typing import Dict, Generator, Mapping, Optional

import numpy as np
from apstools.utils.misc import safe_ophyd_name
from bluesky.protocols import Triggerable
from ophyd import Component as Cpt
from ophyd import EpicsSignal, EpicsSignalRO
from ophyd import FormattedComponent as FCpt
from ophyd import Kind, Signal, flyers, status
from ophyd.mca import EpicsMCARecord
from ophyd.ophydobj import OphydObject
from ophyd.signal import DerivedSignal, InternalSignal
from ophyd.status import SubscriptionStatus
from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    AsyncStatus,
    ConfigSignal,
    Device,
    DeviceVector,
    HintedSignal,
    StandardReadable,
    TriggerInfo,
    observe_value,
)
from ophyd_async.epics.signal import epics_signal_r, epics_signal_rw
from pcdsdevices.signal import MultiDerivedSignal, MultiDerivedSignalRO
from pcdsdevices.type_hints import OphydDataType, SignalToValue

from .. import exceptions
from .._iconfig import load_config
from .device import (
    await_for_connection,
    connect_devices,
    make_device,
    resolve_device_names,
)
from .instrument_registry import InstrumentRegistry
from .instrument_registry import registry as default_registry
from .labjack import AnalogInput, LabJackT7
from .scaler import CountState, MultiChannelScaler
from .signal import derived_signal_r
from .srs570 import SRS570PreAmplifier

log = logging.getLogger(__name__)


__all__ = ["IonChamber", "load_ion_chambers"]


class IonChamber(StandardReadable, Triggerable):
    """A high-level abstraction of an ion chamber.

    Parameters
    ==========
    auto_name
      If true, or None when no name was provided, the name for
      this motor will be set based on the motor's *description*
      field.


    Sub-Devices
    ===========
    mcs
      A multi-channel scaler pointed to be *scaler_prefix*. This
      device will have two channels, the clock channel (#0) and the
      data channel, determined by *scaler_channel*.

    """

    _ophyd_labels_ = {"ion_chambers", "detectors"}
    _trigger_statuses = {}

    def __init__(
        self,
        scaler_prefix: str,
        scaler_channel: int,
        preamp_prefix: str,
        voltmeter_prefix: str,
        voltmeter_channel: int,
        counts_per_volt_second: float,
        name="",
        auto_name: bool = None,
    ):
        self.counts_per_volt_second = counts_per_volt_second
        self.scaler_prefix = scaler_prefix
        self._scaler_channel = scaler_channel
        self._voltmeter_channel = voltmeter_channel
        self.auto_name = auto_name
        with self.add_children_as_readables():
            self.mcs = MultiChannelScaler(
                prefix=scaler_prefix, channels=[0, scaler_channel]
            )
            self.preamp = SRS570PreAmplifier(preamp_prefix)
            self.voltmeter = LabJackT7(
                prefix=voltmeter_prefix, analog_inputs=[voltmeter_channel], digital_ios=[], analog_outputs=[], digital_words=[],
            )
            self.voltage = derived_signal_r(
                float,
                name="voltage",
                units="volt",
                derived_from={
                    "count": self.scaler_channel.net_count,
                    "time": self.mcs.scaler.elapsed_time,
                },
                inverse=self._counts_to_volts,
            )
            self.current = derived_signal_r(
                float,
                name="current",
                units="ampere",
                derived_from={"voltage": self.voltage, "gain": self.preamp.gain},
                inverse=self._volts_to_amps,
            )
        super().__init__(name=name)

    def _counts_to_volts(self, values, *, count, time):
        """Pre-amp output voltage calculated from scaler counts."""
        return values[count] / self.counts_per_volt_second / values[time]

    def _volts_to_amps(self, values, *, voltage, gain):
        """Pre-amp current calculated from output voltage."""
        return values[voltage] / values[gain]

    def __repr__(self):
        return f"<{type(self).__name__}: '{self.name}' ({self.scaler_channel.raw_count.source})>"

    @property
    def scaler_channel(self):
        return self.mcs.scaler.channels[self._scaler_channel]

    @property
    def voltmeter_channel(self):
        return self.voltmeter.analog_inputs[self._voltmeter_channel]

    @property
    def mca(self):
        return self.mcs.mcas[self._scaler_channel]

    async def connect(
        self,
        mock: bool = False,
        timeout: float = DEFAULT_TIMEOUT,
        force_reconnect: bool = False,
    ):
        """Connect self and all child Devices.

        Contains a timeout that gets propagated to child.connect methods.

        Parameters
        ----------
        mock:
            If True then use ``MockSignalBackend`` for all Signals
        timeout:
            Time to wait before failing with a TimeoutError.

        """
        await super().connect(
            mock=mock, timeout=timeout, force_reconnect=force_reconnect
        )
        # Update the device's name
        auto_name = bool(self.auto_name) or (self.auto_name is None and self.name == "")
        if bool(auto_name):
            try:
                desc = await self.scaler_channel.description.get_value()
            except Exception as exc:
                warnings.warn(
                    f"Could not read description for {self}. Name not updated. {exc}"
                )
                return
            # Only update the name if the description has been set
            if desc != "":
                self.set_name(safe_ophyd_name(desc))
                # Update the labjack's input's .DESC field to match the scaler channel
                print(desc)
                await self.voltmeter_channel.description.set(desc)

    @AsyncStatus.wrap
    async def trigger(self, record_dark_current=False):
        """Instruct the ion chamber's scaler to capture one data point.

        Parameters
        ==========
        record_dark_current
          If true, this measurement will be saved as the dark current
          reading.

        """
        # Recording the dark current is done differently
        if record_dark_current:
            await self.record_dark_current()
            return
        # Check if we've seen this signal before
        signal = self.mcs.scaler.count
        last_status = self._trigger_statuses.get(signal.source)
        # Previous trigger is still going, so wait for that instead
        if last_status is not None and not last_status.done:
            await last_status
            return
        # Nothing to wait on yet, so trigger the scaler and stash the result
        status = signal.set(CountState.COUNT)
        self._trigger_statuses[signal.source] = status
        await status

    async def record_dark_current(self):
        signal = self.mcs.scaler.record_dark_current
        await signal.trigger(wait=False)
        # Now wait for the count state to return to done
        integration_time = await self.mcs.scaler.dark_current_time.get_value()
        timeout = integration_time + DEFAULT_TIMEOUT
        count_signal = self.mcs.scaler.count
        done = asyncio.Event()
        done_status = AsyncStatus(asyncio.wait_for(done.wait(), timeout=timeout))
        async for state in observe_value(count_signal, done_status=done_status):
            if state == CountState.DONE:
                done.set()
                break

    def record_fly_reading(self, reading, **kwargs):
        if self._is_flying:
            self._fly_readings.append(reading)

    @AsyncStatus.wrap
    async def prepare(self, value: TriggerInfo):
        """Prepare the ion chamber for fly scanning."""
        self.start_timestamp = None
        # Set some configuration PVs on the MCS
        await asyncio.gather(
            self.mcs.count_on_start.set(1),
            self.mcs.channel_advance_source.set(self.mcs.ChannelAdvanceSource.INTERNAL),
            self.mcs.num_channels.set(await self.mcs.num_channels_max.get_value()),
            self.mcs.dwell_time.set(value.livetime),
            self.mcs.erase_all.trigger(),
        )
        # Start acquiring data
        self._fly_readings = []
        self._is_flying = False  # Gets set during kickoff

    def kickoff(self) -> AsyncStatus:
        """Start recording data for the fly scan."""
        # Watch for new data being collected so we can save timestamps
        self.mcs.current_channel.subscribe(self.record_fly_reading)
        # Start acquiring
        self._is_flying = True
        return self.mcs.start_all.trigger()

    @AsyncStatus.wrap
    async def complete(self):
        """Finish detector fly-scan acquisition."""
        await self.mcs.stop_all.trigger()
        self._is_flying = False

    async def collect(self):
        # Prepare the individual signal data-sets
        timestamps = [
            d[self.mcs.current_channel.name]["timestamp"] for d in self._fly_readings
        ]
        num_points = len(timestamps)
        raw_counts = (await self.mca.spectrum.get_value())[:num_points]
        raw_times = await self.mcs.mcas[0].spectrum.get_value()
        clock_freq = await self.mcs.scaler.clock_frequency.get_value()
        times = raw_times / clock_freq
        # Apply the dark current correction
        offset_rate = await self.scaler_channel.offset_rate.get_value()
        net_counts = raw_counts - offset_rate * times
        # Build the results dictionary to be sent out
        data = {
            self.scaler_channel.raw_count.name: raw_counts,
            self.scaler_channel.net_count.name: net_counts,
            self.mcs.scaler.elapsed_time.name: times,
        }
        results = {
            "time": max(timestamps),
            "data": data,
            "timestamps": {key: timestamps for key in data.keys()},
        }
        yield results

    @property
    def default_time_signal(self):
        """The signal to use for setting exposure time when no other signal is
        provided.

        """
        return self.mcs.scaler.preset_time


async def load_ion_chambers(
    config: Mapping = None,
    registry: InstrumentRegistry = default_registry,
    connect: bool = True,
    auto_name=True,
):
    """Load ion chambers based on configuration files' ``[ion_chamber]``
    sections.

    The name for each ion chamber is retrieved from the scaler
    channel's .DESC field.

    """
    # Load IOC configuration from the config file
    if config is None:
        config = load_config()
    if "ion_chamber" not in config.keys():
        warnings.warn("Ion chambers not configured.")
        return []
    # Create the ion chambers
    devices = []
    for grp, cfg in config["ion_chamber"].items():
        # Get the corresponding scaler info
        scaler_prefix = config["scaler"][cfg["scaler"]]["prefix"]
        # Create the ion chamber
        devices.append(
            IonChamber(
                scaler_prefix=scaler_prefix,
                scaler_channel=cfg["scaler_channel"],
                preamp_prefix=cfg["preamp_prefix"],
                voltmeter_prefix=cfg["voltmeter_prefix"],
                voltmeter_channel=cfg["voltmeter_channel"],
                counts_per_volt_second=cfg["counts_per_volt_second"],
                name=grp,
                auto_name=auto_name,
            )
        )
        # Connect to devices
    if connect:
        devices = await connect_devices(
            devices, mock=not config["beamline"]["is_connected"], registry=registry
        )
    return devices
