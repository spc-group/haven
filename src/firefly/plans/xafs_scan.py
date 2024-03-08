import re

from qtpy import QtWidgets
from qtpy.QtGui import QDoubleValidator
from xraydb.xraydb import XrayDB

from firefly import display
from firefly.application import FireflyApplication
from haven.energy_ranges import (
    E_step_to_k_step,
    ERange,
    KRange,
    energy_to_wavenumber,
    k_step_to_E_step,
    merge_ranges,
    wavenumber_to_energy,
)
from haven.plans.energy_scan import energy_scan

# TODO: remove exposure time


class XafsScanRegion:
    def __init__(self):
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
        self.step_line_edit.setValidator(QDoubleValidator(0.0, float('inf'), 2))  # only takes positive floats
        self.step_line_edit.setPlaceholderText("Step…")
        self.layout.addWidget(self.step_line_edit)

        # Weight factor box
        self.weight_spinbox = QtWidgets.QDoubleSpinBox()
        self.layout.addWidget(self.weight_spinbox)
        self.weight_spinbox.setDecimals(1)

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
        self.region_checkbox.stateChanged.connect(self.disable_region)
    
    def disable_region(self, is_region_checked):
        self.start_line_edit.setEnabled(is_region_checked)
        self.stop_line_edit.setEnabled(is_region_checked)
        self.step_line_edit.setEnabled(is_region_checked)
        self.exposure_time_spinbox.setEnabled(is_region_checked)
        self.weight_spinbox.setEnabled(is_region_checked)
        self.k_space_checkbox.setEnabled(is_region_checked)

    def update_line_edit_value(self, line_edit, conversion_func):
        text = line_edit.text()
        if text:
            converted_value = conversion_func(float(text))
            line_edit.setText(f"{converted_value:.5g}")

    def update_wavenumber_energy(self):
        is_checked = self.k_space_checkbox.isChecked()

        # Define conversion functions
        conversion_funcs = {
            self.step_line_edit: E_step_to_k_step
            if is_checked
            else lambda x, y: k_step_to_E_step(x, y),
            self.start_line_edit: energy_to_wavenumber
            if is_checked
            else wavenumber_to_energy,
            self.stop_line_edit: energy_to_wavenumber
            if is_checked
            else wavenumber_to_energy,
        }

        # Iterate over line edits and apply corresponding conversion
        for line_edit, func in conversion_funcs.items():
            if line_edit == self.step_line_edit:
                # Special handling for step_line_edit due to different parameters needed
                start_text = self.start_line_edit.text()
                if start_text and line_edit.text():
                    start = float(start_text)
                    step = float(line_edit.text())
                    new_values = func(start, step) if is_checked else func(start, step)
                    line_edit.setText(f"{new_values:.4g}")
            else:
                self.update_line_edit_value(line_edit, func)


class XafsScanDisplay(display.FireflyDisplay):
    min_energy = 4000
    max_energy = 33000

    def customize_ui(self):
        # Remove the defaufdsadfsfdsfagafdsgalt XAFS layout from .ui file
        self.clearLayout(self.ui.region_layout)

        self.reset_default_regions()
        # add absorption edges from XrayDB
        self.xraydb = XrayDB()

        combo_box = self.ui.edge_combo_box
        ltab = self.xraydb.tables["xray_levels"]
        edges = self.xraydb.query(ltab)
        edges = edges.filter(
            ltab.c.absorption_edge < self.max_energy,
            ltab.c.absorption_edge > self.min_energy,
        )
        items = [
            f"{r.element} {r.iupac_symbol} ({int(r.absorption_edge)} eV)"
            for r in edges.all()
        ]
        combo_box.addItems(["Select edge…", *items])

        # Connect the E0 checkbox to the E0 combobox
        self.ui.use_edge_checkbox.stateChanged.connect(self.use_edge)

        # disable the line edits in spin box
        self.ui.regions_spin_box.lineEdit().setReadOnly(True)

        # when regions number changed
        self.ui.regions_spin_box.valueChanged.connect(self.update_regions)
        self.ui.regions_spin_box.editingFinished.connect(self.update_regions)

        # reset button
        self.ui.pushButton.clicked.connect(self.reset_default_regions)

        self.ui.run_button.setEnabled(True) #for testing
        self.ui.run_button.clicked.connect(self.queue_plan)        

    def use_edge(self):
        self.edge_combo_box.setEnabled(self.ui.use_edge_checkbox.isChecked())
        
        # extract edge values
        match = re.findall(r"\d+\.?\d*", self.edge_combo_box.currentText())
        edge_value = float(match[-1]) if match else 0

        is_checked = self.ui.use_edge_checkbox.isChecked()
        # iterate through selected regions
        checked_regions = [region_i for region_i in self.regions if region_i.region_checkbox.isChecked()]
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
                        float(text) - edge_value
                        if is_checked
                        else float(text) + edge_value
                    )
                    line_edit.setText(f"{value:.4g}")

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

        # set default values for testing, to be deleted in the future
        pre_edge = [-50, -20, 1]
        XANES_region = [-20, 50, 0.2]
        EXAFS_region = [50, 500, 0.5]
        default_regions = [pre_edge, XANES_region, EXAFS_region]
        for i, region_i in enumerate(self.regions):
            region_i.start_line_edit.setText(str(default_regions[i][0]))
            region_i.stop_line_edit.setText(str(default_regions[i][1]))
            region_i.step_line_edit.setText(str(default_regions[i][2]))


    def add_regions(self, num=1):
        for i in range(num):
            region = XafsScanRegion()
            self.ui.regions_layout.addLayout(region.layout)
            self.regions.append(region)

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

    def queue_plan(self, *args, **kwargs):
        """Execute this plan on the queueserver."""
        # get paramters from each rows of line regions:
        energy_ranges_all = []

        # iterate through only selected regions
        checked_regions = [region_i for region_i in self.regions if region_i.region_checkbox.isChecked()]
        for region_i in checked_regions:
            start = float(region_i.start_line_edit.text())
            stop = float(region_i.stop_line_edit.text())
            step = float(region_i.step_line_edit.text())
            weight = region_i.weight_spinbox.value()
            exposure_time = region_i.exposure_time_spinbox.value()
            # print(start, stop, step, weight, exposure_time)
            if region_i.k_space_checkbox.isChecked():
                energy_ranges_all.append(
                    KRange(
                        k_min=start,
                        k_max=stop,
                        k_step=step,
                        k_weight=weight,
                        exposure=exposure_time,
                    )
                )

            else:
                energy_ranges_all.append(
                    ERange(
                        E_min=start,
                        E_max=stop,
                        E_step=step,
                        weight=weight,
                        exposure=exposure_time,
                    )
                )

        energies, exposures = merge_ranges(*energy_ranges_all)
        detectors = self.ui.detectors_list.selected_detectors()
        if self.use_edge_checkbox.isChecked():
            try:
                match = re.findall(r"\d+\.?\d*", self.edge_combo_box.currentText())
                edge_value = float(match[-1])

            except:
                QtWidgets.QMessageBox.warning(self, "Error", "Please select an absorption edge.")
        else:
            edge_value = 0
        # Build the queue item
        item = energy_scan(
            energies=energies,
            exposure=exposures,
            E0=edge_value,
            detectors=detectors,
            # energy_signals=energy_signals,
            # time_signals=time_signals,
            ),

        print(item)
        print(energies, exposures, edge_value, detectors)
        
        """
        # Submit the item to the queueserver

        app = FireflyApplication.instance()
        log.info("Add ``scan()`` plan to queue.")
        app.add_queue_item(item)
        """

    def ui_filename(self):
        return "plans/xafs_scan.ui"


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
