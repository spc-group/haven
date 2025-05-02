from unittest import mock

import numpy as np
import pytest
from qtpy import QtWidgets

from firefly.plans.xafs_scan import XafsScanDisplay, XafsScanRegion

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


@pytest.fixture()
def region(qtbot):
    layout = QtWidgets.QGridLayout()
    region = XafsScanRegion(layout, row=1)
    return region


def test_region_number(display):
    """Does changing the region number affect the UI?"""
    # Check that the display has the right number of rows to start with
    assert display.ui.num_regions_spin_box.value() == 3
    assert hasattr(display, "regions")
    assert len(display.regions) == 3

    # Check that regions can be inserted
    display.ui.num_regions_spin_box.setValue(5)
    assert len(display.regions) == 5

    # Check that regions can be removed
    display.ui.num_regions_spin_box.setValue(1)
    assert len(display.regions) == 1


def test_time_calculator(display, xspress, ion_chamber):
    display.ui.num_regions_spin_box.setValue(2)
    display.edge_combo_box.setCurrentIndex(1)
    # Set up the first region
    display.regions[0].start_spin_box.setValue(-20)
    display.regions[0].stop_spin_box.setValue(40)
    display.regions[0].step_spin_box.setValue(10)
    # Set up the second region
    display.regions[1].start_spin_box.setValue(50)
    display.regions[1].stop_spin_box.setValue(800)
    # Convert to k space
    display.regions[1].k_space_checkbox.setChecked(True)
    display.regions[1].step_spin_box.setValue(5)
    display.regions[1].weight_spinbox.setValue(2)
    # Set up detector list
    display.ui.detectors_list.selected_detectors = mock.MagicMock(
        return_value=[xspress, ion_chamber]
    )
    display.update_total_time()
    # Set repeat scan num to 2
    display.ui.spinBox_repeat_scan_num.setValue(3)
    # Check whether time is calculated correctly for a single scan
    assert display.ui.scan_duration_label.text() == "0 h 0 m 27 s"
    # Check whether time is calculated correctly including the repeated scan
    assert display.ui.total_duration_label.text() == "0 h 1 m 23 s"


def test_E0_checkbox(display):
    """Does selecting the E0 checkbox adjust the UI properly?"""
    # check whether extracted edge value is correct
    display.edge_combo_box.setCurrentIndex(2)
    E0 = 4966.0
    display.ui.use_edge_checkbox.setChecked(True)

    # check whether the math is done correctly when switching off E0
    display.ui.use_edge_checkbox.setChecked(False)
    # K-space checkboxes should be disabled when E0 is unchecked
    assert not display.regions[0].k_space_checkbox.isEnabled()

    # check whether energy values are added correctly
    for (start, stop, step), region in zip(default_values, display.regions):
        np.testing.assert_almost_equal(
            region.start_spin_box.value(),
            start + E0,
            decimal=3,
        )
        np.testing.assert_almost_equal(
            region.stop_spin_box.value(),
            stop + E0,
            decimal=3,
        )
        np.testing.assert_almost_equal(
            region.step_spin_box.value(),
            step,
            decimal=3,
        )

    # check whether k range is calculated right
    display.ui.use_edge_checkbox.setChecked(True)
    # K-space checkbox should become re-enabled after E0 is checked
    k_region = display.regions[-1]
    assert k_region.k_space_checkbox.isEnabled()
    k_region.k_space_checkbox.setChecked(True)
    np.testing.assert_almost_equal(k_region.start_spin_box.value(), 3.6226, decimal=4)
    np.testing.assert_almost_equal(k_region.stop_spin_box.value(), 14.4905, decimal=4)
    np.testing.assert_almost_equal(
        k_region.step_spin_box.value(), 3.64069 - 3.6226, decimal=4
    )


def test_queue_plan(display, qtbot):
    """Does a plan actually get emitted when queued?"""
    display.edge_combo_box.setCurrentText("58893.0")
    display.regions[-1].region_checkbox.setChecked(False)
    # Set up detector list
    display.ui.detectors_list.selected_detectors = mock.MagicMock(
        return_value=["vortex_me4", "I0"]
    )
    # set up meta data
    display.ui.lineEdit_sample.setText("sam")
    display.ui.checkBox_is_standard.setChecked(True)
    display.ui.comboBox_purpose.setCurrentText("test")
    display.ui.textEdit_notes.setText("sam_notes")

    args, kwargs = display.plan_args()
    assert args == (
        ["vortex_me4", "I0"],
        ("E", -200.0, -50.0, 5.0, 1.0),
        ("E", -50.0, 50.0, 0.5, 1.0),
    )
    assert kwargs == {
        "E0": 58893.0,
        "md": {
            "sample_name": "sam",
            "purpose": "test",
            "is_standard": True,
            "notes": "sam_notes",
        },
    }


def test_plan_energies(display, qtbot):
    display.edge_combo_box.setCurrentIndex(1)
    display.regions[-1].region_checkbox.setChecked(False)
    # Set up detector list
    display.ui.detectors_list.selected_detectors = mock.MagicMock(
        return_value=["vortex_me4", "I0"]
    )
    # set up meta data
    display.ui.lineEdit_sample.setText("sam")
    display.ui.checkBox_is_standard.setChecked(True)
    display.ui.comboBox_purpose.setCurrentText("test")
    display.ui.textEdit_notes.setText("sam_notes")
    # Check plan arguments that will be sent to the queue
    args, kwargs = display.plan_args()
    assert args == (
        ["vortex_me4", "I0"],
        ("E", -200.0, -50.0, 5.0, 1.0),
        ("E", -50.0, 50.0, 0.5, 1.0),
    )
    assert kwargs == {
        "E0": "Sc-K",
        "md": {
            "sample_name": "sam",
            "purpose": "test",
            "is_standard": True,
            "notes": "sam_notes",
        },
    }


def test_xafs_scan_plan_queued_numeric_E0(display, qtbot):
    display.edge_combo_box.setCurrentText("58893.0")
    display.regions[-1].region_checkbox.setChecked(False)
    # Set up detector list
    display.ui.detectors_list.selected_detectors = mock.MagicMock(
        return_value=["vortex_me4", "I0"]
    )
    # set up meta data
    display.ui.lineEdit_sample.setText("sam")
    display.ui.checkBox_is_standard.setChecked(True)
    display.ui.comboBox_purpose.setCurrentText("test")
    display.ui.textEdit_notes.setText("sam_notes")

    # Check plan arguments
    args, kwargs = display.plan_args()
    detectors, *energy_ranges = args
    assert detectors == ["vortex_me4", "I0"]
    assert energy_ranges == [
        ("E", -200.0, -50.0, 5.0, 1.0),
        ("E", -50.0, 50.0, 0.5, 1.0),
    ]
    assert kwargs["E0"] == 58893.0
    assert kwargs["md"] == {
        "sample_name": "sam",
        "purpose": "test",
        "is_standard": True,
        "notes": "sam_notes",
    }


def test_plan_energies_k_mixed(qtbot, display):
    display.ui.num_regions_spin_box.setValue(2)
    display.edge_combo_box.setCurrentIndex(1)
    # Set up the first region
    display.regions[0].start_spin_box.setValue(-20)
    display.regions[0].stop_spin_box.setValue(40)
    display.regions[0].step_spin_box.setValue(10)
    # Set up the second region
    display.regions[1].start_spin_box.setValue(50)
    display.regions[1].stop_spin_box.setValue(800)
    # Convert to k space
    display.regions[1].k_space_checkbox.setChecked(True)
    display.regions[1].step_spin_box.setValue(5)
    display.regions[1].weight_spinbox.setValue(2)
    # Set up detector list
    display.ui.detectors_list.selected_detectors = mock.MagicMock(
        return_value=["vortex_me4", "I0"]
    )
    # Set repeat scan num to 2
    display.ui.spinBox_repeat_scan_num.setValue(3)
    # Set up meta data
    display.ui.lineEdit_sample.setText("sam")
    display.ui.textEdit_notes.setText("sam_notes")

    args, kwargs = display.plan_args()
    detectors, *energy_ranges = args
    assert detectors == ["vortex_me4", "I0"]
    assert energy_ranges == [
        ("E", -20.0, 40.0, 10, 1.0),
        ("K", 3.6226, 14.4905, 5.0, 1.0, 2),
    ]
    assert kwargs["E0"] == "Sc-K"
    assert kwargs["md"] == {
        "sample_name": "sam",
        "is_standard": False,
        "notes": "sam_notes",
    }


def test_edge_name(display):
    # With a pre-defined option, return just the edge name
    display.edge_combo_box.setCurrentIndex(1)
    assert display.edge_name == "Sc-K"
    # With a write-in edge name, return the edge name
    display.edge_combo_box.setCurrentText("Zz-Z9")
    assert display.edge_name == "Zz-Z9"
    # With a non-edge name, raise an exception
    display.edge_combo_box.setCurrentText("1153")
    assert display.edge_name is None


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


def test_region_domain(qtbot, region):
    assert region.start_spin_box.suffix() == " eV"
    assert region.stop_spin_box.suffix() == " eV"
    assert region.step_spin_box.suffix() == " eV"
    region.set_domain(domain=1)
    assert region.start_spin_box.suffix() == " Å⁻"
    assert region.stop_spin_box.suffix() == " Å⁻"
    assert region.step_spin_box.suffix() == " Å⁻"
    region.set_domain(domain=0)
    assert region.start_spin_box.suffix() == " eV"
    assert region.stop_spin_box.suffix() == " eV"
    assert region.step_spin_box.suffix() == " eV"


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
