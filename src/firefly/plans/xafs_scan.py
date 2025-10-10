import logging
import re
from dataclasses import dataclass
from enum import IntEnum
from functools import partial
from typing import Any

import xraydb
from bluesky_queueserver_api import BPlan
from qasync import asyncSlot
from qtpy.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QMessageBox,
    QSizePolicy,
    QWidget,
)
from xraydb.xraydb import XrayDB

from firefly.exceptions import UnknownAbsorptionEdge
from firefly.plans import display
from firefly.plans.regions import RegionsManager
from haven.energy_ranges import (
    ERange,
    KRange,
    energy_to_wavenumber,
    merge_ranges,
    wavenumber_to_energy,
)

log = logging.getLogger(__name__)


class Domain(IntEnum):
    ENERGY = 0
    WAVENUMBER = 1


class XafsRegionsManager(RegionsManager):
    energy_suffix = "eV"
    wavenumber_suffix = "Å⁻"
    energy_precision = 1
    wavenumber_precision = 4

    @dataclass(frozen=True)
    class WidgetSet:
        active_checkbox: QCheckBox
        start_spin_box: QDoubleSpinBox
        stop_spin_box: QDoubleSpinBox
        step_spin_box: QDoubleSpinBox
        exposure_time_spin_box: QDoubleSpinBox
        k_space_checkbox: QCheckBox
        weight_spin_box: QDoubleSpinBox

    @dataclass(frozen=True, eq=True)
    class Region:
        is_active: bool
        start: float
        stop: float
        step: float
        exposure_time: float
        domain: Domain
        weight: float

        @property
        def energy_range(self):
            if self.domain == Domain.WAVENUMBER:
                return KRange(
                    self.start, self.stop, self.step, self.exposure_time, self.weight
                )
            else:
                return ERange(self.start, self.stop, self.step, self.exposure_time)

    async def add_row(self):
        row = await super().add_row()
        self.set_domain(Domain.ENERGY, row=row)

    async def create_row_widgets(self, row: int) -> list[QWidget]:
        """Create the widgets that are to go in each row, in order."""
        start_spin_box = QDoubleSpinBox()
        stop_spin_box = QDoubleSpinBox()
        step_spin_box = QDoubleSpinBox()
        # Apply hints to number
        exposure_time_spin_box = QDoubleSpinBox()
        exposure_time_spin_box.setValue(1.0)
        exposure_time_spin_box.setSuffix(" s")
        # For converting between k and E space
        k_space_checkbox = QCheckBox()
        k_space_checkbox.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        k_space_checkbox.setEnabled(True)
        # Weight factor box
        weight_spin_box = QDoubleSpinBox()
        weight_spin_box.setDecimals(1)
        weight_spin_box.setEnabled(False)

        # Apply validation criteria
        for spinbox in [start_spin_box, stop_spin_box, step_spin_box]:
            spinbox.setMinimum(float("-inf"))
            spinbox.setMaximum(float("inf"))
            spinbox.setStepType(spinbox.AdaptiveDecimalStepType)
            spinbox.setDecimals(self.energy_precision)

        # Connect the k-space enabled checkbox to the relevant signals
        k_space_checkbox.stateChanged.connect(
            partial(self.update_wavenumber_energy, row=row)
        )
        # Notify clients when the widgets change
        start_spin_box.valueChanged.connect(self.regions_changed)
        stop_spin_box.valueChanged.connect(self.regions_changed)
        step_spin_box.valueChanged.connect(self.regions_changed)
        exposure_time_spin_box.valueChanged.connect(self.regions_changed)
        k_space_checkbox.stateChanged.connect(self.regions_changed)
        weight_spin_box.valueChanged.connect(self.regions_changed)
        return [
            start_spin_box,
            stop_spin_box,
            step_spin_box,
            exposure_time_spin_box,
            k_space_checkbox,
            weight_spin_box,
        ]

    def widgets_to_region(self, widgets: WidgetSet) -> Region:
        """Take a list of widgets in a row, and build a Region object."""
        return self.Region(
            is_active=widgets.active_checkbox.isChecked(),
            start=widgets.start_spin_box.value(),
            stop=widgets.stop_spin_box.value(),
            step=widgets.step_spin_box.value(),
            exposure_time=widgets.exposure_time_spin_box.value(),
            domain=widgets.k_space_checkbox.isChecked(),
            weight=widgets.weight_spin_box.value(),
        )

    def enable_row_widgets(self, enabled: bool, *, row: int):
        """Enable/disable the widgets in a row of the layout.

        Excludes the checkbox used to enable/disable the rest of the
        row.

        """
        super().enable_row_widgets(enabled=enabled, row=row)
        # Weight spin box should respect the previous k-space decision
        widgets = self.row_widgets(row=row)
        if enabled:
            widgets.weight_spin_box.setEnabled(widgets.k_space_checkbox.isChecked())

    def set_domain(self, domain: Domain, *, row: int):
        """Set up the UI to be in either energy (eV) or wavenumber (Å⁻) units."""
        widgets = self.row_widgets(row)
        double_widgets = [
            widgets.start_spin_box,
            widgets.stop_spin_box,
            widgets.step_spin_box,
        ]
        suffix = (
            self.wavenumber_suffix
            if domain == Domain.WAVENUMBER
            else self.energy_suffix
        )
        for widget in double_widgets:
            widget.setSuffix(f" {suffix}")
        # Disable weight box when k is not selected
        widgets.weight_spin_box.setEnabled(domain == Domain.WAVENUMBER)

    def update_wavenumber_energy(self, is_k_checked: bool, row: int):
        domain = Domain.WAVENUMBER if is_k_checked else Domain.ENERGY
        self.set_domain(domain, row=row)
        # Define conversion functions
        widgets = self.row_widgets(row=row)
        spin_boxes = [
            widgets.start_spin_box,
            widgets.stop_spin_box,
            widgets.step_spin_box,
        ]
        start, stop, step = [widget.value() for widget in spin_boxes]
        if is_k_checked:
            convert = energy_to_wavenumber
        else:
            convert = wavenumber_to_energy
        # Set new values
        new_start, new_stop = convert(start), convert(stop)
        new_step = convert(start + step, relative_to=start)
        precision = self.wavenumber_precision if is_k_checked else self.energy_precision
        for widget in spin_boxes:
            widget.setDecimals(precision)
        widgets.start_spin_box.setValue(new_start)
        widgets.stop_spin_box.setValue(new_stop)
        widgets.step_spin_box.setValue(new_step)

    def apply_E0(self, E0: float):
        """Apply an energy offset correction, *E0*, to widgets.

        Effectively, converts from absolute to relative regions.

        """
        for row in self.row_numbers:
            widgets = self.row_widgets(row=row)
            widgets.k_space_checkbox.setEnabled(True)
            # Un-check k-space to convert back to energy from wavenumber
            widgets.k_space_checkbox.setChecked(False)
            # Convert between absolute energies and relative energies
            for line_edit in [widgets.start_spin_box, widgets.stop_spin_box]:
                old_value = line_edit.value()
                new_value = old_value - E0
                line_edit.setValue(new_value)

    def unapply_E0(self, E0: float):
        """Remove an E0 correction.

        Effectively, converts from relative to absolute regions.

        """
        for row in self.row_numbers:
            widgets = self.row_widgets(row=row)
            # Un-check k-space to convert back to energy from wavenumber
            widgets.k_space_checkbox.setEnabled(False)
            # Convert between absolute energies and relative energies
            for line_edit in [widgets.start_spin_box, widgets.stop_spin_box]:
                old_value = line_edit.value()
                new_value = old_value + E0
                line_edit.setValue(new_value)


class XafsScanDisplay(display.PlanDisplay):
    plan_type = "xafs_scan"
    min_energy = 4000
    max_energy = 33000
    _default_region_count = 3

    def customize_ui(self):
        super().customize_ui()
        self.regions = XafsRegionsManager(layout=self.regions_layout)
        self.regions.regions_changed.connect(self.update_total_time)
        self.num_regions_spin_box.valueChanged.connect(self.regions.set_region_count)
        self.num_regions_spin_box.setValue(self._default_region_count)
        self.enable_all_checkbox.stateChanged.connect(self.regions.enable_all_rows)
        # Disable the line edits in spin box (use up/down buttons instead)
        self.ui.num_regions_spin_box.lineEdit().setReadOnly(True)
        # Add absorption edges from XrayDB
        self.xraydb = XrayDB()
        combo_box = self.ui.edge_combo_box
        combo_box.lineEdit().setPlaceholderText("Select edge…")
        ltab = self.xraydb.tables["xray_levels"]
        edges = self.xraydb.query(ltab)
        edges = edges.filter(
            ltab.c.absorption_edge < self.max_energy,
            ltab.c.absorption_edge > self.min_energy,
        )
        for edge in edges:
            text = (
                f"{edge.element} {edge.iupac_symbol} ({int(edge.absorption_edge)} eV)"
            )
            combo_box.addItem(text, userData=edge)
        combo_box.setCurrentText("")
        # Connect signals for updates
        self.scan_time_changed.connect(self.scan_duration_label.set_seconds)
        self.total_time_changed.connect(self.total_duration_label.set_seconds)
        self.use_edge_checkbox.stateChanged.connect(self.use_edge)
        self.num_regions_spin_box.lineEdit().setReadOnly(True)
        self.num_regions_spin_box.valueChanged.connect(self.regions.set_region_count)
        self.spinBox_repeat_scan_num.valueChanged.connect(self.update_total_time)

    async def update_devices(self, registry):
        """Set available components in the device list."""
        await super().update_devices(registry)
        await self.detectors_list.update_devices(registry)

    def use_edge(self, is_checked: bool):
        self.edge_combo_box.setEnabled(is_checked)
        # Update regions
        if self.E0 is None:
            return
        elif is_checked:
            self.regions.apply_E0(self.E0)
        else:
            self.regions.unapply_E0(self.E0)

    def scan_durations(self, detector_time: float = 0) -> tuple[float, float]:
        energy_ranges = [
            region.energy_range for region in self.regions if region.is_active
        ]
        _, exposures = merge_ranges(*energy_ranges, sort=True)
        time_per_scan = sum(exposures)
        num_scan_repeat = self.ui.spinBox_repeat_scan_num.value()
        total_time = num_scan_repeat * time_per_scan
        return time_per_scan, total_time

    @asyncSlot()
    async def update_total_time(self):
        """Summing total_time for all checked regions."""
        try:
            time_per_scan, total_time = self.scan_durations()
        except ZeroDivisionError:
            time_per_scan, total_time = float("nan"), float("nan")
        self.scan_time_changed.emit(time_per_scan)
        self.total_time_changed.emit(total_time)

    @property
    def edge_name(self) -> str:
        edge_regex = r"([A-Z][a-z]?)[-_ ]([K-Z][0-9]*)"
        edge_text = self.ui.edge_combo_box.currentText()
        if re_match := re.search(edge_regex, edge_text):
            return "-".join(re_match.groups())
        else:
            return ""

    @property
    def E0(self) -> float | None:
        try:
            element, edge = self.edge_name.split("-")
        except (UnknownAbsorptionEdge, ValueError):
            pass
        else:
            return xraydb.xray_edge(element, edge).energy
        # Try and parse as a number
        edge_text = self.ui.edge_combo_box.currentText()
        try:
            return float(edge_text)
        except ValueError:
            return None

    def plan_args(self) -> tuple[tuple, dict]:
        """Build the arguments that will be used when building a plan object."""
        detectors = self.ui.detectors_list.selected_detectors()
        detector_names = [detector.name for detector in detectors]
        regions = [region for region in self.regions if region.is_active]
        energy_ranges = [region.energy_range.astuple() for region in regions]
        E0 = self.edge_name if self.edge_name != "" else self.E0
        # Additional metadata
        md = {**self.plan_metadata()}
        args = (detector_names, *energy_ranges)
        kwargs: dict[str, Any] = {
            "md": md,
        }
        if self.use_edge_checkbox.isChecked():
            kwargs["E0"] = E0
        return args, kwargs

    def queue_plan(self, *args, **kwargs) -> BPlan:
        # Fail if no energy is selected
        use_edge = self.use_edge_checkbox.isChecked()
        if use_edge and self.E0 is None:
            # Check that an absorption edge was selected
            if self.E0 is None:
                QMessageBox.warning(self, "Error", "Please select an absorption edge.")
                raise ValueError(
                    "Absorption edge is selected, but no valid value was provided."
                )
        super().queue_plan(*args, **kwargs)

    def ui_filename(self):
        return "plans/xafs_scan.ui"


# -----------------------------------------------------------------------------
# :author:    Juanjuan Huang
# :email:     juanjuan.huang@anl.gov
# :copyright: Copyright © 2024, UChicago Argonne, LLC
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
