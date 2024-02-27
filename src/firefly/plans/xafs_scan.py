from qtpy import QtWidgets

from firefly import display
from qtpy.QtGui import QDoubleValidator
from xraydb.xraydb import XrayDB
import re

# TODO: use relative import in the future, copied energy_ranges.py to the current folder
from energy_ranges import ERange, KRange, KRange_useE, merge_ranges, energy_to_wavenumber, wavenumber_to_energy
from haven.plans import energy_scan

class XafsScanRegion:
    def __init__(self):
        self.setup_ui()

    def setup_ui(self):
        self.layout = QtWidgets.QHBoxLayout()

        # First energy box
        self.start_line_edit = QtWidgets.QLineEdit()
        self.start_line_edit.setValidator(QDoubleValidator()) # only takes numbers
        self.start_line_edit.setPlaceholderText("Start…")
        self.layout.addWidget(self.start_line_edit)
        # Last energy box
        self.stop_line_edit = QtWidgets.QLineEdit()
        self.start_line_edit.setValidator(QDoubleValidator()) # only takes numbers
        self.stop_line_edit.setPlaceholderText("Stop…")
        self.layout.addWidget(self.stop_line_edit)
        # Energy step box
        self.step_line_edit = QtWidgets.QLineEdit()
        self.start_line_edit.setValidator(QDoubleValidator()) # only takes numbers
        self.step_line_edit.setPlaceholderText("Step…")
        self.layout.addWidget(self.step_line_edit)
        # K-space checkbox
        self.k_space_checkbox = QtWidgets.QCheckBox()
        self.k_space_checkbox.setText("K-space")
        self.k_space_checkbox.setEnabled(False)
        self.layout.addWidget(self.k_space_checkbox)
        # K-weight factor box, hidden at first
        self.k_weight_line_edit = QtWidgets.QLineEdit()
        self.k_weight_line_edit.setPlaceholderText("K-weight")
        self.k_weight_line_edit.setEnabled(False)
        self.layout.addWidget(self.k_weight_line_edit)

        # Connect the k-space enabled checkbox to the relevant signals
        self.k_space_checkbox.stateChanged.connect(self.update_wavenumber_energy)
        # # when value is negative, disable k checkbox
        # self.start_line_edit.textChanged.connect(self.update_k_space_checkbox)
        # self.stop_line_edit.textChanged.connect(self.update_k_space_checkbox)

    # def update_k_space_checkbox(self):
    #     start, stop = float(self.start_line_edit.text()), float(self.stop_line_edit.text())
    #     if start > 0 and stop > 0:
    #         self.k_space_checkbox.setEnabled(True)
    #     else:
    #         self.k_space_checkbox.setEnabled(False)

    def update_wavenumber_energy(self):
        if self.k_space_checkbox.isChecked():
            self.k_weight_line_edit.setEnabled(True)
            # convert energy to wavenumber
            if self.start_line_edit.text() != '':
                k_min = energy_to_wavenumber(float(self.start_line_edit.text()))
                self.start_line_edit.setText(f'{k_min:.5f}')

            if self.stop_line_edit.text() != '':
                k_max = energy_to_wavenumber(float(self.stop_line_edit.text()))
                self.stop_line_edit.setText(f'{k_max:.5f}')

            if self.step_line_edit.text() != '':
                k_step = energy_to_wavenumber(float(self.step_line_edit.text()))
                self.step_line_edit.setText(f'{k_step:.5f}')
        
        if not self.k_space_checkbox.isChecked():
            self.k_weight_line_edit.setEnabled(False)
            # convert wavenumber to energy
            if self.start_line_edit.text() != '':
                E_min = wavenumber_to_energy(float(self.start_line_edit.text()))
                self.start_line_edit.setText(f'{E_min:.1f}')

            if self.stop_line_edit.text() != '':
                E_max = wavenumber_to_energy(float(self.stop_line_edit.text()))
                self.stop_line_edit.setText(f'{E_max:.1f}')

            if self.step_line_edit.text() != '':
                E_step = wavenumber_to_energy(float(self.step_line_edit.text()))
                self.step_line_edit.setText(f'{E_step:.1f}')

class XafsScanDisplay(display.FireflyDisplay):
    min_energy = 4000
    max_energy = 33000

    def customize_ui(self):
        # Remove the defaufdsadfsfdsfagafdsgalt XAFS layout from .ui file
        self.clearLayout(self.ui.region_layout)

        self.reset_default_regions()
        # Connect the E0 checkbox to the E0 combobox
        self.ui.use_edge_checkbox.stateChanged.connect(self.use_edge)
    
        # disable the line edits in spin box
        self.ui.regions_spin_box.lineEdit().setReadOnly(True)
        
        # when regions number changed
        self.ui.regions_spin_box.valueChanged.connect(self.update_regions)
        self.ui.regions_spin_box.editingFinished.connect(self.update_regions)
        
        # reset button
        self.ui.pushButton.clicked.connect(self.reset_default_regions)
        
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


    def use_edge(self):
        self.edge_value = float(re.search(r'\d+\.?\d*', self.edge_combo_box.currentText()).group())
        if self.ui.use_edge_checkbox.isChecked():
            self.edge_combo_box.setEnabled(True)
            for i, region_i in enumerate(self.regions):
                start, stop = region_i.start_line_edit.text(), region_i.stop_line_edit.text()
                if start != '':
                    relativeE_start = float(start) - self.edge_value
                    region_i.start_line_edit.setText("{:.1f}".format(relativeE_start))
                if stop != '':
                    relativeE_stop = float(stop) - self.edge_value
                    region_i.stop_line_edit.setText("{:.1f}".format(relativeE_stop))

        if not self.ui.use_edge_checkbox.isChecked():
            self.edge_combo_box.setEnabled(False)
            self.edge_value = float(re.search(r'\d+\.?\d*', self.edge_combo_box.currentText()).group())
            
            for i, region_i in enumerate(self.regions):
                # uncheck k space
                region_i.k_space_checkbox.setChecked(False)
                region_i.k_space_checkbox.setEnabled(False)

                # change absolute E to relative E
                start, stop = region_i.start_line_edit.text(), region_i.stop_line_edit.text()
                if start != '':
                    relativeE_start = float(start) + self.edge_value
                    region_i.start_line_edit.setText("{:.1f}".format(relativeE_start))
                if stop != '':
                    relativeE_stop = float(stop) + self.edge_value
                    region_i.stop_line_edit.setText("{:.1f}".format(relativeE_stop))
                
    def update_k_space_checkbox(self): 
        use_edge_checked = self.ui.use_edge_checkbox.isChecked() 
        for region_i in self.regions: 
            start_text = region_i.start_line_edit.text() 
            stop_text = region_i.stop_line_edit.text() 
            # Determine if start and stop are both non-empty and convert to floats if they are 
            start = float(start_text) if start_text else 0 
            stop = float(stop_text) if stop_text else 0 
            # Enable k_space_checkbox if use_edge_checked is True, and both start and stop are positive 
            region_i.k_space_checkbox.setEnabled(use_edge_checked and start > 0 and stop > 0)
        
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
            # region_i.update_k_space_checkbox()
        self.update_k_space_checkbox()

        

    def add_regions(self, num=1):
        for i in range(num):
            region = XafsScanRegion()
            self.ui.regions_layout.addLayout(region.layout)
            # Connect the E0 checkbox to each of the regions
            # self.ui.use_edge_checkbox.stateChanged.connect(region.update_edge_enabled)         
            # when value is negative, disable k checkbox
            region.start_line_edit.textChanged.connect(self.update_k_space_checkbox)
            region.stop_line_edit.textChanged.connect(self.update_k_space_checkbox)
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
        detectors = self.ui.detectors_list.selected_detectors()
        exposure_time = self.ui.doubleSpinBox_exposure.value()
        
        # get paramters from each rows of line regions:
        energy_ranges_all = []
        for region_i in self.regions:
            E_min = float(region_i.start_line_edit.text())
            E_max = float(region_i.stop_line_edit.text())
            E_step = float(region_i.step_line_edit.text())

            if self.region_i.k_space_checkbox.isUnchecked():
                energy_ranges_all.append(
                    ERange(E_min=E_min,
                           E_max=E_max,
                           E_step= E_step,
                           exposure=exposure_time
                           ))            
            else:
                energy_ranges_all.append(
                    KRange(E_min=E_min,
                           k_max=E_max,
                           k_step= E_step,
                           k_weight=float(region_i.k_weight_line_edit.text()),
                           exposure=exposure_time
                           ))
                    
        energy_ranges = []
        energies, exposures = merge_ranges(*energy_ranges)
        # # Build the queue item
        item = energy_scan(
            energies=energies,
            exposure=exposures,
            E0=self.edge_value,
            detectors=detectors,
            # energy_positioners=energy_positioners,
            # time_positioners=time_positioners,
            md=ChainMap(md, {"plan_name": "xafs_scan"}),
            )
        
        print(item)
        """
        # Submit the item to the queueserver
        from firefly.application import FireflyApplication

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
