import logging
import warnings

import qtawesome as qta
from bluesky_queueserver_api import BPlan
from ophydregistry import ComponentNotFound
from pydm.widgets.label import PyDMLabel
from pydm.widgets.line_edit import PyDMLineEdit
from qtpy import QtCore, QtWidgets
from qtpy.QtWidgets import QDialogButtonBox, QFormLayout, QLineEdit, QVBoxLayout
from xraydb.xraydb import XrayDB

from firefly import display
from haven import load_config, registry

log = logging.getLogger(__name__)


class EnergyCalibrationDialog(QtWidgets.QDialog):
    """A dialog box for calibrating the energy."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowTitle("Energy calibration")

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        # Widgets for inputting calibration parameters
        self.form_layout = QFormLayout()
        self.layout.addLayout(self.form_layout)
        self.form_layout.addRow(
            "Energy readback:", PyDMLabel(self, init_channel="haven://energy.readback")
        )
        self.form_layout.addRow(
            "Energy setpoint:",
            PyDMLineEdit(self, init_channel="haven://energy.setpoint"),
        )
        self.form_layout.addRow(
            "Calibrated energy:",
            QLineEdit(),
        )
        # Button for accept/close
        buttons = QDialogButtonBox.Apply | QDialogButtonBox.Close
        self.buttonBox = QDialogButtonBox(buttons)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonBox)


class EnergyDisplay(display.FireflyDisplay):
    caqtdm_mono_ui_file = "/net/s25data/xorApps/ui/DCMControlCenter.ui"
    caqtdm_id_ui_file = (
        "/net/s25data/xorApps/epics/synApps_6_2/ioc/25ida/25idaApp/op/ui/IDControl.ui"
    )
    stylesheet_danger = (
        "background: rgb(220, 53, 69); color: white; border-color: rgb(220, 53, 69)"
    )
    stylesheet_normal = ""
    energy_positioner = None

    def __init__(self, args=None, macros={}, **kwargs):
        # Load X-ray database for calculating edge energies
        self.xraydb = XrayDB()
        super().__init__(args=args, macros=macros, **kwargs)

    def customize_device(self):
        try:
            self.energy_positioner = registry.find("energy")
        except ComponentNotFound:
            warnings.warn("Could not find energy positioner.")
            log.warning("Could not find energy positioner.")

    def prepare_caqtdm_actions(self):
        """Create QActions for opening mono/ID caQtDM panels.

        Creates two actions, one for the mono and one for the
        insertion device.

        """
        self.caqtdm_actions = []
        # Create an action for launching the mono caQtDM file
        action = QtWidgets.QAction(self)
        action.setObjectName("launch_mono_caqtdm_action")
        action.setText("Mono caQtDM")
        action.triggered.connect(self.launch_mono_caqtdm)
        action.setIcon(qta.icon("fa5s.wrench"))
        action.setToolTip("Launch the caQtDM panel for the monochromator.")
        self.caqtdm_actions.append(action)
        # Create an action for launching the ID caQtDM file
        action = QtWidgets.QAction(self)
        action.setObjectName("launch_id_caqtdm_action")
        action.setText("ID caQtDM")
        action.triggered.connect(self.launch_id_caqtdm)
        action.setIcon(qta.icon("fa5s.wrench"))
        action.setToolTip("Launch the caQtDM panel for the insertion device.")
        self.caqtdm_actions.append(action)

    def launch_mono_caqtdm(self):
        config = load_config()
        mono = self.energy_positioner.monochromator
        ID = self.energy_positioner.undulator
        prefix = mono.prefix
        caqtdm_macros = {
            "P": prefix,
            "MONO": config["monochromator"]["ioc_branch"],
            "BRAGG": mono.bragg.prefix.replace(prefix, ""),
            "GAP": mono.gap.prefix.replace(prefix, ""),
            "ENERGY": mono.energy.prefix.replace(prefix, ""),
            "OFFSET": mono.offset.prefix.replace(prefix, ""),
            "IDENERGY": ID.energy.prefix,
        }
        self.launch_caqtdm(macros=caqtdm_macros, ui_file=self.caqtdm_mono_ui_file)

    def launch_id_caqtdm(self):
        """Launch the pre-built caQtDM UI file for the ID."""
        prefix = self.energy_positioner.undulator.prefix
        # caQtDM doesn't expect the trailing ";"
        prefix = prefix.rstrip(":")
        # Strip leading "ID" from the ID IOC since caQtDM adds it
        prefix = prefix.strip("ID")
        caqtdm_macros = {
            # No idea what "M", and "D" do, they're not in the UI
            # file.
            "ID": prefix,
            "M": 2,
            "D": 2,
        }
        self.launch_caqtdm(macros=caqtdm_macros, ui_file=self.caqtdm_id_ui_file)

    def set_energy(self, *args, **kwargs):
        energy = float(self.ui.target_energy_lineedit.text())
        log.info(f"Setting new energy: {energy}")
        # Build the queue item
        item = BPlan("set_energy", energy=energy)
        # Submit the item to the queueserver
        self.queue_item_submitted.emit(item)

    def update_queue_status(self, status):
        self.set_energy_button.update_queue_style(status)

    def customize_ui(self):
        self.ui.set_energy_button.clicked.connect(self.set_energy)
        # Set up the combo box with X-ray energies
        combo_box = self.ui.edge_combo_box
        ltab = self.xraydb.tables["xray_levels"]
        edges = self.xraydb.query(ltab)
        min_energy, max_energy = self.energy_positioner.limits
        print(self.energy_positioner)
        print(min_energy, max_energy)
        edges = edges.filter(
            ltab.c.absorption_edge < max_energy,
            ltab.c.absorption_edge > min_energy,
        )
        items = [
            f"{r.element} {r.iupac_symbol} ({int(r.absorption_edge)} eV)"
            for r in edges.all()
        ]
        combo_box.addItems(["Select edge…", *items])
        combo_box.activated.connect(self.select_edge)
        # Respond to the "calibrate" button
        self.ui.calibrate_button.clicked.connect(self.show_calibrate_dialog)

    def show_calibrate_dialog(self):
        dialog = EnergyCalibrationDialog(self)
        dialog.exec()

    @QtCore.Slot(int)
    def select_edge(self, index):
        if index == 0:
            # The placeholder text was selected
            return
        # Parse the combo box text to get the selected edge
        combo_box = self.ui.edge_combo_box
        text = combo_box.itemText(index)
        elem, edge = text.replace(" ", "_").split("_")[:2]
        # Determine which energy was selected
        edge_info = self.xraydb.xray_edge(element=elem, edge=edge)
        if edge_info is None:
            # Edge is not recognized, so provide feedback
            combo_box.setStyleSheet(self.stylesheet_danger)
        else:
            # Set the text field to the selected edge's energy
            energy, fyield, edge_jump = edge_info
            self.ui.target_energy_lineedit.setText(f"{energy:.3f}")
            combo_box.setStyleSheet(self.stylesheet_normal)

    def ui_filename(self):
        return "energy.ui"


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
