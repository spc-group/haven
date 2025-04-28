import logging
import warnings
from functools import partial

from bluesky_queueserver_api import BPlan
from ophydregistry import ComponentNotFound
from ophyd_async.core import Device
from pydm.widgets.label import PyDMLabel
from pydm.widgets.line_edit import PyDMLineEdit
from qtpy import QtCore, QtWidgets
from qtpy.QtWidgets import QDialogButtonBox, QFormLayout, QLineEdit, QVBoxLayout
from xraydb.xraydb import XrayDB
from ophydregistry.exceptions import ComponentNotFound

from firefly import display
from haven import beamline

log = logging.getLogger(__name__)


class EnergyDisplay(display.FireflyDisplay):
    stylesheet_danger = (
        "background: rgb(220, 53, 69); color: white; border-color: rgb(220, 53, 69)"
    )
    stylesheet_normal = ""
    monochromators: list[Device]
    undulators: list[Device]

    def __init__(self, args=None, macros={}, **kwargs):
        # Load X-ray database for calculating edge energies
        self.xraydb = XrayDB()
        super().__init__(args=args, macros=macros, **kwargs)

    def customize_device(self):
        self.monochromators = beamline.devices.findall("monochromators", allow_none=True)
        self.undulators = beamline.devices.findall("undulators", allow_none=True)
        if len(self.monochromators) == 0:
            warnings.warn("Could not find monochromators.")
            log.warning("Could not find monochromators.")
        if len(self.monochromators) + len(self.undulators) == 0:
            raise ComponentNotFound("No devices with label 'energy'")

    def set_energy_args(self) -> tuple[list, dict]:
        kwargs = {
            "energy": self.ui.target_energy_spinbox.value()
        }
        # Parse checkbox states (e.g. "auto") into kwargs
        if not self.harmonic_checkbox.isChecked():
            kwargs['harmonic'] = None
        elif not self.harmonic_auto_checkbox.isChecked():
            kwargs['harmonic'] = self.harmonic_spinbox.value()
        if not self.offset_checkbox.isChecked():
            kwargs['undulator_offset'] = None
        elif not self.offset_auto_checkbox.isChecked():
            kwargs['undulator_offset'] = self.offset_spinbox.value()
            
        return [], kwargs

    @property
    def energy_devices(self) -> list[Device]:
        return [device.energy for device in self.monochromators + self.undulators]

    def jog_energy_devices(self,  *args, direction: int | float = 1, **kwargs):
        jog_value = direction * self.ui.jog_value_spinbox.value()
        args = tuple(arg for device in self.energy_devices for arg in (device.name, jog_value))
        item = BPlan("mvr", *args)
        self.queue_item_executed.emit(item)

    def move_energy_devices(self,  *args, **kwargs):
        new_energy = self.ui.move_energy_devices_spinbox.value()
        args = [arg for device in self.energy_devices for arg in (device.name, new_energy)]
        item = BPlan("mv", *args)
        self.queue_item_executed.emit(item)
    
    def set_energy(self, *args, **kwargs):
        args, kwargs = self.set_energy_args()
        log.info(f"Setting new energy: {kwargs['energy']}")
        # Build the queue item
        item = BPlan("set_energy", *args, **kwargs)
        # Submit the item to the queueserver
        self.queue_item_submitted.emit(item)

    def update_queue_status(self, status):
        self.set_energy_button.update_queue_style(status)

    def customize_ui(self):
        self.ui.move_energy_devices_spinbox.setMaximum(float('inf'))
        self.ui.set_energy_button.clicked.connect(self.set_energy)
        self.ui.move_energy_devices_button.clicked.connect(self.move_energy_devices)
        self.ui.jog_forward_button.clicked.connect(partial(self.jog_energy_devices, direction=1))
        self.ui.jog_reverse_button.clicked.connect(partial(self.jog_energy_devices, direction=-1))
        # Set up the combo box with X-ray energies
        combo_box = self.ui.edge_combo_box
        ltab = self.xraydb.tables["xray_levels"]
        edges = self.xraydb.query(ltab)
        # min_energy, max_energy = self.energy_positioner.limits
        min_energy, max_energy = 4000, 33000
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
            self.ui.target_energy_spinbox.setValue(energy)
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
