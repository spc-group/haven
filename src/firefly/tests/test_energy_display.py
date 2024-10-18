import pytest
from bluesky_queueserver_api import BPlan

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


def test_move_energy(qtbot, display, monkeypatch):
    monkeypatch.setattr(display, "submit_queue_item", mock.MagicMock())
    # Prepare the display for sending a plan
    expected_item = BPlan("set_energy", energy=8402.0)
    display.target_energy_lineedit.setText("8402")
    # Check that the right plan is emitted
    display.set_energy()
    assert display.submit_queue_item.called
    submitted_item = display.submit_queue_item.call_args[0][0]
    assert submitted_item.to_dict() == expected_item.to_dict()


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
