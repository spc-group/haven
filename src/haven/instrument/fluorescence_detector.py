"""Support tools useful to all fluorescence detectors.

Device specific support can be found in the module for the specific
hardware, e.g. ``dxp.py`` for XIA's XMAP, Mercury, Saturn, and
``xspress.py`` for Quantum Detectors's Xspress3 and Xspress3 mini.

"""

from enum import IntEnum
from collections import OrderedDict
from typing import Optional, Sequence
from contextlib import contextmanager
import warnings
import logging
import asyncio
import time

import numpy as np
from ophyd import (
    mca,
    Device,
    EpicsSignal,
    EpicsSignalRO,
    Component as Cpt,
    DynamicDeviceComponent as DDC,
    Kind,
    Signal,
    flyers,
)
from ophyd.signal import InternalSignal
from ophyd.areadetector.plugins import NetCDFPlugin_V34
from ophyd.status import SubscriptionStatus, StatusBase
from apstools.utils import cleanupText
from pcdsdevices.signal import MultiDerivedSignal, MultiDerivedSignalRO
from pcdsdevices.type_hints import SignalToValue, OphydDataType

from .scaler_triggered import ScalerTriggered
from .instrument_registry import registry
from .device import RegexComponent as RECpt, await_for_connection, aload_devices, make_device
from .._iconfig import load_config
from .. import exceptions


__all__ = ["DxpDetectorBase", "load_fluorescence_detectors"]


log = logging.getLogger(__name__)


active_kind = Kind.normal | Kind.config


class ROISumSignal(InternalSignal):
    """Like an InternalSignal, but compatible with DynamicDeviceComponent."""
    def __init__(self, roi_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        device = self.parent.parent
        self.root_device = device
        self.roi_num = int(roi_name.split(":")[-1])
        # Watch for changes to ROI values to compute new sums
        for roi in self._roi_signals():
            roi.net_count.subscribe(self._update_roi_sum)

    def _roi_signals(self):
        signals = []
        for mca in self.root_device.mca_records():
            roi = getattr(mca.rois, f"roi{self.roi_num}")
            signals.append(roi)
        return signals

    def _update_roi_sum(self, *args, value, **kwargs):
        rois = self._roi_signals()
        total = np.sum([roi.net_count.get() for roi in rois])
        self.put(total, internal=True)


def add_roi_sums(mcas, rois):
    """Add a set of signals to sum the ROI over all elements."""
    defn = OrderedDict()
    for roi in rois:
        attr = f"roi{roi}"
        defn[attr] = (
            ROISumSignal,
            roi,
            {},
        )
    return defn


class MCASumMixin(Device):
    """Adds a signal that reports the sum of the *spectrum* signal."""
    total_count = Cpt(InternalSignal, kind="normal")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Update the total count when the spectrum changes
        self.spectrum.subscribe(self._update_total_count)

    def _update_total_count(self, *args, old_value, value, **kwargs):
        # print(value)
        total = np.sum(value)
        self.total_count.put(total, internal=True)


class ROIMixin(Device):
    _original_name = None
    _original_kinds = {}
    _dynamic_hint_fields = ["net_count"]

    def stage(self):
        self._original_name = self.name
        # Append the ROI label to the signal name
        label = cleanupText(str(self.label.get()))
        old_name_base = self.name
        new_name_base = f"{self.name}_{label}"
        if label != "":
            self.name = new_name_base
        # Update the device name for children
        for walk in self.walk_signals():
            walk.item.name = walk.item.name.replace(old_name_base, new_name_base)
        # Set the kind based on the user-settable ".R0_BS_HINTED" PV
        if bool(self.use.get()):
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

    def _get_counts(self, mds: MultiDerivedSignalRO, items: SignalToValue) -> int:
        spectrum = items[self.parent.parent.spectrum]
        # Sometimes we get non-array spectra in here
        if not hasattr(spectrum, "shape"):
            return spectrum
        # Force the hi/lo boundaries to be within range
        hi = min(items[self.hi_chan], spectrum.shape[0])
        lo = max(items[self.lo_chan], 0)
        # Sum bins with the ROI range
        counts = np.sum(spectrum[lo:hi+1])
        counts = int(counts)
        if counts == 389:
            print(lo, hi, spectrum.shape)
        return counts

    count = Cpt(
        MultiDerivedSignalRO,
        attrs=["hi_chan", "lo_chan", "parent.parent.spectrum"],
        calculate_on_get=_get_counts,
    )        


class XRFMixin(Device):
    """Properties common to all XRF detectors."""

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
            elements = range(self.num_elements)

        for mca_num in elements:
            for roi_num in rois:
                roi = self.get_roi(mca_num, roi_num)
                status = roi.use.set(1)
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
            elements = range(1, self.num_elements)
        # Go through and set the hint on requested ROIs
        for mca_num in elements:
            for roi_num in rois:
                roi = self.get_roi(mca_num, roi_num)
                status = roi.use.set(0)
                statuses.append(status)
        return statuses

    def get_roi(self, mca_num: int, roi_num: int):
        """Get a specific ROI component based on
        its MCA number and then the ROI number.
        """
        mca = getattr(self.mcas, f"mca{mca_num}")
        roi = getattr(mca.rois, f"roi{roi_num}")
        return roi

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



