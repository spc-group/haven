import pytest
from bluesky_queueserver_api import BPlan
from qtpy import QtCore

from firefly.energy import EnergyDisplay
from haven.devices import AxilonMonochromator, PlanarUndulator


@pytest.fixture()
async def mono(sim_registry):
    mono_ = AxilonMonochromator(name="mono", prefix="")
    await mono_.connect(mock=True)
    sim_registry.register(mono_)
    return mono_


@pytest.fixture()
async def undulator(sim_registry):
    undulator_ = PlanarUndulator(name="undulator", prefix="", offset_pv="")
    await undulator_.connect(mock=True)
    sim_registry.register(undulator_)
    return undulator_


@pytest.fixture()
def display(qtbot, mono, undulator):
    # Load display
    display = EnergyDisplay()
    qtbot.addWidget(display)
    return display


async def test_set_energy_plan(qtbot, display):
    # Click the set energy button
    btn = display.ui.set_energy_button
    expected_item = BPlan("set_energy", energy=8402.0)

    def check_item(item):
        from pprint import pprint

        pprint(item.to_dict())
        pprint(expected_item.to_dict())
        return item.to_dict() == expected_item.to_dict()

    display.target_energy_spinbox.setValue(8402)
    with qtbot.waitSignal(
        display.queue_item_submitted, timeout=1000, check_params_cb=check_item
    ):
        qtbot.mouseClick(btn, QtCore.Qt.LeftButton)


def test_set_energy_args(display):
    args, kwargs = display.set_energy_args()
    assert kwargs == {"energy": 0.0}
    # Set specific harmonic/offset
    display.ui.harmonic_auto_checkbox.setChecked(False)
    display.ui.harmonic_spinbox.setValue(3)
    display.ui.offset_auto_checkbox.setChecked(False)
    display.ui.offset_spinbox.setValue(25.0)
    args, kwargs = display.set_energy_args()
    assert kwargs == {"energy": 0.0, "harmonic": 3, "undulator_offset": 25.0}
    # Don't change the harmonic/offset
    display.ui.harmonic_checkbox.setChecked(False)
    display.ui.offset_checkbox.setChecked(False)
    args, kwargs = display.set_energy_args()
    assert kwargs == {"energy": 0.0, "harmonic": None, "undulator_offset": None}


def test_predefined_energies(qtbot, display):
    # Check that the combo box was populated
    combo_box = display.ui.edge_combo_box
    assert combo_box.count() > 0
    assert combo_box.itemText(0) == "Select edge…"
    assert combo_box.itemText(1) == "Ca K (4038 eV)"
    # Does it filter energies outside the usable range?
    assert combo_box.count() < 250
    # Does it update the energy line edit?
    with qtbot.waitSignal(combo_box.activated, timeout=1000):
        qtbot.keyClicks(combo_box, "Ni K (8333 eV)\t")
        combo_box.activated.emit(9)  # <- this shouldn't be necessary
    spin_box = display.ui.target_energy_spinbox
    assert spin_box.value() == 8333.0


async def test_jog_energy_plan(qtbot, display, mono, undulator):
    display.jog_value_spinbox.setValue(10.0)
    # Click the set energy button
    btn = display.ui.jog_reverse_button
    expected_item = BPlan("mvr", mono.energy.name, -10, undulator.energy.name, -10)

    def check_item(item):
        from pprint import pprint

        pprint(item.to_dict())
        pprint(expected_item.to_dict())
        return item.to_dict() == expected_item.to_dict()

    display.target_energy_spinbox.setValue(8402)
    with qtbot.waitSignal(
        display.execute_item_submitted, timeout=1000, check_params_cb=check_item
    ):
        qtbot.mouseClick(btn, QtCore.Qt.LeftButton)


async def test_move_energy_plan(qtbot, display, mono, undulator):
    display.move_energy_devices_spinbox.setValue(8420.0)
    # Click the set energy button
    btn = display.ui.move_energy_devices_button
    expected_item = BPlan("mv", mono.energy.name, 8420.0, undulator.energy.name, 8420.0)

    def check_item(item):
        from pprint import pprint

        pprint(item.to_dict())
        pprint(expected_item.to_dict())
        return item.to_dict() == expected_item.to_dict()

    display.target_energy_spinbox.setValue(8402)
    with qtbot.waitSignal(
        display.execute_item_submitted, timeout=1000, check_params_cb=check_item
    ):
        qtbot.mouseClick(btn, QtCore.Qt.LeftButton)


def test_energy_readbacks(display, mono):
    """Do we have widgets for reporting the readback energy value for each
    energy device.

    """
    layout = display.ui.energy_layout
    assert layout.rowCount() == 4
    # First device (mono)
    lbl = layout.itemAt(2, layout.LabelRole).widget()
    assert lbl.text() == "Mono:"
    hlayout = layout.itemAt(2, layout.FieldRole)
    assert hlayout.count() == 2
    # Second device (ID)
    lbl = layout.itemAt(3, layout.LabelRole).widget()
    assert lbl.text() == "Undulator:"


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
