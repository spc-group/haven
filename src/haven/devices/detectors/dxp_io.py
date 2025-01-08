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
    SubsetEnum,
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



class ScanRate:
    pass


class DXPTriggerMode(StrictEnum):
    """DXP triggering mode."""

    ON = "On"
    OFF = "Off"


class DXPTriggerSource(SubsetEnum):
    """A minimal set of TriggerSources that must be supported by the
    underlying record.

    """
    FREERUN = "Freerun"
    LINE1 = "Line1"



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
