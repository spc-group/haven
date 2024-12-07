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
from .dxp_io import DXPDriverIO
from .netcdf import NetCDFWriter, NDFileNetCDFIO
# from ._utils import (
#     FileWriteMode,
#     convert_param_dtype_to_np,
#     convert_pv_dtype_to_np,
# )


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
