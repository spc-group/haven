"""Implementation of a TetraAMM electrometer as a detector.

This class does not include the individual channels. Sub-classes
should add these for specific configurations, e.g. split ion chamber.

"""

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated as A

from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    DetectorArmLogic,
    DetectorTriggerLogic,
    SignalR,
    SignalRW,
    StandardDetector,
    StrictEnum,
    non_zero,
)
from ophyd_async.epics.adcore import ADArmLogic, ADImageMode, NDPluginBaseIO
from ophyd_async.epics.core import (
    EpicsDevice,
    EpicsOptions,
    PvSuffix,
    wait_for_good_state,
)

from ..synApps import ScanInterval


class CurrentRange(StrictEnum):
    PM_120_UA = "+- 120 uA"
    PM_120_NA = "+- 120 nA"


class Geometry(StrictEnum):
    DIAMOND = "Diamond"
    SQUARE = "Square"


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


class BaseTetrAmmDriverIO(EpicsDevice):
    """Base class for TetrAmm electrometer driver."""

    # : A[SignalR[], PvSuffix("")]
    model: A[SignalR[str], PvSuffix("Model")]
    firmware: A[SignalR[str], PvSuffix("Firmware")]
    sample_time: A[SignalR[float], PvSuffix("SampleTime_RBV")]
    acquire: A[SignalRW[bool], PvSuffix.rbv("Acquire"), EpicsOptions(wait=non_zero)]
    acquire_mode: A[SignalRW[ADImageMode], PvSuffix.rbv("AcquireMode")]
    current_range: A[SignalRW[CurrentRange], PvSuffix.rbv("Range")]
    geometry: A[SignalRW[Geometry], PvSuffix.rbv("Geometry")]
    values_per_reading: A[SignalRW[int], PvSuffix.rbv("ValuesPerRead")]
    averaging_time: A[SignalRW[float], PvSuffix.rbv("AveragingTime")]
    fast_averaging_scan: A[SignalRW[ScanInterval], PvSuffix("FastAverageScan.SCAN")]
    fast_averaging_time: A[SignalRW[float], PvSuffix.rbv("FastAveragingTime")]
    num_acquisitions: A[SignalRW[int], PvSuffix.rbv("NumAcquire")]
    acquisition_counter: A[SignalR[int], PvSuffix("NumAcquired")]
    num_to_average: A[SignalR[int], PvSuffix("NumAverage_RBV")]
    num_averaged: A[SignalR[int], PvSuffix("NumAveraged_RBV")]
    num_to_average_fast: A[SignalR[int], PvSuffix("NumFastAverage")]
    num_channels: A[SignalRW[NumChannels], PvSuffix.rbv("NumChannels")]
    read_format: A[SignalRW[ReadFormat], PvSuffix.rbv("ReadFormat")]
    trigger_mode: A[SignalRW[TriggerMode], PvSuffix.rbv("TriggerMode")]
    trigger_polarity: A[SignalRW[TriggerPolarity], PvSuffix.rbv("TriggerPolarity")]
    bias_state: A[SignalRW[bool], PvSuffix.rbv("BiasState")]
    bias_voltage: A[SignalRW[float], PvSuffix.rbv("BiasVoltage")]
    bias_voltage_actual: A[SignalR[float], PvSuffix("HVVReadback")]
    bias_interlock: A[SignalRW[bool], PvSuffix.rbv("BiasInterlock")]
    bias_current: A[SignalR[float], PvSuffix("HVIReadback")]
    temperature: A[SignalR[float], PvSuffix("Temperature")]


@dataclass()
class TetrAmmTriggerLogic(DetectorTriggerLogic):
    driver: BaseTetrAmmDriverIO

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
            self.driver.acquire_mode.set(ADImageMode.MULTIPLE),
            self.driver.num_acquisitions.set(num),
        )


class TetrAmmArmLogic(ADArmLogic):
    async def wait_for_idle(self):
        if self.acquire_status:
            await self.acquire_status
        await wait_for_good_state(
            self.driver.acquire,
            {False},
            timeout=DEFAULT_TIMEOUT,
        )


class BaseTetrAmmDetector(StandardDetector):
    def __init__(
        self,
        arm_logic: DetectorArmLogic | None = None,
        prefix: str = "",
        plugins: Mapping[str, NDPluginBaseIO] | None = None,
        config_sigs: Sequence[SignalR] = (),
        name: str = "",
    ) -> None:
        self.driver = BaseTetrAmmDriverIO(prefix)
        if plugins is not None:
            for plugin_name, plugin in plugins.items():
                setattr(self, plugin_name, plugin)
        trigger_logic = TetrAmmTriggerLogic(driver=self.driver)
        self.add_detector_logics(trigger_logic)
        arm_logic = TetrAmmArmLogic(self.driver)
        self.add_detector_logics(arm_logic)
        self.add_config_signals(
            self.driver.model,
            self.driver.firmware,
            self.driver.sample_time,
            self.driver.acquire_mode,
            self.driver.current_range,
            self.driver.geometry,
            self.driver.read_format,
            self.driver.trigger_mode,
            self.driver.trigger_polarity,
            self.driver.bias_voltage,
            self.driver.bias_voltage_actual,
            self.driver.bias_interlock,
            *config_sigs
        )
        super().__init__(name=name)


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
