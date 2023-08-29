from enum import IntEnum
import logging
import asyncio
from typing import Optional, Sequence
from collections import OrderedDict

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
)
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
from .device import await_for_connection, aload_devices, make_device


log = logging.getLogger(__name__)


active_kind = Kind.normal | Kind.config


class ROI(Device):

    minimum = Cpt(EpicsSignal, "MinX", kind="config")
    label = Cpt(EpicsSignal, "Name", kind="config")
    size = Cpt(EpicsSignal, "SizeX", kind="config")
    background_width = Cpt(EpicsSignal, "BgdWidth", kind="config")
    use = Cpt(EpicsSignalWithRBV, "Use", kind="config")
    
    total_count = Cpt(EpicsSignalRO, "Total_RBV", kind="normal")
    net_count = Cpt(EpicsSignalRO, "Net_RBV", kind="normal")
    min_count = Cpt(EpicsSignalRO, "MinValue_RBV", kind="normal")
    max_count = Cpt(EpicsSignalRO, "MaxValue_RBV", kind="normal")
    mean_count = Cpt(EpicsSignalRO, "MeanValue_RBV", kind="normal")
    
                  
    _default_read_attrs = [
        # "count",
        # "net_count",
    ]
    _default_configuration_attrs = [
        # "label",
        # "bkgnd_chans",
        # "hi_chan",
        # "lo_chan",
    ]
    # hints = {"fields": ["net_count"]}
    kind = active_kind


def add_rois(range_: Sequence[int] = range(1, 49), kind=Kind.normal, **kwargs):
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
        if not (1 <= roi <= 48):
            raise ValueError("roi must be in the set [0,31]")
        attr = f"roi{roi}"
        defn[attr] = (
            ROI,
            f"ROI:{roi}:",
            kwargs,
        )
    return defn


class MCARecord(Device):
    rois = DDC(add_rois(), kind=active_kind)
    spectrum = Cpt(EpicsSignalRO, ":ArrayData", kind="normal")
    _default_read_attrs = [
        "rois",
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
            f"MCA{idx}",
            kwargs,
        )
    return defn


class Xspress3Detector(DetectorBase):
    """A fluorescence detector plugged into an Xspress3 readout."""
    cam = ADCpt(CamBase, "det1:")
    
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

    @property
    def stage_num_frames(self):
        """How many frames to prepare for when staging this detector."""
        return self.stage_sigs.get(self.num_frames, 1)

    @stage_num_frames.setter
    def stage_num_frames(self, val):
        self.stage_sigs[self.num_frames] = val


async def make_xspress_device(name, prefix, num_elements):
    # Build the mca components
    # (Epics uses 1-index instead of 0-index)
    mca_range = range(1, num_elements + 1)
    attrs = {
        "mcas": DDC(
            add_mcas(range_=mca_range),
            kind=active_kind,
            default_read_attrs=[f"mca{i}" for i in mca_range],
            default_configuration_attrs=[f"mca{i}" for i in mca_range],
        )
    }
    # Create a dynamic subclass with the MCAs
    class_name = name.title().replace("_", "")
    parent_classes = (Xspress3Detector,)
    Cls = type(class_name, parent_classes, attrs)
    det = Cls(prefix=f"{prefix}:", name=name, labels={"xrf_detectors"})
    # Verify it is connection
    try:
        await await_for_connection(det)
    except TimeoutError as exc:
        msg = f"Could not connect to Xspress3 detector: {name} ({prefix}:)"
        log.warning(msg)
        raise
    else:
        log.info(f"Created Xspress3 detector: {name} ({prefix})")
        registry.register(det)
        return det
        


def load_xspress_coros(config=None):
    if config is None:
        config = load_config()
    # Create slits
    for name, cfg in config.get("xspress", {}).items():
        yield make_xspress_device(prefix=cfg["prefix"], num_elements=cfg["num_elements"], name=name)


def load_xspress(config=None):
    asyncio.run(aload_devices(*load_xspress_coros(config=config)))
