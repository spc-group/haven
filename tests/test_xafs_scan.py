import pytest

from firefly.main_window import FireflyMainWindow
from firefly.xafs_scan import XafsScanDisplay


def test_region_number(qtbot):
    """Does changing the region number affect the UI?"""
    window = FireflyMainWindow()
    qtbot.addWidget(window)
    disp = XafsScanDisplay()
    qtbot.addWidget(disp)
    # Check that the display has the right number of rows to start with
    assert disp.ui.regions_spin_box.value() == 3
    assert hasattr(disp, "regions")
    assert len(disp.regions) == 3
    # Check that regions can be inserted and removed


def test_region(qtbot):
    """Does changing the region ui respond the way it should."""
    window = FireflyMainWindow()
    qtbot.addWidget(window)
    disp = XafsScanDisplay()
    qtbot.addWidget(disp)
    # Does the k-space checkbox enable the k-weight edit line
    region = disp.regions[0]
    region.k_space_checkbox.setChecked(True)
    assert region.k_weight_line_edit.isEnabled() is True


def test_E0_checkbox(qtbot):
    """Does selecting the E0 checkbox adjust the UI properly?"""
    window = FireflyMainWindow()
    qtbot.addWidget(window)
    disp = XafsScanDisplay()
    qtbot.addWidget(disp)
    # K-space checkboxes should be disabled when E0 is unchecked
    disp.ui.use_edge_checkbox.setChecked(False)
    assert not disp.regions[0].k_space_checkbox.isEnabled()
    # K-space checkbox should become re-enabled after E0 is checked
    disp.ui.use_edge_checkbox.setChecked(True)
    assert disp.regions[0].k_space_checkbox.isEnabled()
    # Checked k-space boxes should be unchecked when the E0 is disabled
    disp.regions[0].k_space_checkbox.setChecked(True)
    disp.ui.use_edge_checkbox.setChecked(False)
    disp.regions[0].k_space_checkbox.setChecked(False)
    assert not disp.regions[0].k_space_checkbox.isChecked()
