"""Implementation of a Measurement Computing USB counter as a detector."""

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated as A

import numpy as np
from bluesky.protocols import Reading
from event_model import DataKey
from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    Array1D,
    DetectorArmLogic,
    DetectorDataLogic,
    DetectorTriggerLogic,
    DeviceVector,
    ReadableDataProvider,
    SignalR,
    SignalRW,
    StandardDetector,
    StrictEnum,
    SubsetEnum,
    derived_signal_r,
    set_and_wait_for_other_value,
)
from ophyd_async.epics.adcore import NDPluginBaseIO
from ophyd_async.epics.core import (
    EpicsDevice,
    PvSuffix,
    epics_signal_r,
    wait_for_good_state,
)

from ..scaler import MCA, Scaler


class ReadFormat(StrictEnum):
    BINARY = "Binary"
    ASCII = "ASCII"


class TriggerMode(StrictEnum):
    FREE_RUN = "Free run"
    EXTERNAL_TRIGGER = "Ext. trig."
    EXTERNAL_BULB = "Ext. bulb"
    EXTERNAL_GATE = "Ext. gate"


class TriggerPolarity(StrictEnum):
    POSITIVE = "Positive"
    NEGATIVE = "Negative"


class NumChannels(StrictEnum):
    ONE = "1"
    TWO = "2"
    FOUR = "4"


class ChannelAdvanceSource(SubsetEnum):
    INTERNAL = "Internal"
    EXTERNAL = "External"


def _reduce_array(arr: Array1D[np.int32]) -> int:
    """Reduce an array to a single point."""
    return int(arr[-1]) if len(arr) > 0 else 0


class PulseGenerator(EpicsDevice):

    frequency: A[SignalRW[float], PvSuffix.rbv("Frequency")]
    period: A[SignalRW[float], PvSuffix.rbv("Period")]
    duty_cycle: A[SignalRW[float], PvSuffix.rbv("DutyCycle")]
    pulse_width: A[SignalRW[float], PvSuffix.rbv("Width")]
    running: A[SignalRW[bool], PvSuffix("Run")]


class USBCounterDriverIO(EpicsDevice):
    """Base class for USB Counter driver."""

    model: A[SignalR[str], PvSuffix("ModelName")]
    model_number: A[SignalR[int], PvSuffix("ModelNumber")]
    unique_id: A[SignalR[str], PvSuffix("UniqueID")]
    firmware_version: A[SignalR[str], PvSuffix("FirmwareVersion")]
    ul_version: A[SignalR[str], PvSuffix("ULVersion")]
    driver_version: A[SignalR[str], PvSuffix("DriverVersion")]
    start_all: A[SignalRW[str], PvSuffix("MCS:StartAll")]
    stop_all: A[SignalRW[str], PvSuffix("MCS:StopAll")]
    erase_all: A[SignalRW[str], PvSuffix("MCS:EraseAll")]
    erase_start: A[SignalRW[str], PvSuffix("MCS:EraseStart")]
    acquiring: A[SignalR[bool], PvSuffix("MCS:Acquiring")]
    preset_time: A[SignalRW[str], PvSuffix("MCS:PresetReal")]
    dwell_time: A[SignalRW[str], PvSuffix.rbv("MCS:Dwell")]
    elapsed_time: A[SignalR[float], PvSuffix("MCS:ElapsedReal")]
    prescale: A[SignalRW[float], PvSuffix("MCS:Prescale")]
    channel_advance_source: A[
        SignalRW[ChannelAdvanceSource], PvSuffix("MCS:ChannelAdvance")
    ]
    current_channel: A[SignalR[float], PvSuffix("MCS:CurrentChannel")]
    num_channels: A[SignalRW[float], PvSuffix("MCS:NuseAll")]
    num_channels_max: A[SignalR[int], PvSuffix("MCS:MaxChannels")]

    def __init__(self, prefix: str, channels: Sequence[int], name: str = ""):
        self.pulse_generators = DeviceVector(
            {i: PulseGenerator(f"{prefix}PulseGen{i+1}") for i in range(4)}
        )
        self.scaler = Scaler(prefix=f"{prefix}scaler1", channels=channels)
        self.mcas = DeviceVector({i: MCA(f"{prefix}mca{i+1}") for i in channels})
        # Add a clock signal if it's not being used for something else
        if 0 not in self.mcas.keys():
            self.clock_ticks_array = epics_signal_r(
                Array1D[np.int32], f"{prefix}mca1.VAL"
            )
            self.clock_ticks = derived_signal_r(
                _reduce_array, arr=self.clock_ticks_array
            )
        super().__init__(prefix=prefix, name=name)


@dataclass
class StepDataLogic(DetectorDataLogic):
    driver: USBCounterDriverIO

    async def prepare_single(self, datakey_name: str) -> ReadableDataProvider:
        return SignalsProvider(
            signals=[
                self.driver.elapsed_time,
                self.driver.current_channel,
                self.driver.clock_ticks,
            ]
        )


@dataclass
class SignalsProvider(ReadableDataProvider):
    signals: Sequence[SignalR]

    async def make_datakeys(self) -> dict[str, DataKey]:
        """Return a DataKey for each Readable that produces a Reading.

        Called before the first exposure is taken.
        """
        coros = [sig.describe() for sig in self.signals]
        readings = await asyncio.gather(*coros)
        merged = dict(pair for reading in readings for pair in reading.items())
        return merged

    async def make_readings(self) -> dict[str, Reading]:
        coros = [sig.read(cached=False) for sig in self.signals]
        readings = await asyncio.gather(*coros)
        merged = dict(pair for reading in readings for pair in reading.items())
        return merged


@dataclass()
class USBCounterTriggerLogic(DetectorTriggerLogic):
    driver: USBCounterDriverIO

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
        await asyncio.gather(
            self.driver.num_channels.set(num),
            self.driver.channel_advance_source.set(ChannelAdvanceSource.INTERNAL),
        )


@dataclass
class USBCounterArmLogic(DetectorArmLogic):
    def __init__(self, driver: USBCounterDriverIO):
        self.driver = driver

    async def wait_for_idle(self):
        if self.acquire_status:
            await self.acquire_status
        await wait_for_good_state(
            self.driver.acquiring,
            {False},
            timeout=DEFAULT_TIMEOUT,
        )

    async def arm(self):
        self.acquire_status = await set_and_wait_for_other_value(
            set_signal=self.driver.erase_start,
            set_value=True,
            match_signal=self.driver.acquiring,
            match_value=True,
            wait_for_set_completion=False,
            timeout=DEFAULT_TIMEOUT,
        )

    async def disarm(self, on_unstage: bool):
        disarm_status = await set_and_wait_for_other_value(
            set_signal=self.driver.stop_all,
            set_value=True,
            match_signal=self.driver.acquiring,
            match_value=False,
            wait_for_set_completion=False,
            timeout=DEFAULT_TIMEOUT,
        )
        await disarm_status


class USBCounter(StandardDetector):
    def __init__(
        self,
        arm_logic: DetectorArmLogic | None = None,
        prefix: str = "",
        channels: Sequence[int] = range(1, 8),
        plugins: Mapping[str, NDPluginBaseIO] | None = None,
        config_sigs: Sequence[SignalR] = (),
        name: str = "",
        driver: USBCounterDriverIO | None = None,
    ) -> None:
        self.driver = driver or USBCounterDriverIO(prefix, channels=channels)
        if plugins is not None:
            for plugin_name, plugin in plugins.items():
                setattr(self, plugin_name, plugin)
        trigger_logic = USBCounterTriggerLogic(driver=self.driver)
        self.add_detector_logics(trigger_logic)
        arm_logic = USBCounterArmLogic(self.driver)
        step_logic = StepDataLogic(driver=self.driver)
        self.add_detector_logics(arm_logic, step_logic)
        self.add_config_signals(
            # self.driver.model,
            # self.driver.firmware,
            # self.driver.sample_time,
            # self.driver.acquire_mode,
            # self.driver.read_format,
            # self.driver.trigger_mode,
            # self.driver.trigger_polarity,
            # self.driver.bias_voltage,
            # self.driver.bias_voltage_actual,
            # self.driver.bias_interlock,
            *config_sigs
        )
        super().__init__(name=name)

    def set_name(self, name: str, *, child_name_separator: str | None = None) -> None:
        super().set_name(name=name, child_name_separator=child_name_separator)
        # Rename the driver to avoid a bunch of "-driver-"s in the readings
        self.driver.set_name(name=self.name, child_name_separator=child_name_separator)


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
