"""Support tools useful to all fluorescence detectors.

Device specific support can be found in the module for the specific
hardware, e.g. ``dxp.py`` for XIA's XMAP, Mercury, Saturn, and
``xspress.py`` for Quantum Detectors's Xspress3 and Xspress3 mini.

"""

import logging
from collections import OrderedDict
from typing import Optional, Sequence

import numpy as np

# from apstools.utils import cleanupText
from ophyd import Component as Cpt
from ophyd import Device, Kind
from ophyd.signal import DerivedSignal, InternalSignal

__all__ = ["XRFMixin"]


log = logging.getLogger(__name__)


active_kind = Kind.normal | Kind.config


class ROISum(Device):
    """Sums an ROI across multiple elements."""

    count = Cpt(InternalSignal, name="count")
    net_count = Cpt(InternalSignal, name="net_count")

    def __init__(self, suffix, *args, **kwargs):
        super().__init__(suffix, *args, **kwargs)
        device = self.parent.parent
        self.root_device = device
        self.roi_num = int(suffix.split(":")[-1].strip("roi"))
        # self.roi_num = int(roi_name.split(":")[-1])
        # Watch for changes to ROI values to compute new sums
        for roi in self._roi_signals():
            roi.count.subscribe(self._update_roi_total)
            roi.net_count.subscribe(self._update_roi_net)

    def _roi_signals(self):
        signals = []
        for mca in self.root_device.mca_records():
            roi = getattr(mca.rois, f"roi{self.roi_num}")
            signals.append(roi)
        return signals

    def _update_roi_total(self, *args, value, **kwargs):
        rois = self._roi_signals()
        total = np.sum([roi.count.get() for roi in rois])
        self.count.put(total, internal=True)

    def _update_roi_net(self, *args, value, **kwargs):
        rois = self._roi_signals()
        net = np.sum([roi.net_count.get() for roi in rois])
        self.net_count.put(net, internal=True)


def add_roi_sums(mcas, rois):
    """Add a set of signals to sum the ROI over all elements."""
    defn = OrderedDict()
    for roi in rois:
        attr = f"roi{roi}"
        defn[attr] = (
            ROISum,
            f"roi{roi}",
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
        total = int(np.sum(value))
        self.total_count.put(total, internal=True)


class UseROISignal(DerivedSignal):
    """Check that the ``.use`` ROI signal properly mangles the label.

    It uses label mangling instead of any underlying PVs because
    different detector types don't have this feature or use it in an
    undesirable way.

    """

    sentinel_char = "~"

    def inverse(self, value):
        """Compute original signal value -> derived signal value"""
        try:
            disabled = value.startswith(self.sentinel_char)
        except AttributeError:
            disabled = True
        return not disabled

    def forward(self, value):
        """Compute derived signal value -> original signal value"""
        label = str(self._derived_from.get()).strip(self.sentinel_char)
        disable_roi = not bool(value)
        if disable_roi:
            label = f"{self.sentinel_char}{label}"
        return label


class ROIMixin(Device):
    _original_name = None
    _original_kinds = {}
    _dynamic_hint_fields = ["count"]

    def stage(self):
        self._original_name = self.name
        # Append the ROI label to the signal name
        label = str(self.label.get()).strip("~")
        label = label.encode("ascii", "replace").decode("ascii")
        old_name_base = self.name
        new_name_base = f"{self.name}_{label}"

        if label != "":
            log.debug(
                f"Mangling ROI label '{self.label.get()}' -> "
                f"'{label}' ('{new_name_base}')"
            )
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
        return super().stage()

    def unstage(self):
        # Restore the original (pre-staged) name
        if self.name != self._original_name:
            for walk in self.walk_signals():
                if self._original_name is not None:
                    walk.item.name = walk.item.name.replace(
                        self.name, self._original_name
                    )
            self.name = self._original_name
        # Restore original signal kinds
        for fld, kind in self._original_kinds.items():
            getattr(self, fld).kind = kind
        super().unstage()


class XRFMixin(Device):
    """Properties common to all XRF detectors."""

    total_count = Cpt(InternalSignal, kind=active_kind)
    _mca_count_cache: dict

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mca_count_cache = {}
        # Monitor the individual MCAs to keep track of their sums
        for mca in self.mca_records():
            mca.total_count.subscribe(self._update_total_count)

    def _update_total_count(self, *args, obj, value, timestamp, **kwargs):
        """Callback for summing the total counts across all MCAs."""
        # Update caches values
        self._mca_count_cache[obj] = value
        # Calculate new sum
        new_total = sum(self._mca_count_cache.values())
        self.total_count.put(new_total, internal=True, timestamp=timestamp)

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


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2023, UChicago Argonne, LLC
#
# Distributed under the terms of the 3-Clause BSD License
#
# The full license is in the file LICENSE, distributed with this software.
#
# DISCLAIMER
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# -----------------------------------------------------------------------------
