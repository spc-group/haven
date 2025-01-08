import asyncio
from collections.abc import AsyncGenerator, AsyncIterator, Sequence

from bluesky.protocols import StreamAsset
from event_model import DataKey
from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    AsyncStatus,
    DatasetDescriber,
    DetectorController,
    DetectorWriter,
    Device,
    HDFDataset,
    HDFFile,
    NameProvider,
    PathProvider,
    SignalR,
    StandardDetector,
    StrictEnum,
    TriggerInfo,
    observe_value,
    set_and_wait_for_value,
    wait_for_value,
)
from ophyd_async.epics import adcore
from ophyd_async.epics.adcore._core_io import NDPluginBaseIO
from ophyd_async.epics.core import (
    epics_signal_r,
    epics_signal_rw,
    epics_signal_rw_rbv,
    epics_signal_x,
)

from ..synApps import ScanInterval
from .area_detectors import HavenDetector, default_path_provider

# from ._utils import (
#     FileWriteMode,
#     convert_param_dtype_to_np,
#     convert_pv_dtype_to_np,
# )

import asyncio
from typing import Literal

from ophyd_async.core import (
    AsyncStatus,
    DetectorController,
    DetectorTrigger,
    TriggerInfo,
    set_and_wait_for_value,
)
from ophyd_async.epics import adcore

from .dxp_io import DXPDriverIO, DXPTriggerMode, DXPTriggerSource


# Need to figure out what the highest deadtime for a DXP detector is
_HIGHEST_POSSIBLE_DEADTIME = 1961e-6


class DXPController(DetectorController):
    def __init__(self, driver: DXPDriverIO) -> None:
        self._drv = driver
        self._arm_status: AsyncStatus | None = None

    def get_deadtime(self, exposure: float | None) -> float:
        return _HIGHEST_POSSIBLE_DEADTIME

    async def prepare(self, trigger_info: TriggerInfo):
        if trigger_info.total_number_of_triggers == 0:
            image_mode = adcore.ImageMode.CONTINUOUS
        else:
            image_mode = adcore.ImageMode.MULTIPLE
        if (exposure := trigger_info.livetime) is not None:
            await self._drv.acquire_time.set(exposure)

        trigger_mode, trigger_source = self._get_trigger_info(trigger_info.trigger)
        # trigger mode must be set first and on it's own!
        await self._drv.trigger_mode.set(trigger_mode)

        await asyncio.gather(
            self._drv.trigger_source.set(trigger_source),
            self._drv.num_images.set(trigger_info.total_number_of_triggers),
            self._drv.image_mode.set(image_mode),
        )

    async def arm(self):
        self._arm_status = await set_and_wait_for_value(self._drv.acquire, True)

    async def wait_for_idle(self):
        if self._arm_status:
            await self._arm_status

    def _get_trigger_info(
        self, trigger: DetectorTrigger
    ) -> tuple[DXPTriggerMode, DXPTriggerSource]:
        supported_trigger_types = (
            DetectorTrigger.CONSTANT_GATE,
            DetectorTrigger.EDGE_TRIGGER,
            DetectorTrigger.INTERNAL,
        )
        if trigger not in supported_trigger_types:
            raise ValueError(
                f"{self.__class__.__name__} only supports the following trigger "
                f"types: {supported_trigger_types} but was asked to "
                f"use {trigger}"
            )
        if trigger == DetectorTrigger.INTERNAL:
            return DXPTriggerMode.OFF, DXPTriggerSource.FREERUN
        else:
            return (DXPTriggerMode.ON, f"Line{self.gpio_number}")  # type: ignore

    async def disarm(self):
        await adcore.stop_busy_record(self._drv.acquire, False, timeout=1)
