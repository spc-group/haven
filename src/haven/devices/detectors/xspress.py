import asyncio
from collections.abc import Sequence

from ophyd_async.core import (
    PathProvider,
    SignalR,
    StandardDetector,
    DetectorController,
    DetectorTrigger,
    AsyncStatus,
    TriggerInfo,
    StrictEnum,
    set_and_wait_for_value,
)
from ophyd_async.epics import adcore
from ophyd_async.epics.core import epics_signal_rw, epics_signal_x

from .area_detectors import default_path_provider, HavenDetector


class XspressTriggerMode(StrictEnum):
    SOFTWARE = "Software"
    INTERNAL = "Internal"
    IDC = "IDC"
    TTL_VETO_ONLY = "TTL Veto Only"
    TTL_BOTH = "TTL Both"
    LVDS_VETO_ONLY = "LVDS Veto Only"
    LVDS_BOTH = "LVDS Both"
    SOFTWARE_INTERNAL = "Software + Internal"


class XspressDriverIO(adcore.ADBaseIO):
    def __init__(self, prefix, name=""):
        self.trigger_mode = epics_signal_rw(XspressTriggerMode, f"{prefix}TriggerMode")
        self.erase_on_start = epics_signal_rw(bool, f"{prefix}EraseOnStart")
        self.erase = epics_signal_x(f"{prefix}ERASE")
        super().__init__(prefix=prefix, name=name)


class XspressController(DetectorController):
    def __init__(self, driver: adcore.ADBaseIO) -> None:
        self._drv = driver

    def get_deadtime(self, exposure: float) -> float:
        # Xspress deadtime handling
        return 0.001

    @AsyncStatus.wrap
    async def prepare(self, trigger_info: TriggerInfo):
        await asyncio.gather(
            self._drv.num_images.set(trigger_info.total_number_of_triggers),
            self._drv.image_mode.set(adcore.ImageMode.multiple),
            self._drv.trigger_mode.set(XspressTriggerMode.INTERNAL),
        )

    async def wait_for_idle(self):
        if self._arm_status:
            await self._arm_status

    async def arm(self):
        self._arm_status = await adcore.start_acquiring_driver_and_ensure_status(
            self._drv
        )

    async def disarm(self):
        await adcore.stop_busy_record(self._drv.acquire, False, timeout=1)


class Xspress3Detector(HavenDetector, StandardDetector):
    _controller: DetectorController
    _writer: adcore.ADHDFWriter

    def __init__(
        self,
        prefix: str,
        path_provider: PathProvider | None = None,
        drv_suffix="det1:",
        hdf_suffix="HDF1:",
        name: str = "",
        config_sigs: Sequence[SignalR] = (),
    ):
        self.drv = XspressDriverIO(prefix + drv_suffix)
        self.hdf = adcore.NDFileHDFIO(prefix + hdf_suffix)

        if path_provider is None:
            path_provider = default_path_provider()
        super().__init__(
            XspressController(self.drv),
            adcore.ADHDFWriter(
                self.hdf,
                path_provider,
                lambda: self.name,
                adcore.ADBaseDatasetDescriber(self.drv),
            ),
            config_sigs=(self.drv.acquire_period, self.drv.acquire_time, *config_sigs),
            name=name,
        )

    @AsyncStatus.wrap
    async def stage(self) -> None:
        await asyncio.gather(
            super().stage(),
            self.drv.erase_on_start.set(False),
            self.drv.erase.trigger(),
        )