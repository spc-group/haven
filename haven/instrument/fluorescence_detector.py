from enum import IntEnum
from collections import OrderedDict
from typing import Optional, Sequence

from ophyd import (
    mca,
    Device,
    EpicsSignal,
    Component as Cpt,
    DynamicDeviceComponent as DDC,
    Kind,
)

from .scaler_triggered import ScalerTriggered
from .instrument_registry import registry
from .._iconfig import load_config
from .. import exceptions


default_kind = Kind.normal | Kind.config


class ROI(mca.ROI):
    _default_read_attrs = [
        "count",
        "net_count",
    ]
    _default_configuration_attrs = [
        "label",
        "bkgnd_chans",
        "hi_chan",
        "lo_chan",
    ]
    kind = default_kind


def add_rois(range_, kind=Kind.omitted, **kwargs):
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
    # import pdb; pdb.set_trace()
    kwargs["kind"] = kind
    for roi in range_:
        if not (0 <= roi < 32):
            raise ValueError("roi must be in the set [0,31]")
        attr = "roi{}".format(roi)
        defn[attr] = (ROI, ".R{}".format(roi), kwargs,)
    return defn


class MCARecord(mca.EpicsMCARecord):
    rois = DDC(add_rois(range(0, 32)), kind=default_kind)
    _default_read_attrs = ["rois"]


@registry.register
class DxpDetectorBase(mca.EpicsDXPMultiElementSystem):
    """A fluorescence detector based on XIA-DXP XMAP electronics.

    Creates MCA components based on the number of elements.
    
    """
    _default_read_attrs = [
        'preset_live_time',
        'preset_real_time',
        'dead_time',
        'elapsed_live',
        'elapsed_real',
        'mca1',
        'mca2',
        'mca3',
        'mca4',
    ]
    _default_configuration_attrs = [
        'max_scas',
        'num_scas',
        'poll_time',
        'prescale',
        'preset_mode',
        'preset_events',
        'preset_triggers',
        'snl_connected',
    ]
    _omitted_attrs = [  # Just save them here for easy reference
        'channel_advance',
        'client_wait',
        'dwell',
        'save_system',
        'save_system_file',
        'set_client_wait',
        'erase_all',
        'erase_start',
        'start_all',
        'stop_all',
        'set_acquire_busy',
        'acquire_busy',
        'status_all',
        'status_all_once',
        'acquiring',
        'read_baseline_histograms',
        'read_all',
        'read_all_once',
        'copy_adcp_ercent_rule',
        'copy_baseline_cut_enable',
        'copy_baseline_cut_percent',
        'copy_baseline_filter_length',
        'copy_baseline_threshold',
        'copy_decay_time',
        'copy_detector_polarity',
        'copy_energy_threshold',
        'copy_gap_time',
        'copy_max_energy',
        'copy_max_width',
        'copy_peaking_time',
        'copy_preamp_gain',
        'copy_roic_hannel',
        'copy_roie_nergy',
        'copy_roi_sca',
        'copy_reset_delay',
        'copy_trigger_gap_time',
        'copy_trigger_peaking_time',
        'copy_trigger_threshold',
        'do_read_all',
        'do_read_baseline_histograms',
        'do_read_traces',
        'do_status_all',
        'read_low_level_params',
        'read_traces',
        'trace_modes',
        'trace_times',
        'idead_time',
    ]
    
    def mcas(self):
        mcas = [getattr(self, m) for m in self.component_names if m.startswith("mca")]
        return mcas

    def rois(self, roi_indices: Optional[Sequence[int]] = None):
        # Get the list of ROIs to activate
        all_rois = []
        for mca in self.mcas():
            rois = mca.rois.component_names
            rois = [getattr(mca.rois, r) for r in rois]
            # Get sub-list if requested
            if roi_indices is not None:
                rois = [rois[i] for i in roi_indices]
            all_rois.extend(rois)
        return all_rois
    
    def enable_rois(self, rois: Optional[Sequence[int]] = None):
        """Include some, or all, ROIs in the list of detectors to
        read.

        rois
          A list of indices for which ROIs to enable. Default is to
          operate on all ROIs.

        """
        for roi in self.rois(roi_indices=rois):
            roi.kind = default_kind


    def disable_rois(self, rois: Optional[Sequence[int]] = None):
        """Remove some, or all, ROIs from the list of detectors to
        read.

        rois
          A list of indices for which ROIs to enable. Default is to
          operate on all ROIs.

        """
        for roi in self.rois(roi_indices=rois):
            roi.kind = Kind.omitted
               

class XspressDetector(ScalerTriggered, Device):
    """A fluorescence detector plugged into an Xspress3 readout."""
    
    num_frames = Cpt(EpicsSignal, "NumImages", kind=Kind.config)
    trigger_mode = Cpt(EpicsSignal, "TriggerMode", kind=Kind.config)
    acquire = Cpt(EpicsSignal, "Acquire", kind=Kind.omitted)
    erase = Cpt(EpicsSignal, "Erase", kind=Kind.omitted)

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
        self.stage_sigs[self.erase] = self.erase_states.ERASE
        self.stage_sigs[self.trigger_mode] = self.mode.TTL_VETO_ONLY
        self.stage_sigs[self.acquire] = self.acquire_states.ACQUIRE

    @property
    def stage_num_frames(self):
        """How many frames to prepare for when staging this detector."""
        return self.stage_sigs.get(self.num_frames, 1)

    @stage_num_frames.setter
    def stage_num_frames(self, val):
        self.stage_sigs[self.num_frames] = val


def load_dxp_detector(device_name, prefix, num_elements):
    # Build the mca components
    mca_names = [f"mca{n}" for n in range(1, num_elements+1)]
    mcas = {mname: Cpt(MCARecord, suffix=mname, name=mname)
            for mname in mca_names}
    # Add the ROIs to the list of readable detectors
    # Create a dynamic subclass
    class_name = device_name.title().replace("_", "")
    parent_classes = (DxpDetectorBase,)
    Cls = type(class_name, parent_classes, mcas)
    det = Cls(prefix=f"{prefix}:", name=device_name)
    

def load_fluorescence_detectors(config=None):
    # Get the detector definitions from config files
    if config is None:
        config = load_config()
    for name, cfg in config.get("fluorescence_detector", {}).items():
        if "prefix" not in cfg.keys():
            continue
        # Build the detector device
        if cfg["electronics"] == "dxp":
            load_dxp_detector(device_name=name, prefix=cfg["prefix"],
                              num_elements=cfg["num_elements"])
        else:
            msg = f"Electronics '{cfg['electronics']}' for {name} not supported."
            raise exceptions.UnknownDeviceConfiguration(msg)
