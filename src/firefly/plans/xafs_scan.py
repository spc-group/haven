import logging
import re

import xraydb
from bluesky_queueserver_api import BPlan
from qtpy import QtWidgets
from qtpy.QtCore import QObject, Signal
from qtpy.QtGui import QDoubleValidator
from xraydb.xraydb import XrayDB

from firefly.exceptions import UnknownAbsorptionEdge
from firefly.plans import regions_display
from haven.energy_ranges import (
    E_step_to_k_step,
    ERange,
    KRange,
    energy_to_wavenumber,
    k_step_to_E_step,
    merge_ranges,
    wavenumber_to_energy,
)

log = logging.getLogger(__name__)

# How much rounding to do when convert energy to k-space
float_accuracy = 4


# The energy resolution will not be better than 0.01 eV at S25
# e.g. 0.01 eV / 4000 eV -> 10^-6 level, Si(311) is 10-5 level
def wavenumber_to_energy_round(wavenumber):
    return round(wavenumber_to_energy(wavenumber), 2)


def k_step_to_E_step_round(k_start, k_step):
    return round(k_step_to_E_step(k_start, k_step), 2)


class TitleRegion:
    def __init__(self):
        self.setup_ui()

    def setup_ui(self):
        self.layout = QtWidgets.QHBoxLayout()

        # Enable checkbox
        self.regions_all_checkbox = QtWidgets.QCheckBox()
        self.regions_all_checkbox.setChecked(True)
        self.regions_all_checkbox.setFixedWidth(15)

        self.layout.addWidget(self.regions_all_checkbox)

        labels = ["Start", "Stop", "Step", "Weight", "", "Exposure [s]"]
        Qlabels_all = {}
        for label_i in labels:
            Qlabel_i = QtWidgets.QLabel(label_i)
            self.layout.addWidget(Qlabel_i)
            Qlabels_all[label_i] = Qlabel_i

        # fix widths so the labels are aligned with XafsRegions
        Qlabels_all["Weight"].setFixedWidth(57)
        Qlabels_all[""].setFixedWidth(57)
        Qlabels_all["Exposure [s]"].setFixedWidth(68)


class XafsScanRegion(QObject):
    time_calculation_signal = Signal()
    # Flag for whether time is calculated correctly, if not, will set to -1
    xafs_region_time: int = 0

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        self.layout = QtWidgets.QHBoxLayout()

        # Enable checkbox
        self.region_checkbox = QtWidgets.QCheckBox()
        self.region_checkbox.setChecked(True)
        self.layout.addWidget(self.region_checkbox)

        # First energy box
        self.start_line_edit = QtWidgets.QLineEdit()
        self.start_line_edit.setValidator(QDoubleValidator())  # only takes floats
        self.start_line_edit.setPlaceholderText("Start…")
        self.layout.addWidget(self.start_line_edit)

        # Last energy box
        self.stop_line_edit = QtWidgets.QLineEdit()
        self.stop_line_edit.setValidator(QDoubleValidator())  # only takes floats
        self.stop_line_edit.setPlaceholderText("Stop…")
        self.layout.addWidget(self.stop_line_edit)

        # Energy step box
        self.step_line_edit = QtWidgets.QLineEdit()
        self.step_line_edit.setValidator(
            QDoubleValidator(0.0, float("inf"), 2)  # the step is always bigger than 0
        )
        # only takes positive floats
        self.step_line_edit.setPlaceholderText("Step…")
        self.layout.addWidget(self.step_line_edit)

        # Weight factor box
        self.weight_spinbox = QtWidgets.QDoubleSpinBox()
        self.layout.addWidget(self.weight_spinbox)
        self.weight_spinbox.setDecimals(1)
        self.weight_spinbox.setEnabled(False)

        # K-space checkbox
        self.k_space_checkbox = QtWidgets.QCheckBox()
        self.k_space_checkbox.setText("k-space")
        self.k_space_checkbox.setEnabled(True)
        self.layout.addWidget(self.k_space_checkbox)

        # Exposure time double spin box
        self.exposure_time_spinbox = QtWidgets.QDoubleSpinBox()
        self.exposure_time_spinbox.setValue(1)
        self.layout.addWidget(self.exposure_time_spinbox)

        # Connect the k-space enabled checkbox to the relevant signals
        self.k_space_checkbox.stateChanged.connect(self.update_wavenumber_energy)

    def update_line_edit_value(self, line_edit, conversion_func):
        text = line_edit.text()
        if text:
            converted_value = conversion_func(round(float(text), float_accuracy))
            line_edit.setText(f"{converted_value:.6g}")

    def update_wavenumber_energy(self, is_k_checked):
        # disable weight box when k is not selected
        self.weight_spinbox.setEnabled(is_k_checked)

        # Define conversion functions
        conversion_funcs = {
            self.step_line_edit: (
                E_step_to_k_step
                if is_k_checked
                else lambda x, y: k_step_to_E_step_round(x, y)
            ),
            self.start_line_edit: (
                energy_to_wavenumber if is_k_checked else wavenumber_to_energy_round
            ),
            self.stop_line_edit: (
                energy_to_wavenumber if is_k_checked else wavenumber_to_energy_round
            ),
        }

        # Iterate over line edits and apply corresponding conversion
        for line_edit, func in conversion_funcs.items():
            # Special handling for step_line_edit due to different parameters needed
            if line_edit == self.step_line_edit:
                start_text = self.start_line_edit.text()
                if start_text and line_edit.text():
                    start = float(start_text)
                    step = float(line_edit.text())
                    new_values = (
                        func(start, step) if is_k_checked else func(start, step)
                    )
                    line_edit.setText(f"{new_values:.4g}")
            else:
                self.update_line_edit_value(line_edit, func)

    @property
    def energy_range(self):
        weight = self.weight_spinbox.value()
        exposure_time = self.exposure_time_spinbox.value()
        # Prevent invalid inputs such as nan
        try:
            start = round(float(self.start_line_edit.text()), float_accuracy)
            stop = round(float(self.stop_line_edit.text()), float_accuracy)
            step = round(float(self.step_line_edit.text()), float_accuracy)
        # When the round doesn't work for nan values
        except ValueError:
            self.kErange = []
            start, stop, step = float("nan"), float("nan"), float("nan")

        if self.k_space_checkbox.isChecked():
            return KRange(start, stop, step, exposure=exposure_time, weight=weight)
        else:
            return ERange(start, stop, step, exposure=exposure_time)


class XafsScanDisplay(regions_display.PlanDisplay):
    min_energy = 4000
    max_energy = 33000

    def customize_ui(self):
        super().customize_ui()
        # Remove the defaut XAFS layout from .ui file
        self.ui.clearLayout(self.ui.region_layout)

        # add title layout
        self.title_region = TitleRegion()
        self.ui.title_layout.addLayout(self.title_region.layout)

        self.reset_default_regions()
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

        # Connect the E0 checkbox to the E0 combobox
        self.ui.use_edge_checkbox.stateChanged.connect(self.use_edge)

        # disable the line edits in spin box
        self.ui.regions_spin_box.lineEdit().setReadOnly(True)

        # when regions number changed
        self.ui.regions_spin_box.valueChanged.connect(self.update_regions)
        self.ui.regions_spin_box.editingFinished.connect(self.update_regions)

        # reset button
        self.ui.reset_button.clicked.connect(self.reset_default_regions)

        # connect checkboxes with all regions' check box
        self.title_region.regions_all_checkbox.stateChanged.connect(
            self.on_regions_all_checkbox
        )
        # connect is_standard with a warning box
        self.ui.checkBox_is_standard.clicked.connect(self.on_is_standard)

        # repeat scans
        self.ui.spinBox_repeat_scan_num.valueChanged.connect(self.update_total_time)

        # Default metadata values
        self.ui.comboBox_purpose.lineEdit().setPlaceholderText(
            "e.g. commissioning, alignment…"
        )
        self.ui.comboBox_purpose.setCurrentText("")

    async def update_devices(self, registry):
        """Set available components in the device list."""
        await super().update_devices(registry)
        await self.ui.detectors_list.update_devices(registry)

    def on_region_checkbox(self):
        for region_i in self.regions:
            is_region_i_checked = region_i.region_checkbox.isChecked()
            region_i.start_line_edit.setEnabled(is_region_i_checked)
            region_i.stop_line_edit.setEnabled(is_region_i_checked)
            region_i.step_line_edit.setEnabled(is_region_i_checked)
            region_i.exposure_time_spinbox.setEnabled(is_region_i_checked)
            region_i.weight_spinbox.setEnabled(is_region_i_checked)
            if not self.use_edge_checkbox.isChecked():
                region_i.k_space_checkbox.setEnabled(False)
            else:
                region_i.k_space_checkbox.setEnabled(is_region_i_checked)

    def on_regions_all_checkbox(self, is_checked):
        for region_i in self.regions:
            region_i.region_checkbox.setChecked(is_checked)

    def use_edge(self, is_checked):
        self.edge_combo_box.setEnabled(is_checked)

        # extract edge values
        match = re.findall(r"\d+\.?\d*", self.edge_combo_box.currentText())
        edge_eV = round(float(match[-1]), float_accuracy) if match else 0

        # iterate through selected regions
        checked_regions = [
            region_i
            for region_i in self.regions
            if region_i.region_checkbox.isChecked()
        ]
        for region_i in checked_regions:
            # Adjust checkbox based on use_edge_checkbox state
            region_i.k_space_checkbox.setEnabled(is_checked)
            # uncheck k space to convert back to energy values from k values
            region_i.k_space_checkbox.setChecked(False)

            # Convert between absolute energies and relative energies
            for line_edit in [region_i.start_line_edit, region_i.stop_line_edit]:
                text = line_edit.text()
                if text:
                    value = (
                        round(float(text), float_accuracy) - edge_eV
                        if is_checked
                        else round(float(text), float_accuracy) + edge_eV
                    )
                    line_edit.setText(f"{value:.6g}")

    def clearLayout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

    def reset_default_regions(self):
        default_num_regions = 3

        if hasattr(self, "regions"):
            self.remove_regions(len(self.regions))
        self.regions = []
        self.add_regions(default_num_regions)
        self.ui.regions_spin_box.setValue(default_num_regions)

        # set default values for EXAFS scans
        pre_edge = [-200, -50, 5]
        xanes_region = [-50, 50, 0.5]
        exafs_region = [50, 800, 0.5]

        default_regions = [pre_edge, xanes_region, exafs_region]
        for i, region_i in enumerate(self.regions):
            region_i.start_line_edit.setText(str(default_regions[i][0]))
            region_i.stop_line_edit.setText(str(default_regions[i][1]))
            region_i.step_line_edit.setText(str(default_regions[i][2]))

        # reset scan repeat num to 1
        self.ui.spinBox_repeat_scan_num.setValue(1)

    def add_regions(self, num=1):
        for i in range(num):
            region = XafsScanRegion()
            self.ui.regions_layout.addLayout(region.layout)
            self.regions.append(region)
            # disable/enabale regions when selected
            region.region_checkbox.stateChanged.connect(self.on_region_checkbox)
            # Connect all signals to the update_total_time method
            for signal in [
                region.region_checkbox.stateChanged,
                region.start_line_edit.textChanged,
                region.stop_line_edit.textChanged,
                region.step_line_edit.textChanged,
                region.weight_spinbox.valueChanged,
                region.exposure_time_spinbox.valueChanged,
                region.k_space_checkbox.stateChanged,
            ]:
                signal.connect(self.update_total_time)

    def remove_regions(self, num=1):
        for i in range(num):
            layout = self.regions[-1].layout
            # iterate/wait, and delete all widgets in the layout in the end
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.regions.pop()

    def update_regions(self):
        new_region_num = self.ui.regions_spin_box.value()
        old_region_num = len(self.regions)
        diff_region_num = new_region_num - old_region_num

        if diff_region_num < 0:
            self.remove_regions(abs(diff_region_num))
        elif diff_region_num > 0:
            self.add_regions(diff_region_num)
        self.update_total_time()

    def update_total_time(self):
        # Summing total_time for all checked regions directly within the sum function using a generator expression
        energy_ranges = [
            region.energy_range
            for region in self.regions
            if region.region_checkbox.isChecked()
        ]

        # Keep end points from being smaller than start points
        try:
            _, exposures = merge_ranges(*energy_ranges, sort=True)
            total_time_per_scan = exposures.sum()
        except ValueError:
            total_time_per_scan = float("nan")

        self.set_time_label(total_time_per_scan)

    def on_is_standard(self, is_checked):
        # if is_standard checked, warn that the data will be used for public
        if is_checked:
            response = QtWidgets.QMessageBox.warning(
                self,
                "Notice",
                "When checking this option, this data will be used by public.",
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
    def E0(self):
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

    def queue_plan(self, *args, **kwargs):
        """Execute this plan on the queueserver."""
        # Get parameters from each rows of line regions:
        energy_ranges_all = []

        # Iterate through only selected regions
        checked_regions = [
            region_i
            for region_i in self.regions
            if region_i.region_checkbox.isChecked()
        ]
        energy_ranges = [region.energy_range for region in checked_regions]
        # Set up other plan arguments
        md = self.get_meta_data()
        md["is_standard"] = self.ui.checkBox_is_standard.isChecked()
        detectors, repeat_scan_num = self.get_scan_parameters()
        # Check that an absorption edge was selected
        if self.use_edge_checkbox.isChecked():
            edge = self.edge_name
            E0 = self.E0
            if edge is not None:
                E0_arg = edge
            elif E0 is not None:
                E0_arg = E0
            else:
                QtWidgets.QMessageBox.warning(
                    self, "Error", "Please select an absorption edge."
                )
                return None
        # Build the queue item
        item = BPlan(
            "xafs_scan",
            detectors,
            *energy_ranges,
            E0=E0_arg,
            md=md,
        )
        # Submit the item to the queueserver
        log.info("Adding XAFS scan to queue.")
        # Repeat scans
        for i in range(repeat_scan_num):
            self.queue_item_submitted.emit(item)

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
