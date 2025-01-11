import asyncio
from collections.abc import Sequence

from ophyd_async.core import (
    AsyncStatus,
    DetectorController,
    PathProvider,
    SignalR,
    StandardDetector,
    StrictEnum,
    TriggerInfo,
)
from ophyd_async.epics import adcore
from ophyd_async.epics.adcore._utils import (
    ADBaseDataType,
    NDAttributeDataType,
    NDAttributeParam,
    convert_ad_dtype_to_np,
)
from ophyd_async.epics.core import epics_signal_rw, epics_signal_x

from .area_detectors import HavenDetector, default_path_provider


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
        self.deadtime_correction = epics_signal_rw(bool, f"{prefix}CTRL_DTC")
        super().__init__(prefix=prefix, name=name)


class XspressController(DetectorController):
    def __init__(self, driver: adcore.ADBaseIO) -> None:
        self._drv = driver

    def get_deadtime(self, exposure: float) -> float:
        # Arbitrary value. To-do: fill this in when we know what to
        # include
        return 0.001

    @AsyncStatus.wrap
    async def prepare(self, trigger_info: TriggerInfo):
        await asyncio.gather(
            self._drv.num_images.set(trigger_info.total_number_of_triggers),
            self._drv.image_mode.set(adcore.ImageMode.MULTIPLE),
            self._drv.trigger_mode.set(XspressTriggerMode.INTERNAL),
            # Hardware deadtime correciton is not reliable
            # https://github.com/epics-modules/xspress3/issues/57
            self._drv.deadtime_correction.set(False),
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


class XspressDatasetDescriber(adcore.ADBaseDatasetDescriber):
    """The datatype cannot be reliably determined from DataType_RBV.

    Instead, read out whether deadtime correction is enabled and
    determine the datatype this way.

    https://github.com/epics-modules/xspress3/issues/57

    """

    async def np_datatype(self) -> str:
        dt_correction = await self._driver.deadtime_correction.get_value()
        if dt_correction:
            return convert_ad_dtype_to_np(ADBaseDataType.FLOAT64)
        else:
            return convert_ad_dtype_to_np(ADBaseDataType.UINT32)


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
                XspressDatasetDescriber(self.drv),
                self.drv,  # <- for DT ndattributes
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


def ndattribute_params(
    device_name: str, elements: Sequence[int]
) -> Sequence[NDAttributeParam]:
    """Create a set of ndattribute params that can be written to the AD's
    HDF5 file.

    These parameters can then be used with something like
    :py:func:`ophyd_async.plan_stubs.setup_ndattributes` to build the
    XML.

    """
    params = []
    for idx in elements:
        new_params = [
            NDAttributeParam(
                name=f"{device_name}-element{idx}-deadtime_factor",
                param="XSP3_CHAN_DTFACTOR",
                datatype=NDAttributeDataType.DOUBLE,
                addr=idx,
                description=f"Chan {idx} DTC Factor",
            ),
            NDAttributeParam(
                name=f"{device_name}-element{idx}-deadtime_percent",
                param="XSP3_CHAN_DTPERCENT",
                datatype=NDAttributeDataType.DOUBLE,
                addr=idx,
                description=f"Chan {idx} DTC Percent",
            ),
            NDAttributeParam(
                name=f"{device_name}-element{idx}-event_width",
                param="XSP3_EVENT_WIDTH",
                datatype=NDAttributeDataType.DOUBLE,
                addr=idx,
                description=f"Chan {idx} Event Width",
            ),
            NDAttributeParam(
                name=f"{device_name}-element{idx}-clock_ticks",
                param="XSP3_CHAN_SCA0",
                datatype=NDAttributeDataType.DOUBLE,
                addr=idx,
                description=f"Chan {idx} ClockTicks",
            ),
            NDAttributeParam(
                name=f"{device_name}-element{idx}-reset_ticks",
                param="XSP3_CHAN_SCA1",
                datatype=NDAttributeDataType.DOUBLE,
                addr=idx,
                description=f"Chan {idx} ResetTicks",
            ),
            NDAttributeParam(
                name=f"{device_name}-element{idx}-reset_counts",
                param="XSP3_CHAN_SCA2",
                datatype=NDAttributeDataType.DOUBLE,
                addr=idx,
                description=f"Chan {idx} ResetCounts",
            ),
            NDAttributeParam(
                name=f"{device_name}-element{idx}-all_event",
                param="XSP3_CHAN_SCA3",
                datatype=NDAttributeDataType.DOUBLE,
                addr=idx,
                description=f"Chan {idx} AllEvent",
            ),
            NDAttributeParam(
                name=f"{device_name}-element{idx}-all_good",
                param="XSP3_CHAN_SCA4",
                datatype=NDAttributeDataType.DOUBLE,
                addr=idx,
                description=f"Chan {idx} AllGood",
            ),
            NDAttributeParam(
                name=f"{device_name}-element{idx}-pileup",
                param="XSP3_CHAN_SCA7",
                datatype=NDAttributeDataType.DOUBLE,
                addr=idx,
                description=f"Chan {idx} Pileup",
            ),
        ]
        params.extend(new_params)
    return params
