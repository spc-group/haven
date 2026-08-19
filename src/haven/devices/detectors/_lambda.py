import asyncio
from collections.abc import Sequence
from dataclasses import dataclass

from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    DetectorTriggerLogic,
    SignalDict,
    SignalR,
    StrictEnum,
    SubsetEnum,
    observe_value,
)
from ophyd_async.epics.adcore import (
    ADAcquireLogic,
    ADBaseIO,
    ADWriterFactory,
    AreaDetector,
    NDPluginBaseIO,
    prepare_exposures,
)
from ophyd_async.epics.core import epics_signal_rw, epics_signal_rw_rbv

from .area_detectors import default_path_provider


class OperatingMode(StrictEnum):
    ONE_BIT = "1-Bit"
    SIX_BIT = "6-Bit"
    TWELVE_BIT = "12-Bit"
    TWENTY_FOUR_BIT = "24-Bit"


class LambdaImageMode(SubsetEnum):
    SINGLE = "Single"
    MULTIPLE = "Multiple"


class LambdaTriggerMode(StrictEnum):
    INTERNAL = "Internal"
    EXTERNAL_SEQUENCE = "External_SequencePer"
    EXTERNAL_IMAGE = "External_ImagePer"


class LambdaDriverIO(ADBaseIO):

    def __init__(self, prefix, name=""):
        self.operating_mode = epics_signal_rw_rbv(
            OperatingMode, f"{prefix}OperatingMode"
        )
        self.trigger_mode = epics_signal_rw(LambdaTriggerMode, f"{prefix}TriggerMode")
        self.dual_mode = epics_signal_rw_rbv(bool, f"{prefix}DualMode")
        self.gating_mode = epics_signal_rw_rbv(bool, f"{prefix}GatingMode")
        self.charge_summing = epics_signal_rw_rbv(bool, f"{prefix}ChargeSumming")
        self.energy_threshold = epics_signal_rw_rbv(float, f"{prefix}EnergyThreshold")
        self.dual_threshold = epics_signal_rw_rbv(float, f"{prefix}DualThreshold")
        super().__init__(prefix=prefix, name=name)
        # Our lambda's do not support all image modes
        self.image_mode = epics_signal_rw_rbv(LambdaImageMode, f"{prefix}ImageMode")
        self.set_name(self.name)


class LambdaAcquireLogic(ADAcquireLogic):
    async def ensure_ready(self):
        """The operating mode might change depending on the scan we're
        running.

        Stash it so we can restore it after the scan is done.

        """
        self._operating_mode, _ = await asyncio.gather(
            self.driver.operating_mode.get_value(),
            super().ensure_ready(),
        )

    async def ensure_stopped(self):
        coros = [super().ensure_stopped()]
        if getattr(self, "_operating_mode", None) is not None:
            coros.append(self.driver.operating_mode.set(self._operating_mode))
        await asyncio.gather(*coros)


@dataclass
class LambdaTriggerLogic(DetectorTriggerLogic):
    driver: ADBaseIO

    def get_deadtime(self, config_values: SignalDict) -> float:
        # From manual: No readout time in 12-bit, 6-bit and 1-bit mode,
        # 1 ms in 24-bit mode
        if config_values[self.driver.operating_mode] == OperatingMode.TWENTY_FOUR_BIT:
            return 1e-6
        return 0.0

    async def set_trigger_mode(self):
        """External triggering requires a 1ms additiona delay in 24-bit mode.

        We want to avoid that, so use 12-bit mode if needed.

        """
        bit_depth = await self.driver.operating_mode.get_value()
        if bit_depth == OperatingMode.TWENTY_FOUR_BIT:
            await self.driver.operating_mode.set(OperatingMode.TWELVE_BIT)

    async def prepare_edge(self, num: int, livetime: float) -> None:
        task = asyncio.ensure_future(
            asyncio.gather(
                self.set_trigger_mode(),
                prepare_exposures(self.driver, num),
                self.driver.trigger_mode.set(LambdaTriggerMode.EXTERNAL_IMAGE),
                self.driver.acquire_time.set(livetime),
            )
        )
        await self._wait_for_num_images(num)
        await task

    async def prepare_internal(
        self, num: int, livetime: float, deadtime: float
    ) -> None:
        await asyncio.gather(
            self.driver.trigger_mode.set(LambdaTriggerMode.INTERNAL),
            prepare_exposures(self.driver, num, livetime, deadtime),
        )

    async def _wait_for_num_images(self, num: int):
        """Make sure the number of frames is set properly (not too high)"""
        async for num_images in observe_value(
            self.driver.num_images, done_timeout=DEFAULT_TIMEOUT
        ):
            if num_images == num:
                break


class LambdaDetector(AreaDetector):
    """A Lambda area detector, e.g. Lambda 250K/."""

    _ophyd_labels_ = {"detectors", "area_detectors"}

    def __init__(
        self,
        prefix: str,
        *writer_factories: ADWriterFactory,
        driver_suffix="cam1:",
        override_deadtime: float | None = None,
        plugins: dict[str, NDPluginBaseIO] | None = None,
        config_sigs: Sequence[SignalR] = (),
        name: str = "",
    ) -> None:
        if len(writer_factories) == 0:
            writer_factories = (
                ADWriterFactory.hdf(default_path_provider(), writer_suffix="HDF1:"),
            )
        # Area detector IO devices
        driver = LambdaDriverIO(f"{prefix}{driver_suffix}")
        config_sigs = (
            driver.operating_mode,
            driver.dual_mode,
            driver.gating_mode,
            driver.charge_summing,
            driver.energy_threshold,
            driver.dual_threshold,
            *config_sigs,
        )
        super().__init__(
            driver,
            prefix,
            *writer_factories,
            acquire_logic=LambdaAcquireLogic(driver),
            trigger_logic=LambdaTriggerLogic(driver),
            plugins=plugins,
            config_sigs=config_sigs,
            name=name,
        )


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2025, UChicago Argonne, LLC
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
