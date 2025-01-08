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
from .dxp_controller import DXPController

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
    _multiplier = 1

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
        assert multiplier == 1
        raise NotImplementedError()

    async def close(self):
        raise NotImplementedError()

    async def observe_indices_written(
        self, timeout=DEFAULT_TIMEOUT
    ) -> AsyncGenerator[int, None]:
        """Wait until a specific index is ready to be collected"""
        async for num_captured in observe_value(self.netcdf.num_captured, timeout):
            yield num_captured // self._multiplier

    async def get_indices_written(self) -> int:
        num_captured = await self.netcdf.num_captured.get_value()
        return num_captured // self._multiplier

    async def collect_stream_docs(
        self, indices_written: int
    ) -> AsyncIterator[StreamAsset]:
        raise NotImplementedError()
