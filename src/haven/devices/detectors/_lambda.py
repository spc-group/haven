import asyncio
from collections.abc import Iterable, Sequence
from itertools import repeat

from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    AsyncStatus,
    DetectorTrigger,
    PathProvider,
    SignalR,
    StrictEnum,
    SubsetEnum,
    TriggerInfo,
    observe_value,
)
from ophyd_async.epics import adcore
from ophyd_async.epics.adcore import ADBaseController, AreaDetector
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


class LambdaDriverIO(adcore.ADBaseIO):

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


class LambdaController(ADBaseController):
    def get_deadtime(self, exposure: float | None) -> float:
        # From manual: No readout time in 12-bit, 6-bit and1-bit mode,
        # 1 ms in 24-bit mode
        return 1e-3

    async def prepare(self, trigger_info: TriggerInfo) -> None:
        external_triggers = [
            DetectorTrigger.CONSTANT_GATE,
            DetectorTrigger.VARIABLE_GATE,
            DetectorTrigger.EDGE_TRIGGER,
        ]
        if trigger_info.trigger == DetectorTrigger.INTERNAL:
            return await super().prepare(trigger_info)
        elif trigger_info.trigger in external_triggers:
            trigger_mode = LambdaTriggerMode.EXTERNAL_SEQUENCE
        else:
            raise ValueError(
                f"{self.name} does not recognize trigger mode '{trigger_info.trigger}'"
            )
        max_frames = 2000
        num_frames = trigger_info.number_of_events or max_frames
        if isinstance(num_frames, Iterable):
            # We have multiple events with distinct number of channels
            self._trigger_frame_nums = iter(num_frames)
        else:
            # Fixed number of events
            self._trigger_frame_nums = repeat(num_frames)
        aws = [
            self.driver.num_images.set(trigger_info.total_number_of_exposures),
            self.driver.image_mode.set(adcore.ADImageMode.MULTIPLE),
            self.driver.trigger_mode.set(trigger_mode),
        ]
        if trigger_info.livetime is not None:
            aws.extend(
                [
                    self.driver.acquire_time.set(trigger_info.livetime),
                    self.driver.acquire_period.set(
                        trigger_info.livetime + trigger_info.deadtime
                    ),
                ]
            )
        task = asyncio.ensure_future(asyncio.gather(*aws))
        # Make sure the number of frames is set properly (not too high)

        async for num_images in observe_value(
            self.driver.num_images, done_timeout=DEFAULT_TIMEOUT
        ):
            if num_images == trigger_info.total_number_of_exposures:
                break
        await task


class LambdaDetector(AreaDetector):
    """A Lambda area detector, e.g. Lambda 250K/."""

    _ophyd_labels_ = {"detectors", "area_detectors"}

    def __init__(
        self,
        prefix: str,
        path_provider: PathProvider | None = None,
        drv_suffix="cam1:",
        writer_cls: type[adcore.ADWriter] = adcore.ADHDFWriter,
        fileio_suffix="HDF1:",
        name: str = "",
        config_sigs: Sequence[SignalR] = (),
        plugins: dict[str, adcore.NDPluginBaseIO] | None = None,
    ):
        if path_provider is None:
            path_provider = default_path_provider()
        # Area detector IO devices
        driver = LambdaDriverIO(f"{prefix}{drv_suffix}")
        controller = LambdaController(driver)
        writer = writer_cls.with_io(
            prefix,
            path_provider,
            dataset_source=driver,
            fileio_suffix=fileio_suffix,
            plugins=plugins,
        )
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
            controller=controller,
            writer=writer,
            plugins=plugins,
            name=name,
            config_sigs=config_sigs,
        )

    @property
    def default_time_signal(self):
        return self.driver.acquire_time

    @AsyncStatus.wrap
    async def prepare(self, value: TriggerInfo) -> None:
        ## This shouldn't really be necessary, but during fly scans
        ## the xspress doesn't finish if the number of frames isn't
        ## set on the HDF5 plugin.
        await super().prepare(value=value)
        await self._writer.fileio.num_capture.set(value.total_number_of_exposures)


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
