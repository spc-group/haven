import re
import logging
import numpy as np

from qtpy import QtWidgets
from qtpy.QtGui import QDoubleValidator
from xraydb.xraydb import XrayDB
from bluesky_queueserver_api import BPlan

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
log = logging.getLogger(__name__)

#TODO solve Python decimal
float_accuracy = 4


# the energy resolution will not be better than 0.01 eV at S25, e.g., 0.01 eV /4000 eV -> 10-6 level, Si(311) is 10-5 level
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

        labels = ['Start', 'Stop', 'Step', 'Weight', '', 'Exposure [s]']
        Qlabels_all = {}
        for label_i in labels:
            Qlabel_i = QtWidgets.QLabel(label_i)
            self.layout.addWidget(Qlabel_i)
            Qlabels_all[label_i] = Qlabel_i

        # fix widths so the labels are aligned with XafsRegions
        Qlabels_all['Weight'].setFixedWidth(57)
        Qlabels_all[''].setFixedWidth(57)
        Qlabels_all['Exposure [s]'].setFixedWidth(68)

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

    def update_line_edit_value(self, line_edit, conversion_func):
        text = line_edit.text()
        if text:
            converted_value = conversion_func(round(float(text), float_accuracy))
            line_edit.setText(f"{converted_value:.6g}")

    def update_wavenumber_energy(self):
        is_k_checked = self.k_space_checkbox.isChecked()

        # Define conversion functions
        conversion_funcs = {
            self.step_line_edit: E_step_to_k_step
            if is_k_checked
            else lambda x, y: k_step_to_E_step_round(x, y),

            self.start_line_edit: energy_to_wavenumber
            if is_k_checked
            else wavenumber_to_energy_round,
            
            self.stop_line_edit: energy_to_wavenumber
            if is_k_checked
            else wavenumber_to_energy_round,
        }

        # Iterate over line edits and apply corresponding conversion
        for line_edit, func in conversion_funcs.items():
            # Special handling for step_line_edit due to different parameters needed
            if line_edit == self.step_line_edit:
                start_text = self.start_line_edit.text()
                if start_text and line_edit.text():
                    start = float(start_text)
                    step = float(line_edit.text())
                    new_values = func(start, step) if is_k_checked else func(start, step)
                    line_edit.setText(f"{new_values:.4g}")
            else:
                self.update_line_edit_value(line_edit, func)


class XafsScanDisplay(display.FireflyDisplay):
    min_energy = 4000
    max_energy = 33000

    def customize_ui(self):
        # Remove the defaut XAFS layout from .ui file
        self.ui.clearLayout(self.ui.region_layout)

        # add title layout
        self.title_region = TitleRegion()
        self.ui.title_layout.addLayout(self.title_region.layout)

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

        # for testing
        #TODO remove the following after testing
        self.ui.run_button.setEnabled(True)
        self.ui.run_button.clicked.connect(self.queue_plan)        
        
        # connect checkboxes with all regions' check box
        self.title_region.regions_all_checkbox.stateChanged.connect(self.on_regions_all_checkbox)

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
        self.edge_value = round(float(match[-1]), float_accuracy) if match else 0

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
                        round(float(text), float_accuracy) - self.edge_value
                        if is_checked
                        else round(float(text), float_accuracy) + self.edge_value
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
            # disable/enabale regions when selected
            region.region_checkbox.stateChanged.connect(self.on_region_checkbox)

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
            try:
                start = round(float(region_i.start_line_edit.text()), float_accuracy)
                stop = round(float(region_i.stop_line_edit.text()), float_accuracy)
                step = round(float(region_i.step_line_edit.text()), float_accuracy)
                weight = region_i.weight_spinbox.value()
                exposure_time = region_i.exposure_time_spinbox.value()
            except ValueError:
                QtWidgets.QMessageBox.warning(self, "Value Error", "Invalid value detected!")
                return None
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

        # Turn ndarrays into lists so they can be JSON serialized
        energies, exposures = merge_ranges(*energy_ranges_all, sort=True)
        energies = list(np.round(energies, float_accuracy))
        exposures = list(np.round(exposures, float_accuracy))
        detectors = self.ui.detectors_list.selected_detectors()
        md={'sample': self.ui.lineEdit_sample.text(),
            'purpose':self.ui.lineEdit_purpose.text()}

        # Check that an absorption edge was selected
        if self.use_edge_checkbox.isChecked():
            try:
                match = re.findall(r"\d+\.?\d*", self.edge_combo_box.currentText())
                self.edge_value = round(float(match[-1]), float_accuracy)

            except:
                QtWidgets.QMessageBox.warning(self, "Error", "Please select an absorption edge.")
                return None
        else:
            self.edge_value = 0
        # Build the queue item
        item = BPlan(
            'energy_scan',
            energies=energies,
            exposure=exposures,
            E0=self.edge_value,
            detectors=detectors,
            md=md,
            )

        print(item)
        print(energies, exposures, self.edge_value, detectors, md)
        

        # Submit the item to the queueserver
        app = FireflyApplication.instance()
        log.info("Add ``scan()`` plan to queue.")
        app.add_queue_item(item)
        

    def ui_filename(self):
        return "plans/xafs_scan.ui"


# -----------------------------------------------------------------------------
# :author:    Juanjuan Huang
# :email:     wolfman@anl.gov
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