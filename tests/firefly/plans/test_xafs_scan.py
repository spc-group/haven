from unittest import mock

import pytest

from firefly.plans.xafs_scan import Domain, XafsScanDisplay

# default values for EXAFS scan
pre_edge = [-200, -50, 5]
xanes_region = [-50, 50, 0.5]
exafs_region = [50, 800, 0.5]
default_values = [pre_edge, xanes_region, exafs_region]


@pytest.fixture()
def display(qtbot):
    display = XafsScanDisplay()
    qtbot.addWidget(display)
    return display


async def test_region_number(display):
    """Does changing the region number affect the UI?"""
    # Check that the display has the right number of rows to start with
    assert display.ui.num_regions_spin_box.value() == 3
    assert hasattr(display, "regions")
    await display.regions.set_region_count(3)
    assert len(display.regions) == 3

    # Check that regions can be inserted
    await display.regions.set_region_count(5)
    assert len(display.regions) == 5

    # Check that regions can be removed
    await display.regions.set_region_count(1)
    assert len(display.regions) == 1


async def test_time_calculator(display, xspress, ion_chamber):
    await display.regions.set_region_count(3)
    display.edge_combo_box.setCurrentIndex(1)
    # Set up the first region
    widgets = display.regions.row_widgets(1)
    widgets.start_spin_box.setValue(-20)
    widgets.stop_spin_box.setValue(40)
    widgets.step_spin_box.setValue(10)
    # Set up the second region
    widgets = display.regions.row_widgets(2)
    widgets.start_spin_box.setValue(50)
    widgets.stop_spin_box.setValue(800)
    # Convert to k space
    widgets.k_space_checkbox.setChecked(True)
    widgets.step_spin_box.setValue(5)
    widgets.weight_spin_box.setValue(2)
    # Disable the third region
    display.regions.row_widgets(3).active_checkbox.setChecked(False)
    # Set other widgets
    display.ui.spinBox_repeat_scan_num.setValue(3)
    # Check whether time is calculated correctly
    await display.update_total_time()
    assert display.ui.scan_duration_label.text() == "0\u202fh 0\u202fm 27\u202fs"
    assert display.ui.total_duration_label.text() == "0\u202fh 1\u202fm 23\u202fs"


async def test_E0_checkbox(display):
    """Does selecting the E0 checkbox adjust the UI properly?"""
    await display.regions.set_region_count(1)
    # check whether extracted edge value is correct
    display.edge_combo_box.setCurrentIndex(2)
    E0 = 4966.0
    display.ui.use_edge_checkbox.setChecked(True)
    # Set some default region values
    widgets = display.regions.row_widgets(1)
    widgets.start_spin_box.setValue(-200)
    widgets.stop_spin_box.setValue(50)
    # check whether the math is done correctly when switching off E0
    display.ui.use_edge_checkbox.setChecked(False)
    # K-space checkboxes should be disabled when E0 is unchecked
    assert not widgets.k_space_checkbox.isEnabled()
    # Check whether energy values are added correctly
    assert widgets.start_spin_box.value() == 4766
    assert widgets.stop_spin_box.value() == 5016
    # check whether k range is calculated right
    display.ui.use_edge_checkbox.setChecked(True)
    # K-space checkbox should become re-enabled after E0 is checked
    assert widgets.k_space_checkbox.isEnabled()
    assert widgets.start_spin_box.value() == -200
    assert widgets.stop_spin_box.value() == 50


async def test_plan_energies(display):
    """Does a plan actually get emitted when queued?"""
    await display.regions.set_region_count(3)
    display.edge_combo_box.setCurrentText("58893.0")
    # Set region widget values
    widgets = display.regions.row_widgets(1)
    widgets.start_spin_box.setValue(-200)
    widgets.stop_spin_box.setValue(-50)
    widgets.step_spin_box.setValue(5)
    widgets = display.regions.row_widgets(2)
    widgets.start_spin_box.setValue(-50)
    widgets.stop_spin_box.setValue(50)
    widgets.step_spin_box.setValue(0.5)
    # Disable the last row
    display.regions.row_widgets(3).active_checkbox.setChecked(False)
    # Set up detector list
    args, kwargs = display.plan_args()
    detectors, *energy_ranges = args
    assert energy_ranges == [
        ("E", -200.0, -50.0, 5.0, 1.0),
        ("E", -50.0, 50.0, 0.5, 1.0),
    ]
    assert kwargs["E0"] == 58893.0


async def test_plan_energies_k_mixed(display):
    await display.regions.set_region_count(2)
    display.edge_combo_box.setCurrentIndex(1)
    # Set up the first region
    widgets = display.regions.row_widgets(1)
    widgets.start_spin_box.setValue(-20)
    widgets.stop_spin_box.setValue(40)
    widgets.step_spin_box.setValue(10)
    # Set up the second region
    widgets = display.regions.row_widgets(2)
    widgets.start_spin_box.setValue(50)
    widgets.stop_spin_box.setValue(800)
    # Convert to k space
    widgets.k_space_checkbox.setChecked(True)
    widgets.step_spin_box.setValue(5)
    widgets.weight_spin_box.setValue(2)
    args, kwargs = display.plan_args()
    detectors, *energy_ranges = args
    assert energy_ranges == [
        ("E", -20.0, 40.0, 10.0, 1.0),
        ("K", 3.6226, 14.4905, 5.0, 1.0, 2),
    ]


async def test_plan_metadata(display):
    """Check that the metadata are passed properly."""
    # set up meta data
    display.metadata_widget.sample_line_edit.setText("sam")
    display.metadata_widget.standard_check_box.setChecked(True)
    display.metadata_widget.purpose_combo_box.setCurrentText("test")
    display.metadata_widget.notes_text_edit.setText("sam_notes")
    # Check plan arguments that will be sent to the queue
    args, kwargs = display.plan_args()
    assert kwargs["md"] == {
        "sample_name": "sam",
        "purpose": "test",
        "is_standard": True,
        "notes": "sam_notes",
    }


async def test_plan_edge(display):
    """Check that the edge name is passed properly."""
    display.edge_combo_box.setCurrentIndex(1)
    # Check plan arguments that will be sent to the queue
    args, kwargs = display.plan_args()
    assert kwargs["E0"] == "Sc-K"


def test_edge_name(display):
    # With a pre-defined option, return just the edge name
    display.edge_combo_box.setCurrentIndex(1)
    assert display.edge_name == "Sc-K"
    # With a write-in edge name, return the edge name
    display.edge_combo_box.setCurrentText("Zz-Z9")
    assert display.edge_name == "Zz-Z9"
    # With a non-edge name, raise an exception
    display.edge_combo_box.setCurrentText("1153")
    assert display.edge_name == ""


def test_E0(display):
    # With a pre-defined option, return just the edge name
    display.edge_combo_box.setCurrentIndex(1)
    assert display.E0 == 4492.0
    # With a write-in edge name, return the edge name
    display.edge_combo_box.setCurrentText("Ni-K")
    assert display.E0 == 8333.0
    # With a non-edge name, raise an exception
    display.edge_combo_box.setCurrentText("1153")
    assert display.E0 == 1153.0
    # Check that non-edges return None
    display.edge_combo_box.setCurrentText("spam and eggs")
    assert display.E0 is None


async def test_region_domain(display):
    await display.regions.set_region_count(1)
    widgets = display.regions.row_widgets(1)
    assert widgets.start_spin_box.suffix() == " eV"
    assert widgets.stop_spin_box.suffix() == " eV"
    assert widgets.step_spin_box.suffix() == " eV"
    assert not widgets.weight_spin_box.isEnabled()
    display.regions.set_domain(domain=Domain.WAVENUMBER, row=1)
    assert widgets.start_spin_box.suffix() == " Å⁻"
    assert widgets.stop_spin_box.suffix() == " Å⁻"
    assert widgets.step_spin_box.suffix() == " Å⁻"
    assert widgets.weight_spin_box.isEnabled()
    display.regions.set_domain(domain=Domain.ENERGY, row=1)
    assert widgets.start_spin_box.suffix() == " eV"
    assert widgets.stop_spin_box.suffix() == " eV"
    assert widgets.step_spin_box.suffix() == " eV"
    assert not widgets.weight_spin_box.isEnabled()


async def test_enable_row_widgets(display):
    """Check that the correct widgets are en/disabled for a row."""
    await display.regions.set_region_count(1)
    widgets = display.regions.row_widgets(1)
    display.regions.set_domain(Domain.ENERGY, row=1)
    assert not widgets.weight_spin_box.isEnabled()
    # Toggle all the widgets in the row
    display.regions.enable_row_widgets(False, row=1)
    display.regions.enable_row_widgets(True, row=1)
    assert not widgets.weight_spin_box.isEnabled()


async def test_update_devices(display, sim_registry):
    display.detectors_list.update_devices = mock.AsyncMock()
    await display.update_devices(sim_registry)
    assert display.detectors_list.update_devices.called


def test_queue_plan(display, qtbot):
    # Make sure the plan can be submitted
    # Specific plan args should test `display.plan_args()`
    display.ui.edge_combo_box.setCurrentText("8333")
    with qtbot.waitSignal(display.queue_item_submitted, timeout=2):
        display.queue_plan()


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman, Juan Juan Huang
# :email:     wolfman@anl.gov, juanjuan.huang@anl.gov
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
