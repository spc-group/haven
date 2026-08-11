"""Implementation of a counter (eg. Measurement Computing) as a detector."""

import asyncio
import time
from collections.abc import AsyncGenerator, Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated as A
from typing import NotRequired, TypedDict

import numpy as np
from event_model import DataKey
from event_model.documents import PartialEventPage
from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    Array1D,
    AsyncStatus,
    DetectorAcquireLogic,
    DetectorDataLogic,
    DetectorTriggerLogic,
    DeviceVector,
    Signal,
    SignalR,
    SignalRW,
    StandardDetector,
    StandardReadable,
    StandardReadableFormat,
    StrictEnum,
    SubsetEnum,
    set_and_wait_for_other_value,
)

try:
    from ophyd_async.core import PageableDataProvider
except ImportError:
    # Remove when released https://github.com/bluesky/ophyd-async/pull/1367
    PageableDataProvider = object
from ophyd_async.epics.adcore import NDPluginBaseIO
from ophyd_async.epics.core import (
    EpicsDevice,
    EpicsOptions,
    PvSuffix,
    epics_signal_r,
    epics_signal_rw,
    wait_for_good_state,
)

from ..scaler import Scaler

__all__ = ["Counter", "CTR08Counter", "SIS3820Counter"]


class TriggerMode(StrictEnum):
    RISING_EDGE = "Rising edge"
    FALLING_EDGE = "Falling edge"
    HIGH_LEVEL = "High level"
    LOW_LEVEL = "Low level"


class ChannelAdvanceSource(SubsetEnum):
    INTERNAL = "Internal"
    EXTERNAL = "External"


class Channel1Source(SubsetEnum):
    INTERNAL_CLOCK = "Int. clock"
    EXTERNAL = "External"


class AcquireMode(SubsetEnum):
    MCS = "MCS"
    SCALER = "Scaler"


class Polarity(StrictEnum):
    NORMAL = "Normal"
    INVERTED = "Inverted"


class CountOnStart(StrictEnum):
    NO = "No"
    YES = "Yes"


class InputMode(SubsetEnum):
    MODE_0 = "Mode 0"
    MODE_1 = "Mode 1"
    MODE_2 = "Mode 2"
    MODE_3 = "Mode 3"
    MODE_4 = "Mode 4"
    MODE_5 = "Mode 5"
    MODE_6 = "Mode 6"


class Point0Action(StrictEnum):
    CLEAR = "Clear"
    NO_CLEAR = "No clear"
    SKIP = "Skip"


class PulseGenerator(EpicsDevice):
    frequency: A[SignalRW[float], PvSuffix.rbv("Frequency")]
    period: A[SignalRW[float], PvSuffix.rbv("Period")]
    duty_cycle: A[SignalRW[float], PvSuffix.rbv("DutyCycle")]
    pulse_width: A[SignalRW[float], PvSuffix.rbv("Width")]
    running: A[SignalRW[bool], PvSuffix("Run")]

    def __init__(self, prefix: str, name: str = ""):
        super().__init__(prefix, name=name)
        self.config_signals = [
            self.frequency,
            self.period,
            self.duty_cycle,
            self.pulse_width,
            self.running,
        ]


class MCAChannel(TypedDict):
    number: int
    name: NotRequired[str]


class MCA(StandardReadable):

    class MCAMode(SubsetEnum):
        PHA = "PHA"
        MCS = "MCS"
        LIST = "List"

    def __init__(self, prefix, name=""):
        # Signals
        with self.add_children_as_readables(
            StandardReadableFormat.HINTED_UNCACHED_SIGNAL
        ):
            self.count = epics_signal_r(Array1D[np.int32], f"{prefix}.VAL")
        self.background = epics_signal_r(Array1D[np.int32], f"{prefix}.BG")
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.mode = epics_signal_rw(self.MCAMode, f"{prefix}.MODE")
        super().__init__(name=name)


class MultiChannelScaler(EpicsDevice):
    """The MCS component of a SIS3820 or MeasComp counter.

    Devices
    =======
    mcas
      The multi-channel analyzers for measuring the channels
      repeatedly.

    """

    _ophyd_labels_ = {"scalers"}

    start_all: A[SignalRW[bool], PvSuffix("StartAll"), EpicsOptions(wait=False)]
    stop_all: A[SignalRW[bool], PvSuffix("StopAll"), EpicsOptions(wait=False)]
    erase_all: A[SignalRW[bool], PvSuffix("EraseAll"), EpicsOptions(wait=False)]
    erase_start: A[SignalRW[bool], PvSuffix("EraseStart"), EpicsOptions(wait=False)]
    acquiring: A[SignalR[bool], PvSuffix("Acquiring")]
    preset_time: A[SignalRW[float], PvSuffix("PresetReal")]
    elapsed_time: A[SignalR[float], PvSuffix("ElapsedReal")]
    prescale: A[SignalRW[int], PvSuffix("Prescale")]
    channel_advance_source: A[
        SignalRW[ChannelAdvanceSource], PvSuffix("ChannelAdvance")
    ]
    current_channel: A[SignalR[int], PvSuffix("CurrentChannel")]
    num_channels: A[SignalRW[int], PvSuffix("NuseAll")]
    num_channels_max: A[SignalR[int], PvSuffix("MaxChannels")]

    def __init__(self, prefix, channels: Sequence[MCAChannel], name=""):
        # Individual arrays for each channel
        self.mcas = DeviceVector(
            {
                ch["number"]: MCA(
                    f"{prefix}mca{ch['number']+1}", name=ch.get("name", "")
                )
                for ch in channels
            }
        )
        # Add a clock signal if it's not being used for something else
        if 0 not in self.mcas.keys():
            self.clock = MCA(prefix=f"{prefix}mca1")
        super().__init__(prefix=prefix, name=name)


class CounterDriverIO(EpicsDevice):
    """Base class for Counter driver."""

    MCS = MultiChannelScaler
    _channels: Sequence[MCAChannel]
    config_signals: Sequence[Signal]

    def __init__(
        self,
        prefix: str,
        scaler_prefix: str,
        mcs_prefix: str,
        channels: Sequence[MCAChannel],
        name: str = "",
    ):
        # These devices do not necessarily have Dale's offset correction support
        self.scaler = Scaler(
            prefix=f"{prefix}scaler1",
            channels=[ch["number"] for ch in channels],
            use_offset_correction=False,
        )
        self.mcs = self.MCS(prefix=mcs_prefix, channels=channels)
        self._channels = channels
        super().__init__(prefix=prefix, name=name)
        self.config_signals = [
            self.scaler.delay,
            self.scaler.clock_frequency,
            self.scaler.count_mode,
            self.scaler.preset_time,
            self.mcs.preset_time,
            self.mcs.prescale,
            self.mcs.channel_advance_source,
            self.mcs.num_channels,
            self.mcs.num_channels_max,
            self.mcs.clock.mode,
            *[mca.mode for mca in self.mcs.mcas.values()],
        ]

    def set_name(self, name: str, *, child_name_separator: str | None = None) -> None:
        super().set_name(name=name, child_name_separator=child_name_separator)
        # Rename the driver to avoid a bunch of "-driver-"s in the readings
        self.mcs.set_name(name=self.name, child_name_separator=child_name_separator)
        # Make the MCS channels match their given names
        for ch in self._channels:
            if ch_name := ch.get("name", ""):
                self.mcs.mcas[ch["number"]].set_name(
                    name=ch_name, child_name_separator=child_name_separator
                )


class CounterDataProvider(PageableDataProvider):
    driver: CounterDriverIO

    def __init__(self, driver: CounterDriverIO):
        self.driver = driver
        self.collections_written_signal = self.driver.mcs.current_channel
        super().__init__()

    async def make_datakeys(self, collections_per_event: int) -> dict[str, DataKey]:
        """Return a DataKey for each field this provider produces.

        Called before the first exposure is taken.

        :param collections_per_event: this should appear in the shape of each DataKey
        """
        mcas = self.driver.mcs.mcas.values()
        descriptions = await asyncio.gather(
            self.driver.mcs.clock.describe(),
            *(mca.describe() for mca in mcas),
        )
        return {key: val for desc in descriptions for key, val in desc.items()}

    async def make_pages(
        self, collections_written: int, collections_per_event: int
    ) -> AsyncGenerator[PartialEventPage, None]:
        """Emit event pages for collections written since the last call.

        :param collections_written: how many collections have been written so far
        :param collections_per_event: how many collections make up one event
        """
        mcas = self.driver.mcs.mcas.values()
        coros = [
            self.driver.scaler.clock_frequency.get_value(),
            self.driver.mcs.clock.count.get_value(),
            self.driver.mcs.clock.read(),
            *(mca.read() for mca in mcas),
        ]
        freq, clock, *mca_readings = await asyncio.gather(*coros)
        # Calculate timestamps,
        readings = mca_readings
        reverse = slice(None, None, -1)
        time_deltas = np.cumsum(-clock[reverse])[reverse] / freq
        # The delta for a point is really the delta for the point
        # after it
        time_deltas = np.asarray([*time_deltas[1:], 0])
        # time_deltas = (time_deltas - time_deltas[-1]) / freq
        timestamps = {
            k: v["timestamp"] + time_deltas
            for reading in readings
            for k, v in reading.items()
        }
        # Combine readings into pages
        data = {k: v["value"] for reading in readings for k, v in reading.items()}
        num_data = max(1, collections_written)
        yield {
            "time": [time.time()] * num_data,
            "data": data,
            "timestamps": timestamps,
        }


@dataclass
class CounterDataLogic(DetectorDataLogic):
    driver: CounterDriverIO

    async def prepare_bounded(
        self, datakey_name: str, num_collections: int, period: float
    ) -> PageableDataProvider:
        return CounterDataProvider(driver=self.driver)


@dataclass()
class CounterTriggerLogic(DetectorTriggerLogic):
    driver: CounterDriverIO

    async def prepare_internal(self, num: int, livetime: float, deadtime: float):
        """Prepare the detector to take internally triggered exposures.

        Parameters
        ==========
        num
          the number of exposures to take
        livetime
          how long the exposure should be, 0 means what is currently set
        deadtime
          how long between exposures, 0 means the shortest possible
        """
        coros = [
            self.driver.mcs.num_channels.set(num),
            self.driver.mcs.channel_advance_source.set(ChannelAdvanceSource.INTERNAL),
            self.driver.mcs.erase_all.set(True),
        ]
        if livetime > 0:
            coros.append(self.driver.mcs.dwell_time.set(livetime))
        await asyncio.gather(*coros)


@dataclass
class CounterAcquireLogic(DetectorAcquireLogic):
    driver: CounterDriverIO
    acquire_status: AsyncStatus | None = None

    async def wait_for_idle(self):
        if self.acquire_status:
            await self.acquire_status
        await wait_for_good_state(
            self.driver.mcs.acquiring,
            {False},
            timeout=DEFAULT_TIMEOUT,
        )

    async def start_acquiring(self):
        self.acquire_status = await set_and_wait_for_other_value(
            set_signal=self.driver.mcs.start_all,
            set_value=True,
            match_signal=self.driver.mcs.acquiring,
            match_value=True,
            wait_for_set_completion=False,
            timeout=DEFAULT_TIMEOUT,
        )

    async def ensure_stopped(self):
        disarm_status = await set_and_wait_for_other_value(
            set_signal=self.driver.mcs.stop_all,
            set_value=True,
            match_signal=self.driver.mcs.acquiring,
            match_value=False,
            wait_for_set_completion=False,
            timeout=DEFAULT_TIMEOUT,
        )
        await disarm_status


class Counter(StandardDetector):
    Driver = CounterDriverIO
    DEFAULT_CHANNELS: Sequence[MCAChannel] = tuple({"number": i} for i in range(1, 8))

    def __init__(
        self,
        prefix: str = "",
        mcs_prefix: str = "",
        scaler_prefix: str = "",
        channels: Sequence[MCAChannel] = DEFAULT_CHANNELS,
        plugins: Mapping[str, NDPluginBaseIO] | None = None,
        config_sigs: Sequence[SignalR] = (),
        name: str = "",
        driver: CounterDriverIO | None = None,
    ) -> None:
        self.driver = driver or self.Driver(
            prefix,
            channels=channels,
            mcs_prefix=mcs_prefix or f"{prefix}MCS:",
            scaler_prefix=scaler_prefix or f"{prefix}scaler1:",
        )
        if plugins is not None:
            for plugin_name, plugin in plugins.items():
                setattr(self, plugin_name, plugin)
        trigger_logic = CounterTriggerLogic(driver=self.driver)
        self.add_detector_logics(trigger_logic)
        acquire_logic = CounterAcquireLogic(self.driver)
        data_logic = CounterDataLogic(driver=self.driver)
        self.add_detector_logics(acquire_logic, data_logic)
        self.add_config_signals(*self.driver.config_signals, *config_sigs)
        super().__init__(name=name)

    def set_name(self, name: str, *, child_name_separator: str | None = None) -> None:
        super().set_name(name=name, child_name_separator=child_name_separator)
        # Rename the driver to avoid a bunch of "-driver-"s in the readings
        self.driver.set_name(name=self.name, child_name_separator=child_name_separator)


class CTR08Counter(Counter):

    class Driver(CounterDriverIO):
        model: A[SignalR[str], PvSuffix("ModelName")]
        model_number: A[SignalR[int], PvSuffix("ModelNumber")]
        unique_id: A[SignalR[str], PvSuffix("UniqueID")]
        firmware_version: A[SignalR[str], PvSuffix("FirmwareVersion")]
        ul_version: A[SignalR[str], PvSuffix("ULVersion")]
        driver_version: A[SignalR[str], PvSuffix("DriverVersion")]

        class MCS(MultiChannelScaler):
            dwell_time: A[SignalRW[float], PvSuffix.rbv("Dwell")]
            action_on_start: A[SignalRW[Point0Action], PvSuffix("Point0Action")]
            external_trigger_mode: A[SignalRW[TriggerMode], PvSuffix("TrigMode")]

        def __init__(
            self,
            prefix: str,
            *args,
            **kwargs,
        ):
            self.pulse_generators = DeviceVector(
                {i: PulseGenerator(f"{prefix}PulseGen{i+1}") for i in range(4)}
            )
            pulse_gen_signals = [
                sig
                for gen in self.pulse_generators.values()
                for sig in gen.config_signals
            ]
            super().__init__(prefix, *args, **kwargs)
            self.config_signals = [
                self.model,
                self.model_number,
                self.unique_id,
                self.firmware_version,
                self.ul_version,
                self.driver_version,
                self.mcs.dwell_time,
                self.mcs.action_on_start,
                self.mcs.external_trigger_mode,
                *pulse_gen_signals,
                *self.config_signals,
            ]


class SIS3820Counter(Counter):

    class Driver(CounterDriverIO):
        class MCS(MultiChannelScaler):
            dwell_time: A[SignalRW[float], PvSuffix("Dwell")]
            action_on_start: A[SignalRW[CountOnStart], PvSuffix("CountOnStart")]

            clock_source: A[SignalRW[Channel1Source], PvSuffix("Channel1Source")]
            acquire_mode: A[SignalRW[AcquireMode], PvSuffix("AcquireMode")]
            input_mode: A[SignalRW[InputMode], PvSuffix("InputMode")]
            input_polarity: A[SignalRW[Polarity], PvSuffix("InputPolarity")]

        def __init__(
            self,
            prefix: str,
            *args,
            **kwargs,
        ):
            super().__init__(prefix, *args, **kwargs)
            self.config_signals = [
                self.mcs.dwell_time,
                self.mcs.action_on_start,
                self.mcs.clock_source,
                self.mcs.acquire_mode,
                self.mcs.input_mode,
                self.mcs.input_polarity,
                *self.config_signals,
            ]


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2026, UChicago Argonne, LLC
#
# Distributed under the terms of the 3-Clause BSD License
#
# The full license is in the file LICENSE, distributed with this software.
#
# DISCLAIMER
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# -----------------------------------------------------------------------------
