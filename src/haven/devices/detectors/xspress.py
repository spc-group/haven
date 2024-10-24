import asyncio
from collections.abc import Sequence

from ophyd_async.core import PathProvider, SignalR, StandardDetector, DetectorController, DetectorTrigger, AsyncStatus, TriggerInfo
from ophyd_async.epics import adcore



class XspressController(DetectorController):
    def __init__(self, driver: adcore.ADBaseIO) -> None:
        self._drv = driver

    def get_deadtime(self, exposure: float) -> float:
        # Xspress deadtime handling
        return 0.001

    async def prepare(self, trigger_info: TriggerInfo):
        raise NotImplementedError()

    async def wait_for_idle(self):
        raise NotImplementedError()

    async def arm(
        self,
        num: int,
        trigger: DetectorTrigger = DetectorTrigger.internal,
        exposure: float | None = None,
    ) -> AsyncStatus:
        await asyncio.gather(
            self._drv.num_images.set(num),
            self._drv.image_mode.set(adcore.ImageMode.multiple),
            self._drv.trigger_mode.set(f"FOO{trigger}"),
        )
        if exposure is not None:
            await self._drv.acquire_time.set(exposure)
        return await adcore.start_acquiring_driver_and_ensure_status(self._drv)

    async def disarm(self):
        await adcore.stop_busy_record(self._drv.acquire, False, timeout=1)


class Xspress3Detector(StandardDetector):
    _controller: DetectorController
    _writer: adcore.ADHDFWriter

    def __init__(
        self,
        prefix: str,
        path_provider: PathProvider,
        drv_suffix="det1:",
        hdf_suffix="HDF1:",
        name: str = "",
        config_sigs: Sequence[SignalR] = (),
    ):
        self.drv = adcore.ADBaseIO(prefix + drv_suffix)
        self.hdf = adcore.NDFileHDFIO(prefix + hdf_suffix)

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
