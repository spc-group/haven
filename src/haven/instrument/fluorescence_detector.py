from enum import IntEnum
from collections import OrderedDict
from typing import Optional, Sequence
import warnings
import logging
import asyncio
import time

from ophyd import (
    mca,
    Device,
    EpicsSignal,
    EpicsSignalRO,
    Component as Cpt,
    DynamicDeviceComponent as DDC,
    Kind,
    flyers,
)
from ophyd.areadetector.plugins import NetCDFPlugin_V34
from ophyd.status import SubscriptionStatus, StatusBase
from apstools.utils import cleanupText

from .scaler_triggered import ScalerTriggered
from .instrument_registry import registry
from .device import RegexComponent as RECpt, await_for_connection, aload_devices
from .._iconfig import load_config
from .. import exceptions


__all__ = ["DxpDetectorBase", "load_fluorescence_detectors"]


log = logging.getLogger(__name__)


active_kind = Kind.normal | Kind.config


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
    # hints = {"fields": ["net_count"]}
    kind = active_kind
    _original_name = None
    _original_kinds = {}
    _dynamic_hint_fields = ["net_count"]
    # Signals
    # net_count = Cpt(EpicsSignalRO, "N", kind=Kind.hinted, lazy=True)
    # user_kind = Cpt(EpicsSignal, "_BS_KIND", lazy=True)
    is_hinted = RECpt(EpicsSignal, "BH", pattern=r"\.R", repl="_R", lazy=True)

    def stage(self):
        self._original_name = self.name
        # Append the ROI label to the signal name
        label = cleanupText(str(self.label.get()))
        if label != "":
            self.name = f"{self.name}_{label}"
        # Set the kind based on the user-settable ".R0_BS_HINTED" PV
        if self.is_hinted.get():
            new_kind = Kind.hinted
        else:
            new_kind = Kind.normal
        self._original_kinds = {
            fld: getattr(self, fld).kind for fld in self._dynamic_hint_fields
        }
        for fld in self._dynamic_hint_fields:
            getattr(self, fld).kind = new_kind
        super().stage()

    def unstage(self):
        # Restore the original (pre-staged) name
        self.name = self._original_name
        # Restore original signal kinds
        for fld, kind in self._original_kinds.items():
            getattr(self, fld).kind = kind
        super().unstage()


def add_rois(range_: Sequence[int] = range(32), kind=Kind.normal, **kwargs):
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
        if not (0 <= roi < 32):
            raise ValueError("roi must be in the set [0,31]")
        attr = "roi{}".format(roi)
        defn[attr] = (
            ROI,
            ".R{}".format(roi),
            kwargs,
        )
    return defn


class MCARecord(mca.EpicsMCARecord):
    rois = DDC(add_rois(), kind=active_kind)
    _default_read_attrs = [
        "rois",
        "spectrum",
        "preset_real_time",
        "preset_live_time",
        "elapsed_real_time",
        "elapsed_live_time",
        "background",
    ]
    _default_configuration_attrs = ["rois", "mode"]
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
            f"mca{idx}",
            kwargs,
        )
    return defn


class DxpDetectorBase(
    flyers.FlyerInterface, mca.EpicsDXPMapping, mca.EpicsDXPMultiElementSystem
):
    """A fluorescence detector based on XIA-DXP XMAP electronics.

    Creates MCA components based on the number of elements.

    """

    class CollectMode(IntEnum):
        MCA_SPECTRA = 0
        MCA_MAPPING = 1
        SCA_MAPPING = 2
        LIST_MAPPING = 3

    write_path: str = "M:\\epics\\fly_scanning\\"
    read_path: str = "/net/s20data/sector20/tmp/"
    # By default, a 4-element detector, subclass for more elements
    mcas = DDC(
        add_mcas(range_=range(1, 5)),
        default_read_attrs=["mca1"],
        default_configuration_attrs=["mca1"],
    )
    net_cdf = Cpt(NetCDFPlugin_V34, "netCDF1:")
    _default_read_attrs = [
        "preset_live_time",
        "preset_real_time",
        "dead_time",
        "elapsed_live",
        "elapsed_real",
        "mcas",
    ]
    _default_configuration_attrs = [
        "max_scas",
        "num_scas",
        "poll_time",
        "prescale",
        "preset_mode",
        "preset_events",
        "preset_triggers",
        "snl_connected",
        "mcas",
    ]
    _omitted_attrs = [  # Just save them here for easy reference
        "channel_advance",
        "client_wait",
        "dwell",
        "save_system",
        "save_system_file",
        "set_client_wait",
        "erase_all",
        "erase_start",
        "start_all",
        "stop_all",
        "set_acquire_busy",
        "acquire_busy",
        "status_all",
        "status_all_once",
        "acquiring",
        "read_baseline_histograms",
        "read_all",
        "read_all_once",
        "copy_adcp_ercent_rule",
        "copy_baseline_cut_enable",
        "copy_baseline_cut_percent",
        "copy_baseline_filter_length",
        "copy_baseline_threshold",
        "copy_decay_time",
        "copy_detector_polarity",
        "copy_energy_threshold",
        "copy_gap_time",
        "copy_max_energy",
        "copy_max_width",
        "copy_peaking_time",
        "copy_preamp_gain",
        "copy_roic_hannel",
        "copy_roie_nergy",
        "copy_roi_sca",
        "copy_reset_delay",
        "copy_trigger_gap_time",
        "copy_trigger_peaking_time",
        "copy_trigger_threshold",
        "do_read_all",
        "do_read_baseline_histograms",
        "do_read_traces",
        "do_status_all",
        "read_low_level_params",
        "read_traces",
        "trace_modes",
        "trace_times",
        "idead_time",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stage_sigs[self.collect_mode] = self.CollectMode.MCA_SPECTRA

    @property
    def num_rois(self):
        n_rois = float("inf")
        for mca in self.mca_records():
            n_rois = min(n_rois, len(mca.rois.component_names))
        return n_rois

    @property
    def num_elements(self):
        return len(self.mca_records())

    def mca_records(self, mca_indices: Optional[Sequence[int]] = None):
        mcas = [
            getattr(self.mcas, m)
            for m in self.mcas.component_names
            if m.startswith("mca")
        ]
        # Filter by element index
        if mca_indices is not None:
            mcas = [
                m for m in mcas if int(m.dotted_name.split(".")[-1][3:]) in mca_indices
            ]
        return mcas

    def rois(self, roi_indices: Optional[Sequence[int]] = None):
        # Get the list of ROIs to activate
        all_rois = []
        for mca in self.mca_records():
            rois = mca.rois.component_names
            rois = [getattr(mca.rois, r) for r in rois]
            # Get sub-list if requested
            if roi_indices is not None:
                rois = [rois[i] for i in roi_indices]
            all_rois.extend(rois)
        return all_rois

    def get_roi(self, mca_num: int, roi_num: int):
        """Get a specific ROI component based on
        its MCA number and then the ROI number.
        """
        mca = getattr(self.mcas, f"mca{mca_num}")
        roi = getattr(mca.rois, f"roi{roi_num}")
        return roi

    def enable_rois(
        self,
        rois: Optional[Sequence[int]] = None,
        elements: Optional[Sequence[int]] = None,
    ) -> list:
        """Include some, or all, ROIs in the list of detectors to
        read.

        elements
          A list of indices for which elements to enable. Default is
          to operate on all elements.

        rois
          A list of indices for which ROIs to enable. Default is to
          operate on all ROIs.

        Returns
        =======
        statuses
          The status object for each ROI that was changed
        """
        statuses = []

        if rois is None:
            rois = range(self.num_rois)

        if elements is None:
            elements = range(1, self.num_elements + 1)

        for mca_num in elements:
            for roi_num in rois:
                roi = self.get_roi(mca_num, roi_num)
                status = roi.is_hinted.set(1)
                statuses.append(status)
        return statuses

    def disable_rois(
        self,
        rois: Optional[Sequence[int]] = None,
        elements: Optional[Sequence[int]] = None,
    ) -> list:
        """Remove some, or all, ROIs from the list of detectors to
        read.

        elements
          A list of indices for which elements to enable. Default is
          to operate on all elements.

        rois
          A list of indices for which ROIs to enable. Default is to
          operate on all ROIs.

        Returns
        =======
        statuses
          The status object for each ROI that was changed
        """
        statuses = []
        # Default to all elements and all ROIs
        if rois is None:
            rois = range(self.num_rois)

        if elements is None:
            elements = range(1, self.num_elements + 1)
        # Go through and set the hint on requested ROIs
        for mca_num in elements:
            for roi_num in rois:
                roi = self.get_roi(mca_num, roi_num)
                status = roi.is_hinted.set(0)
                statuses.append(status)
        return statuses

    def kickoff(self):
        # Make sure the CDF file write plugin is primed (assumes
        # dimensions will be empty when not primed)
        is_primed = len(self.net_cdf.dimensions.get()) > 0
        if not is_primed:
            msg = f"{self.net_cdf.name} plugin not primed."
            warnings.warn(msg, RuntimeWarning)
            exc = exceptions.PluginNotPrimed(msg)
            status = StatusBase()
            status.set_exception(exc)
            return status
        # Set up the status for when the detector is ready to fly
        def check_acquiring(*, old_value, value, **kwargs):
            is_acquiring = bool(value)
            if is_acquiring:
                self.start_timestamp = time.time()
            return is_acquiring

        status = SubscriptionStatus(self.acquiring, check_acquiring)
        # Configure the mapping controls
        self.collect_mode.set(self.CollectMode.MCA_MAPPING)
        self.pixel_advance_mode.set("Gate")
        # Configure the netCDF file writer
        self.net_cdf.enable.set("Enable").wait()
        [
            status.wait()
            for status in [
                self.net_cdf.file_path.set(self.write_path),
                self.net_cdf.file_name.set("fly_scan_temp.nc"),
                self.net_cdf.file_write_mode.set("Capture"),
            ]
        ]
        self.net_cdf.capture.set(1).wait()
        # Start the detector
        self.erase_start.set(1)
        return status

    def complete(self):
        # Stop the CDF file writer
        self.net_cdf.capture.set(0).wait()
        self.stop_all.set(1)

        # Set up the status for when the detector is done collecting
        def check_acquiring(*, old_value, value, **kwargs):
            is_acquiring = bool(value)
            return not is_acquiring

        status = SubscriptionStatus(self.acquiring, check_acquiring)
        return status


def parse_xmap_buffer(buff):
    """Extract meaningful data from an XMAP internal buffer during mapping.

    For more information, see section 5.3.3 of
    https://cars9.uchicago.edu/software/epics/XMAP_User_Manual.pdf

    """
    data = {
        "header": {}
    }
    header = buff[:256]
    # Verify tag words
    assert header[0] == 0x55AA
    assert header[1] == 0xAA55
    # Parse remaining buffer header
    head_data = data["header"]
    head_data["buffer_header_size"] = header[2]
    head_data["mapping_mode"] = header[3]
    head_data["run_number"] = header[4]
    head_data["buffer_number"] = header[5:7]
    head_data["buffer_id"] = header[7]
    head_data["num_pixels"] = header[8]
    head_data["starting_pixel"] = header[9:11]
    head_data["module"] = header[11]
    head_data["buffer_overrun"] = header[24]
    # head_data[""] = 
    return data




async def make_dxp_device(device_name, prefix, num_elements):
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
    class_name = device_name.title().replace("_", "")
    parent_classes = (DxpDetectorBase,)
    Cls = type(class_name, parent_classes, attrs)
    det = Cls(prefix=f"{prefix}:", name=device_name, labels={"xrf_detectors"})
    # Verify it is connection
    try:
        await await_for_connection(det)
    except TimeoutError as exc:
        msg = f"Could not connect to fluorescence detector: {device_name} ({prefix}:)"
        log.warning(msg)
    else:
        log.info(f"Created fluorescence detecotr: {device_name} ({prefix})")
        registry.register(det)
        return det


def load_fluorescence_detector_coros(config=None):
    # Get the detector definitions from config files
    if config is None:
        config = load_config()
    for name, cfg in config.get("fluorescence_detector", {}).items():
        if "prefix" not in cfg.keys():
            continue
        # Build the detector device
        if cfg["electronics"] == "dxp":
            yield make_dxp_device(
                device_name=name,
                prefix=cfg["prefix"],
                num_elements=cfg["num_elements"],
            )
        else:
            msg = f"Electronics '{cfg['electronics']}' for {name} not supported."
            raise exceptions.UnknownDeviceConfiguration(msg)


def load_fluorescence_detectors(config=None):
    asyncio.run(aload_devices(*load_fluorescence_detector_coros(config=config)))
