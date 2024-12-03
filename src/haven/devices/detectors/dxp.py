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


class NDFileNetCDFIO(NDPluginBaseIO):
    def __init__(self, prefix: str, name="") -> None:
        # Define some signals
        self.file_path = epics_signal_rw_rbv(str, prefix + "FilePath")
        self.file_name = epics_signal_rw_rbv(str, prefix + "FileName")
        self.file_path_exists = epics_signal_r(bool, prefix + "FilePathExists_RBV")
        self.file_template = epics_signal_rw_rbv(str, prefix + "FileTemplate")
        self.full_file_name = epics_signal_r(str, prefix + "FullFileName_RBV")
        self.file_write_mode = epics_signal_rw_rbv(
            adcore.FileWriteMode, prefix + "FileWriteMode"
        )
        self.num_capture = epics_signal_rw_rbv(int, prefix + "NumCapture")
        self.num_captured = epics_signal_r(int, prefix + "NumCaptured_RBV")
        self.lazy_open = epics_signal_rw_rbv(bool, prefix + "LazyOpen")
        self.capture = epics_signal_rw_rbv(bool, prefix + "Capture")
        self.array_size0 = epics_signal_r(int, prefix + "ArraySize0")
        self.array_size1 = epics_signal_r(int, prefix + "ArraySize1")
        self.create_directory = epics_signal_rw_rbv(int, prefix + "CreateDirectory")
        super().__init__(prefix, name)


class NetCDFWriter(DetectorWriter):
    def __init__(
        self,
        netcdf: NDFileNetCDFIO,
        path_provider: PathProvider,
        name_provider: NameProvider,
        dataset_describer: DatasetDescriber,
        *plugins: adcore.NDArrayBaseIO,
    ) -> None:
        self.netcdf = netcdf
        self._path_provider = path_provider
        self._name_provider = name_provider
        self._dataset_describer = dataset_describer

        self._plugins = plugins
        self._capture_status: AsyncStatus | None = None

    async def open(self, multiplier: int = 1) -> dict[str, DataKey]:
        raise NotImplementedError()

    async def close(self):
        raise NotImplementedError()

    async def observe_indices_written(
        self, timeout=DEFAULT_TIMEOUT
    ) -> AsyncGenerator[int, None]:
        raise NotImplementedError()

    async def get_indices_written(self) -> int:
        raise NotImplementedError()

    async def collect_stream_docs(
        self, indices_written: int
    ) -> AsyncIterator[StreamAsset]:
        raise NotImplementedError()


class ScanRate:
    pass


class DXPDriverIO(Device):

    class PresetMode(StrictEnum):
        NO_PRESET = "No preset"
        REAL_TIME = "Real time"
        LIVE_TIME = "Live time"
        EVENTS = "Events"
        TRIGGERS = "Triggers"

    class CollectMode(StrictEnum):
        MCA_SPECTRA = "MCA spectra"
        MCA_MAPPING = "MCA mapping"
        SCA_MAPPING = "SCA mapping"
        LIST_MAPPING = "List mapping"

    def __init__(self, prefix: str, name: str = "") -> None:
        # SNL status records
        self.snl_connected = epics_signal_r(bool, f"{prefix}SNL_Connected")
        # Acquisition control records
        self.erase = epics_signal_x(f"{prefix}EraseAll")
        self.start = epics_signal_x(f"{prefix}StartAll")
        self.stop = epics_signal_x(f"{prefix}StopAll")
        # Preset control records
        self.preset_mode = epics_signal_rw(self.PresetMode, f"{prefix}PresetMode")
        self.preset_live_time = epics_signal_rw(float, f"{prefix}PresetLive")
        self.preset_real_time = epics_signal_rw(float, f"{prefix}PresetReal")
        self.preset_events = epics_signal_rw(int, f"{prefix}PresetEvents")
        self.preset_triggers = epics_signal_rw(int, f"{prefix}PresetTriggers")
        # Status/statistics records
        self.status_scan_rate = epics_signal_rw(ScanInterval, f"{prefix}StatusAll.SCAN")
        self.reading_scan_rate = epics_signal_rw(ScanInterval, f"{prefix}ReadAll.SCAN")
        self.acquiring = epics_signal_r(bool, f"{prefix}Acquiring")
        self.elapsed_real_time = epics_signal_r(float, f"{prefix}ElapsedReal")
        self.elapsed_live_time = epics_signal_r(float, f"{prefix}ElapsedLive")
        self.accumulated_dead_time = epics_signal_r(float, f"{prefix}DeadTime")
        self.instantaneous_dead_time = epics_signal_r(float, f"{prefix}IDeadTime")
        # Low-level parameters
        self.low_level_params_scan_rate = epics_signal_rw(
            ScanInterval, f"{prefix}ReadLLParams.SCAN"
        )
        # Trace and diagnostic records
        self.baseline_histograms_read_scan_rate = epics_signal_rw(
            ScanInterval, f"{prefix}ReadBaselineHistograms.SCAN"
        )
        self.traces_scan_rate = epics_signal_rw(
            ScanInterval, f"{prefix}ReadTraces.SCAN"
        )
        self.baseline_histogram_scan_rate = epics_signal_rw(
            ScanInterval, f"{prefix}dxp1:BaselineHistogram.SCAN"
        )
        self.trace_data_scan_rate = epics_signal_rw(
            ScanInterval, f"{prefix}dxp1:TraceData.SCAN"
        )
        # Mapping mode control records
        self.collect_mode = epics_signal_rw_rbv(
            self.CollectMode, f"{prefix}CollectMode"
        )

        super().__init__(name=name)


class DXPController(DetectorController):
    def __init__(self, driver: adcore.ADBaseIO) -> None:
        self._drv = driver

    async def arm(self):
        self._arm_status = await adcore.start_acquiring_driver_and_ensure_status(
            self._drv
        )

    async def disarm(self):
        await adcore.stop_busy_record(self._drv.acquire, False, timeout=1)

    async def wait_for_idle(self):
        if self._arm_status:
            await self._arm_status

    def get_deadtime(self, exposure: float) -> float:
        # No-op value. Fill this in when we know what to include
        return 0.001

    @AsyncStatus.wrap
    async def prepare(self, trigger_info: TriggerInfo):
        raise NotImplementedError()


class DXPDetector(HavenDetector, StandardDetector):
    """An ophyd-async detector for XIA's DXP-based detectors.

    E.g. XMAP, Saturn, and Mercury.

    """

    _controller: DetectorController
    _writer: adcore.ADHDFWriter

    def __init__(
        self,
        prefix: str,
        path_provider: PathProvider | None = None,
        netcdf_suffix="netCDF1:",
        name: str = "",
        config_sigs: Sequence[SignalR] = (),
    ):
        self.drv = DXPDriverIO(prefix)
        self.netcdf = NDFileNetCDFIO(prefix + netcdf_suffix)

        if path_provider is None:
            path_provider = default_path_provider()
        super().__init__(
            DXPController(self.drv),
            NetCDFWriter(
                self.netcdf,
                path_provider,
                lambda: self.name,
                adcore.ADBaseDatasetDescriber(self.drv),
            ),
            config_sigs=(
                self.drv.preset_mode,
                self.drv.preset_live_time,
                self.drv.preset_real_time,
                self.drv.preset_events,
                self.drv.preset_triggers,
                self.drv.collect_mode,
                *config_sigs,
            ),
            name=name,
        )
