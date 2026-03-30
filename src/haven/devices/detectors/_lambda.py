import asyncio
from collections.abc import Sequence
from dataclasses import dataclass

from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    DetectorTriggerLogic,
    PathProvider,
    SignalR,
    StrictEnum,
    SubsetEnum,
    observe_value,
)
from ophyd_async.epics.adcore import (
    ADArmLogic,
    ADBaseIO,
    ADWriterType,
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


@dataclass
class LambdaTriggerLogic(DetectorTriggerLogic):
    driver: ADBaseIO

    def get_deadtime(self, exposure: float | None) -> float:
        # From manual: No readout time in 12-bit, 6-bit and 1-bit mode,
        # 1 ms in 24-bit mode
        return 1e-3

    async def prepare_level(self, num: int) -> None:
        task = asyncio.ensure_future(
            asyncio.gather(
                prepare_exposures(self.driver, num),
                self.driver.trigger_mode.set(LambdaTriggerMode.EXTERNAL_SEQUENCE),
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
        path_provider: PathProvider | None = None,
        drv_suffix="cam1:",
        writer_type: ADWriterType = ADWriterType.HDF,
        writer_suffix="HDF1:",
        name: str = "",
        config_sigs: Sequence[SignalR] = (),
        plugins: dict[str, NDPluginBaseIO] | None = None,
    ):
        if path_provider is None:
            path_provider = default_path_provider()
        # Area detector IO devices
        driver = LambdaDriverIO(f"{prefix}{drv_suffix}")
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
            prefix=prefix,
            driver=driver,
            arm_logic=ADArmLogic(driver),
            trigger_logic=LambdaTriggerLogic(driver),
            path_provider=path_provider,
            writer_type=writer_type,
            writer_suffix=writer_suffix,
            plugins=plugins,
            config_sigs=config_sigs,
            name=name,
        )

    @property
    def default_time_signal(self):
        return self.driver.acquire_time


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
