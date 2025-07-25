import logging
import re
from enum import IntEnum

import xraydb
from qtpy import QtWidgets
from qtpy.QtWidgets import QSizePolicy
from xraydb.xraydb import XrayDB

from firefly.exceptions import UnknownAbsorptionEdge
from firefly.plans import regions_display
from haven.energy_ranges import (
    EnergyRange,
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


class XafsScanRegion(regions_display.RegionBase):
    energy_suffix = "eV"
    wavenumber_suffix = "Å⁻"
    energy_precision = 1
    wavenumber_precision = 4

    def setup_ui(self):

        # Enable checkbox
        self.region_checkbox = QtWidgets.QCheckBox()
        self.region_checkbox.setChecked(True)
        self.layout.addWidget(self.region_checkbox, self.row, 0)

        # First energy box
        self.start_spin_box = QtWidgets.QDoubleSpinBox()
        self.layout.addWidget(self.start_spin_box, self.row, 1)
        # Last energy box
        self.stop_spin_box = QtWidgets.QDoubleSpinBox()
        self.layout.addWidget(self.stop_spin_box, self.row, 2)
        # Energy step box
        self.step_spin_box = QtWidgets.QDoubleSpinBox()
        self.layout.addWidget(self.step_spin_box, self.row, 3)
        # Apply hints to number
        self.set_domain(Domain.ENERGY)

        # Exposure time double spin box
        self.exposure_time_spinbox = QtWidgets.QDoubleSpinBox()
        self.exposure_time_spinbox.setValue(1.0)
        self.exposure_time_spinbox.setSuffix(" s")
        self.layout.addWidget(self.exposure_time_spinbox, self.row, 4)

        # K-space checkbox
        self.k_space_checkbox = QtWidgets.QCheckBox()
        self.k_space_checkbox.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.k_space_checkbox.setEnabled(True)
        self.layout.addWidget(self.k_space_checkbox, self.row, 5)

        # Weight factor box
        self.weight_spinbox = QtWidgets.QDoubleSpinBox()
        self.layout.addWidget(self.weight_spinbox, self.row, 6)
        self.weight_spinbox.setDecimals(1)
        self.weight_spinbox.setEnabled(False)

        # Apply validation criteria
        for spinbox in [self.start_spin_box, self.stop_spin_box, self.step_spin_box]:
            spinbox.setMinimum(float("-inf"))
            spinbox.setMaximum(float("inf"))
            spinbox.setStepType(spinbox.AdaptiveDecimalStepType)
            spinbox.setDecimals(self.energy_precision)

        # Connect the k-space enabled checkbox to the relevant signals
        self.k_space_checkbox.stateChanged.connect(self.update_wavenumber_energy)
        # Disable/enable regions when selected
        self.region_checkbox.stateChanged.connect(self.enable)

    def enable(self, is_checked: bool):
        self.start_spin_box.setEnabled(is_checked)
        self.stop_spin_box.setEnabled(is_checked)
        self.step_spin_box.setEnabled(is_checked)
        self.exposure_time_spinbox.setEnabled(is_checked)
        self.weight_spinbox.setEnabled(is_checked)
        self.k_space_checkbox.setEnabled(is_checked)

    def remove(self):
        widgets = [
            self.region_checkbox,
            self.start_spin_box,
            self.stop_spin_box,
            self.step_spin_box,
            self.exposure_time_spinbox,
            self.k_space_checkbox,
            self.weight_spinbox,
        ]
        for widget in widgets:
            self.layout.removeWidget(widget)
            widget.deleteLater()

    def set_domain(self, domain: Domain):
        """Set up the UI to be in either energy (eV) or wavenumber (Å⁻) units."""
        double_widgets = [
            self.start_spin_box,
            self.stop_spin_box,
            self.step_spin_box,
        ]
        suffix = (
            self.wavenumber_suffix
            if domain == Domain.WAVENUMBER
            else self.energy_suffix
        )
        for widget in double_widgets:
            widget.setSuffix(f" {suffix}")

    def update_wavenumber_energy(self, is_k_checked: bool):
        domain = Domain.WAVENUMBER if is_k_checked else Domain.ENERGY
        self.set_domain(domain)
        # Disable weight box when k is not selected
        self.weight_spinbox.setEnabled(is_k_checked)

        # Define conversion functions
        line_edits = [self.start_spin_box, self.stop_spin_box, self.step_spin_box]
        start, stop, step = [widget.value() for widget in line_edits]
        if is_k_checked:
            convert = energy_to_wavenumber
        else:
            convert = wavenumber_to_energy
        # Set new values
        new_start, new_stop = convert(start), convert(stop)
        new_step = convert(start + step, relative_to=start)
        precision = self.wavenumber_precision if is_k_checked else self.energy_precision
        for widget in line_edits:
            widget.setDecimals(precision)
        self.start_spin_box.setValue(new_start)
        self.stop_spin_box.setValue(new_stop)
        self.step_spin_box.setValue(new_step)

    @property
    def energy_range(self) -> EnergyRange | None:
        weight = self.weight_spinbox.value()
        exposure_time = self.exposure_time_spinbox.value()
        # Prevent invalid inputs such as nan
        try:
            start = self.start_spin_box.value()
            stop = self.stop_spin_box.value()
            step = self.step_spin_box.value()
        # When the round doesn't work for nan values
        except ValueError as exc:
            log.exception(exc)
            return None
        if self.k_space_checkbox.isChecked():
            return KRange(start, stop, step, exposure=exposure_time, weight=weight)
        else:
            return ERange(start, stop, step, exposure=exposure_time)

    def apply_E0(self, E0: float):
        """Apply an E0 correction.

        Effectively, converts from absolute to relative regions.

        """
        self.k_space_checkbox.setEnabled(True)
        # Un-check k-space to convert back to energy from wavenumber
        self.k_space_checkbox.setChecked(False)
        # Convert between absolute energies and relative energies
        for line_edit in [self.start_spin_box, self.stop_spin_box]:
            old_value = line_edit.value()
            new_value = old_value - E0
            line_edit.setValue(new_value)

    def unapply_E0(self, E0: float):
        """Remove an E0 correction.

        Effectively, converts from relative to absolute regions.

        """
        self.k_space_checkbox.setEnabled(False)
        # Un-check k-space to convert back to energy from wavenumber
        self.k_space_checkbox.setChecked(False)
        # Convert between absolute energies and relative energies
        for line_edit in [self.start_spin_box, self.stop_spin_box]:
            old_value = line_edit.value()
            new_value = old_value + E0
            line_edit.setValue(new_value)


class XafsScanDisplay(regions_display.RegionsDisplay):
    Region = XafsScanRegion
    default_num_regions = 3
    plan_type = "xafs_scan"
    min_energy = 4000
    max_energy = 33000

    def customize_ui(self):
        super().customize_ui()
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

        # Connect signals for total time updates
        self.scan_time_changed.connect(self.scan_duration_label.set_seconds)
        self.total_time_changed.connect(self.total_duration_label.set_seconds)

        # Connect the E0 checkbox to the E0 combobox
        self.ui.use_edge_checkbox.stateChanged.connect(self.use_edge)

        # disable the line edits in spin box
        self.ui.num_regions_spin_box.lineEdit().setReadOnly(True)

        # when regions number changed
        self.ui.num_regions_spin_box.valueChanged.connect(self.update_regions)
        self.ui.num_regions_spin_box.editingFinished.connect(self.update_regions)

        # reset button
        self.ui.reset_button.clicked.connect(self.reset_default_regions)

        # connect checkboxes with all regions' check box
        self.ui.regions_all_checkbox.stateChanged.connect(self.on_regions_all_checkbox)
        # connect is_standard with a warning box
        self.ui.checkBox_is_standard.clicked.connect(self.on_is_standard)

        # repeat scans
        self.ui.spinBox_repeat_scan_num.valueChanged.connect(self.update_total_time)
        self.ui.detectors_list.selectionModel().selectionChanged.connect(
            self.update_total_time
        )

        # Default metadata values
        self.ui.comboBox_purpose.lineEdit().setPlaceholderText(
            "e.g. commissioning, alignment, etc."
        )
        self.ui.comboBox_purpose.setCurrentText("")

    def on_regions_all_checkbox(self, is_checked):
        for region_i in self.regions:
            region_i.region_checkbox.setChecked(is_checked)

    def use_edge(self, is_checked: bool):
        self.edge_combo_box.setEnabled(is_checked)
        # Update regions
        for region in self.regions:
            if self.E0 is None:
                return
            elif is_checked:
                region.apply_E0(self.E0)
            else:
                region.unapply_E0(self.E0)

    def reset_default_regions(self):
        super().reset_default_regions()
        self.ui.spinBox_repeat_scan_num.setValue(1)
        # Set default ranges for EXAFS scans
        pre_edge = [-200, -50, 5]
        xanes_region = [-50, 50, 0.5]
        exafs_region = [50, 800, 0.5]

        default_regions = [pre_edge, xanes_region, exafs_region]
        for (start, stop, step), region in zip(default_regions, self.regions):
            region.start_spin_box.setValue(start)
            region.stop_spin_box.setValue(stop)
            region.step_spin_box.setValue(step)

    def add_region(self):
        region = super().add_region()
        # Connect some extra signals
        for signal in [
            region.region_checkbox.stateChanged,
            region.step_spin_box.valueChanged,
            region.weight_spinbox.valueChanged,
            region.exposure_time_spinbox.valueChanged,
            region.k_space_checkbox.stateChanged,
        ]:
            signal.connect(self.update_total_time)
        return signal

    def update_regions(self):
        new_region_num = self.ui.num_regions_spin_box.value()
        old_region_num = len(self.regions)

        for i in range(old_region_num, new_region_num):
            self.add_region()
        for i in range(new_region_num, old_region_num):
            self.remove_region()

        self.update_total_time()

    def update_total_time(self):
        # Summing total_time for all checked regions directly within the sum function using a generator expression
        energy_ranges = [
            region.energy_range
            for region in self.regions
            if region.region_checkbox.isChecked()
        ]
        try:
            _, exposures = merge_ranges(*energy_ranges, sort=True)
            time_per_scan = exposures.sum()
        except (ValueError, ZeroDivisionError, OverflowError):
            time_per_scan = float("nan")
        repetitions = self.ui.spinBox_repeat_scan_num.value()
        total_time = time_per_scan * repetitions
        self.scan_time_changed.emit(time_per_scan)
        self.total_time_changed.emit(total_time)

    def on_is_standard(self, is_checked):
        # if is_standard checked, warn that the data will be used for public
        if is_checked:
            response = QtWidgets.QMessageBox.warning(
                self,
                "Notice",
                "When checking this option, you acknowledge that these data may be made publicly available.",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if response != QtWidgets.QMessageBox.Yes:
                self.ui.checkBox_is_standard.setChecked(False)

    @property
    def edge_name(self) -> str | None:
        edge_regex = r"([A-Z][a-z]?)[-_ ]([K-Z][0-9]*)"
        edge_text = self.ui.edge_combo_box.currentText()
        if re_match := re.search(edge_regex, edge_text):
            return "-".join(re_match.groups())
        else:
            return None

    @property
    def E0(self) -> float | None:
        try:
            element, edge = self.edge_name.split("-")
        except (UnknownAbsorptionEdge, AttributeError):
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
        # Iterate through only selected regions
        checked_regions = [
            region_i
            for region_i in self.regions
            if region_i.region_checkbox.isChecked()
        ]
        energy_ranges = [region.energy_range.astuple() for region in checked_regions]
        # Edge position
        E0 = self.edge_name if self.edge_name is not None else self.E0
        # Additional metadata
        md = self.get_meta_data()
        md["is_standard"] = self.ui.checkBox_is_standard.isChecked()
        args = (detector_names, *energy_ranges)
        kwargs = {
            "md": md,
        }
        if self.use_edge_checkbox.isChecked():
            # Check that an absorption edge was selected
            if E0 is None:
                QtWidgets.QMessageBox.warning(
                    self, "Error", "Please select an absorption edge."
                )
                raise ValueError(
                    "Absorption edge is selected, but no valid value was provided."
                )
            kwargs["E0"] = E0
        return args, kwargs

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
