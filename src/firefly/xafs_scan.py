from qtpy import QtWidgets

from firefly import display


class XafsScanRegion:
    def __init__(self):
        self.setup_ui()

    def setup_ui(self):
        self.layout = QtWidgets.QHBoxLayout()
        # First energy box
        self.start_line_edit = QtWidgets.QLineEdit()
        self.start_line_edit.setPlaceholderText("Start…")
        self.layout.addWidget(self.start_line_edit)
        # Last energy box
        self.stop_line_edit = QtWidgets.QLineEdit()
        self.stop_line_edit.setPlaceholderText("Stop…")
        self.layout.addWidget(self.stop_line_edit)
        # Energy step box
        self.step_line_edit = QtWidgets.QLineEdit()
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
        self.k_space_checkbox.stateChanged.connect(self.k_weight_line_edit.setEnabled)

    def update_edge_enabled(self, is_checked: int):
        # Go back to real space if k-space was enabled
        if not is_checked:
            self.k_space_checkbox.setChecked(False)
        # Disabled the k-space checkbox
        self.k_space_checkbox.setEnabled(is_checked)


class XafsScanDisplay(display.FireflyDisplay):
    def customize_ui(self):
        self.reset_default_regions()
        # Connect the E0 checkbox to the E0 combobox
        self.ui.use_edge_checkbox.stateChanged.connect(self.edge_combo_box.setEnabled)

    def reset_default_regions(self):
        self.regions = []
        num_regions = 3
        self.ui.regions_spin_box.setValue(num_regions)
        self.add_regions(num_regions)

    def add_regions(self, num=1):
        for i in range(num):
            region = XafsScanRegion()
            self.ui.regions_layout.addLayout(region.layout)
            # Connect the E0 checkbox to each of the regions
            self.ui.use_edge_checkbox.stateChanged.connect(region.update_edge_enabled)
            # Save it to the list
            self.regions.append(region)

    def ui_filename(self):
        return "xafs_scan.ui"


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
