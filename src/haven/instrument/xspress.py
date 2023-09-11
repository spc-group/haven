from enum import IntEnum
import logging
import asyncio
from typing import Optional, Sequence
from collections import OrderedDict

import numpy as np
from apstools.devices import CamMixin_V34, SingleTrigger_V34
from ophyd import (
    ADComponent as ADCpt,
    DetectorBase,
    CamBase,
    SimDetectorCam,
    Lambda750kCam,
    EigerDetectorCam,
    Component as Cpt,
    EpicsSignal,
    EpicsSignalRO,
    EpicsSignalWithRBV,
    DynamicDeviceComponent as DDC,
    SingleTrigger,
    Kind,
    OphydObject,
    Device,
    Signal,
    StatusBase,
)
from ophyd.signal import InternalSignal
from ophyd.areadetector.base import EpicsSignalWithRBV as SignalWithRBV
from ophyd.areadetector.filestore_mixins import FileStoreHDF5IterativeWrite
from ophyd.areadetector.plugins import (
    HDF5Plugin_V34,
    HDF5Plugin_V31,
    ImagePlugin_V34,
    ImagePlugin_V31,
    PvaPlugin_V34,
    PvaPlugin_V31,
    TIFFPlugin_V34,
    TIFFPlugin_V31,
    ROIPlugin_V34,
    ROIPlugin_V31,
    StatsPlugin_V31 as OphydStatsPlugin_V31,
    StatsPlugin_V34 as OphydStatsPlugin_V34,
    OverlayPlugin,
)

from .._iconfig import load_config
from .instrument_registry import registry
from .fluorescence_detector import XRFMixin, ROIMixin, MCASumMixin, add_roi_sums
from .device import await_for_connection, aload_devices, make_device, RegexComponent as RECpt


log = logging.getLogger(__name__)


active_kind = Kind.normal | Kind.config


NUM_ROIS = 16


class ROI(ROIMixin):
    lo_chan = Cpt(EpicsSignal, "MinX", kind="config")
    label = Cpt(EpicsSignal, "Name", kind="config")
    hi_chan = Cpt(Signal, kind="config")
    size = Cpt(EpicsSignal, "SizeX", kind="config")
    background_width = Cpt(EpicsSignal, "BgdWidth", kind="config")
    use = Cpt(EpicsSignalWithRBV, "Use", kind="config")

    count = Cpt(EpicsSignalRO, "Total_RBV", kind="normal")
    net_count = Cpt(EpicsSignalRO, "Net_RBV", kind="normal")
    min_count = Cpt(EpicsSignalRO, "MinValue_RBV", kind="normal")
    max_count = Cpt(EpicsSignalRO, "MaxValue_RBV", kind="normal")
    mean_count = Cpt(EpicsSignalRO, "MeanValue_RBV", kind="normal")

    _default_read_attrs = [
        "count",
        "net_count",
    ]
    _default_configuration_attrs = [
        "label",
        "background_width",
        "hi_chan",
        "lo_chan",
    ]
    kind = active_kind


def add_rois(range_: Sequence[int] = range(NUM_ROIS), kind=Kind.normal, **kwargs):
    """Add one or more ROIs to an MCA instance

    Parameters
    ----------
    range_ : sequence of ints
        Must be be in the set [0,31]

    By default, an EpicsMCA is initialized with all 32 rois. These
    provide the following Components as EpicsSignals (N=[0,31]):
    EpicsMCA.rois.roiN.(label,count,net_count,preset_cnt, is_preset,
    bkgnd_chans, hi_chan, lo_chan)

    """
    defn = OrderedDict()
    kwargs["kind"] = kind
    for roi in range_:
        if not (0 <= roi <= 47):
            raise ValueError(f"roi {roi} must be in the set [0,47]")
        attr = f"roi{roi}"
        defn[attr] = (
            ROI,
            f"ROI:{roi+1}:",
            kwargs,
        )
    return defn


class MCARecord(MCASumMixin, Device):
    rois = DDC(add_rois(), kind=active_kind)
    spectrum = Cpt(EpicsSignalRO, ":ArrayData", kind="normal")
    dead_time_percent = RECpt(EpicsSignalRO, ":DeadTime_RBV", pattern=r":MCA", repl=":C", lazy=True)
    dead_time_factor = RECpt(EpicsSignalRO, ":DTFactor_RBV", pattern=r":MCA", repl=":C", lazy=True)
    _default_read_attrs = [
        "rois",
        "spectrum",
        "dead_time_percent",
        "dead_time_factor",
        "total_count",
    ]
    _default_configuration_attrs = ["rois"]
    kind = active_kind



def add_mcas(range_, kind=active_kind, **kwargs):
    """Add one or more MCARecords to a device

    Parameters
    ----------
    range_
      Indices for which to create MCA records.

    """
    defn = OrderedDict()
    kwargs["kind"] = kind
    for idx in range_:
        attr = f"mca{idx}"
        defn[attr] = (
            MCARecord,
            f"MCA{idx+1}",
            kwargs,
        )
    return defn


class Xspress3Detector(SingleTrigger, DetectorBase, XRFMixin):
    """A fluorescence detector plugged into an Xspress3 readout."""
    _dead_times: dict
    
    cam = ADCpt(CamBase, "det1:")
    # Core control interface signals
    acquire = ADCpt(SignalWithRBV, "det1:Acquire")
    acquire_period = ADCpt(SignalWithRBV, "det1:AcquirePeriod")
    acquire_time = ADCpt(SignalWithRBV, "det1:AcquireTime")
    erase = ADCpt(EpicsSignal, "det1:ERASE")
    # Dead time aggregate statistics
    dead_time_average = ADCpt(InternalSignal, kind="normal")
    dead_time_min = ADCpt(InternalSignal, kind="normal")
    dead_time_max = ADCpt(InternalSignal, kind="normal")

    # Number of elements is overridden by subclasses
    mcas = DDC(
        add_mcas(range_=range(1)),
        kind=active_kind,
        default_read_attrs=["mca0"],
        default_configuration_attrs=["mca0"],
    )
    roi_sums = DDC(
        add_roi_sums(mcas=range(1), rois=range(NUM_ROIS)),
        kind=active_kind,
        default_read_attrs=[f"roi{i}" for i in range(NUM_ROIS)],
        default_configuration_attrs=[f"roi{i}" for i in range(NUM_ROIS)],
    )

    _default_read_attrs = [
        "cam",
        "mcas",
        "dead_time_average",
        "dead_time_min",
        "dead_time_max",
    ]
    _default_configuration_attrs = [
        "cam",
        "mcas",
    ]
    
    class erase_states(IntEnum):
        DONE = 0
        ERASE = 1

    class acquire_states(IntEnum):
        DONE = 0
        ACQUIRE = 1

    class mode(IntEnum):
        SOFTWARE = 0
        INTERNAL = 1
        IDC = 2
        TTL_VETO_ONLY = 3
        TTL_BOTH = 4
        LVDS_VETO_ONLY = 5
        LVDS_BOTH = 6

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.stage_sigs[self.erase] = self.erase_states.ERASE
        # self.stage_sigs[self.trigger_mode] = self.mode.TTL_VETO_ONLY
        # self.stage_sigs[self.acquire] = self.acquire_states.ACQUIRE
        self.stage_sigs[self.cam.num_images] = 1
        # The image mode is not a real signal in the Xspress3 IOC
        del self.stage_sigs['cam.image_mode']
        # Set up subscriptions for dead-time calculations
        self._dead_times = {}
        for mca in self.mca_records():
            mca.dead_time_percent.subscribe(self._update_dead_time_calcs)

    def _update_dead_time_calcs(self, *args, value, obj, **kwargs):
        self._dead_times[obj.name] = value
        # Calculate aggregate dead time stats
        dead_times = np.asarray(list(self._dead_times.values()))
        self.dead_time_average.put(np.mean(dead_times), internal=True)
        self.dead_time_min.put(np.min(dead_times), internal=True)
        self.dead_time_max.put(np.max(dead_times), internal=True)
        

    @property
    def stage_num_frames(self):
        """How many frames to prepare for when staging this detector."""
        return self.stage_sigs.get(self.num_frames, 1)

    @stage_num_frames.setter
    def stage_num_frames(self, val):
        self.stage_sigs[self.num_frames] = val

    @property
    def num_elements(self):
        return len(self.mcas.component_names)

    def complete(self) -> StatusBase:
        """Wait for flying to be complete.

        This commands the Xspress to stop acquiring fly-scan data.

        Returns
        -------
        complete_status : StatusBase
          Indicate when flying has completed
        """
        return self.acquire.set(0)


async def make_xspress_device(name, prefix, num_elements):
    # Build the mca components
    # (Epics uses 1-index instead of 0-index)
    mca_range = range(num_elements)
    attrs = {
        "mcas": DDC(
            add_mcas(range_=mca_range),
            kind=active_kind,
            default_read_attrs=[f"mca{i}" for i in mca_range],
            default_configuration_attrs=[f"mca{i}" for i in mca_range],
        ),
        "roi_sums": DDC(
            add_roi_sums(mcas=mca_range, rois=range(NUM_ROIS)),
            kind=active_kind,
            default_read_attrs=[f"roi{i}" for i in range(NUM_ROIS)],
            default_configuration_attrs=[f"roi{i}" for i in range(NUM_ROIS)],
        ),
    }
    # Create a dynamic subclass with the MCAs
    class_name = name.title().replace("_", "")
    parent_classes = (Xspress3Detector,)
    Cls = type(class_name, parent_classes, attrs)
    return await make_device(Cls, name=name, prefix=f"{prefix}:", labels={"xrf_detectors"})


def load_xspress_coros(config=None):
    if config is None:
        config = load_config()
    # Create detector device
    for name, cfg in config.get("xspress", {}).items():
        yield make_xspress_device(prefix=cfg["prefix"], num_elements=cfg["num_elements"], name=name)


def load_xspress(config=None):
    asyncio.run(aload_devices(*load_xspress_coros(config=config)))
