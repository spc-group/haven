import pytest
from bluesky_queueserver_api import BPlan
from qtpy import QtCore

from firefly.energy import EnergyDisplay
from haven.devices.energy_positioner import EnergyPositioner


@pytest.fixture()
async def energy_positioner(sim_registry):
    energy = EnergyPositioner(
        monochromator_prefix="mono_ioc:",
        undulator_prefix="id_ioc:",
        name="energy",
    )
    await energy.connect(mock=True)
    sim_registry.register(energy)
    return energy


@pytest.fixture()
def display(qtbot, energy_positioner):
    # Load display
    display = EnergyDisplay()
    qtbot.addWidget(display)
    return display


async def test_move_energy(qtbot, display):
    # Click the set energy button
    btn = display.ui.set_energy_button
    expected_item = BPlan("set_energy", energy=8402.0)

    def check_item(item):
        return item.to_dict() == expected_item.to_dict()

    qtbot.keyClicks(display.target_energy_lineedit, "8402")
    with qtbot.waitSignal(
        display.queue_item_submitted, timeout=1000, check_params_cb=check_item
    ):
        qtbot.mouseClick(btn, QtCore.Qt.LeftButton)


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
    line_edit = display.ui.target_energy_lineedit
    assert line_edit.text() == "8333.000"


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
