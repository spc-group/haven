import time
from ophyd import Kind

import numpy as np
from pyqtgraph import PlotItem
import pytest
from qtpy import QtCore

from firefly.main_window import FireflyMainWindow
from firefly.xrf_detector import XRFDetectorDisplay, XRFPlotWidget
from firefly.xrf_roi import XRFROIDisplay


@pytest.fixture()
def xrf_display(ffapp, sim_vortex):
    FireflyMainWindow()
    display = XRFDetectorDisplay(macros={"DEV": sim_vortex.name})
    spectra = np.random.default_rng(seed=0).integers(
        0, 65536, dtype=np.int_, size=(4, 1024)
    )
    plot_widget = display.mca_plot_widget
    plot_widget.update_spectrum(1, spectra[0])
    plot_widget.update_spectrum(2, spectra[1])
    return display


def test_open_xrf_detector_viewer_actions(ffapp, qtbot, sim_vortex):
    # Get the area detector parts ready
    ffapp.prepare_xrf_detector_windows()
    assert hasattr(ffapp, "xrf_detector_actions")
    assert len(ffapp.xrf_detector_actions) == 1
    # Launch an action and see that a window opens
    list(ffapp.xrf_detector_actions.values())[0].trigger()
    assert "FireflyMainWindow_xrf_detector_vortex_me4" in ffapp.windows.keys()


def test_roi_widgets(ffapp, sim_vortex):
    FireflyMainWindow()
    display = XRFDetectorDisplay(macros={"DEV": sim_vortex.name})
    display.draw_roi_widgets(2)
    # Check that the widgets were drawn
    assert len(display.roi_displays) == sim_vortex.num_rois
    disp = display.roi_displays[0]


def test_roi_element_comboboxes(ffapp, qtbot, sim_vortex):
    FireflyMainWindow()
    display = XRFDetectorDisplay(macros={"DEV": sim_vortex.name})
    # Check that the comboboxes have the right number of entries
    element_cb = display.ui.mca_combobox
    assert element_cb.count() == sim_vortex.num_elements
    roi_cb = display.ui.roi_combobox
    assert roi_cb.count() == sim_vortex.num_rois


def test_roi_selection(ffapp, qtbot, sim_vortex):
    FireflyMainWindow()
    display = XRFROIDisplay(
        macros={"DEV": sim_vortex.name, "NUM": 2, "MCA": 2, "ROI": 2}
    )
    # Unchecked box should be bland
    assert "background" not in display.styleSheet()
    # Make the ROI selected and check for a distinct background
    display.ui.set_roi_button.setChecked(True)
    assert f"background: {display.selected_background}" in display.styleSheet()
    # Disabling the ROI should unselect it as well
    display.ui.set_roi_button.setChecked(True)
    display.ui.enabled_checkbox.setChecked(True)
    display.ui.enabled_checkbox.setChecked(False)
    assert not display.ui.set_roi_button.isChecked()
    assert f"background: {display.selected_background}" not in display.styleSheet()


def test_all_rois_selection(ffapp, qtbot, sim_vortex):
    """Are all the other ROIs disabled when one is selected?"""
    FireflyMainWindow()
    display = XRFDetectorDisplay(macros={"DEV": sim_vortex.name})
    roi_display = display.roi_displays[0]
    # Pretend an ROI display was selected
    roi_display.selected.emit(True)
    # Check that a different ROI display was disabled
    assert not display.roi_displays[1].isEnabled()


def test_all_mcas_selection(ffapp, qtbot, sim_vortex):
    """Are all the other ROIs disabled when one is selected?"""
    FireflyMainWindow()
    display = XRFDetectorDisplay(macros={"DEV": sim_vortex.name})
    mca_display = display.mca_displays[0]
    # Pretend an ROI display was selected
    mca_display.selected.emit(True)
    # Check that a different ROI display was disabled
    assert not display.mca_displays[1].isEnabled()


def test_update_roi_spectra(ffapp, qtbot, sim_vortex):
    FireflyMainWindow()
    display = XRFDetectorDisplay(macros={"DEV": sim_vortex.name})
    spectra = np.random.default_rng(seed=0).integers(
        0, 65536, dtype=np.int_, size=(4, 1024)
    )
    roi_plot_widget = display.ui.roi_plot_widget
    with qtbot.waitSignal(roi_plot_widget.plot_changed):
        display._spectrum_channels[0].value_slot(spectra[0])
        display._spectrum_channels[1].value_slot(spectra[1])
    # Check that a PlotItem was created
    plot_item = roi_plot_widget.ui.plot_widget.getPlotItem()
    assert isinstance(plot_item, PlotItem)
    # Check that the spectrum was plotted
    data_items = plot_item.listDataItems()
    assert len(data_items) == 1
    # Check that previous plots get cleared
    spectra2 = np.random.default_rng(seed=1).integers(
        0, 65536, dtype=np.int_, size=(4, 1024)
    )
    with qtbot.waitSignal(roi_plot_widget.plot_changed):
        display._spectrum_channels[0].value_slot(spectra2[0])
    data_items = plot_item.listDataItems()
    assert len(data_items) == 1


def test_update_mca_spectra(ffapp, qtbot, sim_vortex):
    FireflyMainWindow()
    display = XRFDetectorDisplay(macros={"DEV": sim_vortex.name})
    spectra = np.random.default_rng(seed=0).integers(
        0, 65536, dtype=np.int_, size=(4, 1024)
    )
    mca_plot_widget = display.ui.mca_plot_widget
    # plot_widget.update_spectrum(spectrum=spectra[0], mca_idx=1)
    with qtbot.waitSignal(mca_plot_widget.plot_changed):
        display._spectrum_channels[0].value_slot(spectra[0])
        display._spectrum_channels[1].value_slot(spectra[1])
    # Check that a PlotItem was created
    plot_item = mca_plot_widget.ui.plot_widget.getPlotItem()
    assert isinstance(plot_item, PlotItem)
    # Check that the spectrum was plotted
    data_items = plot_item.listDataItems()
    assert len(data_items) == 2
    # Check that previous plots get cleared
    spectra2 = np.random.default_rng(seed=1).integers(
        0, 65536, dtype=np.int_, size=(4, 1024)
    )
    with qtbot.waitSignal(mca_plot_widget.plot_changed):
        display._spectrum_channels[0].value_slot(spectra2[0])
    data_items = plot_item.listDataItems()
    assert len(data_items) == 2


def test_mca_selected_highlights(ffapp, qtbot, sim_vortex):
    """Is the spectrum highlighted when the element row is selected."""
    FireflyMainWindow()
    display = XRFDetectorDisplay(macros={"DEV": sim_vortex.name})
    mca_display = display.mca_displays[1]
    spectra = np.random.default_rng(seed=0).integers(
        0, 65536, dtype=np.int_, size=(4, 1024)
    )
    plot_widget = display.mca_plot_widget
    plot_widget.update_spectrum(1, spectra[0])
    plot_widget.update_spectrum(2, spectra[1])
    this_data_item = display.mca_plot_widget._data_items[2]
    other_data_item = display.mca_plot_widget._data_items[1]
    this_data_item.setOpacity(0.77)
    # Select this display and check if the spectrum is highlighted
    mca_display.selected.emit(True)
    assert this_data_item.opacity() == 1.0
    assert other_data_item.opacity() == 0.15
    # Hovering other rows should not affect the opacity
    display.mca_displays[0].enterEvent()
    assert this_data_item.opacity() == 0.55
    assert other_data_item.opacity() == 1.0
    display.mca_displays[0].leaveEvent()
    assert this_data_item.opacity() == 1.0
    assert other_data_item.opacity() == 0.15


def test_show_mca_region_visibility(ffapp, xrf_display):
    """Is the spectrum highlighted when the element row is selected."""
    # Check that the region is hidden at startup
    plot_widget = xrf_display.mca_plot_widget
    region = plot_widget.region(mca_num=2, roi_num=0)
    assert not region.isVisible()
    # Now highlight a spectrum, and confirm it is visible
    plot_widget.highlight_spectrum(mca_num=2, roi_num=0, hovered=True)
    assert region.isVisible()
    # assert region.brush.color().name() == "#ff7f0e"
    # Unhighlight and confirm it is invisible
    plot_widget.highlight_spectrum(mca_num=1, roi_num=0, hovered=False)
    assert not region.isVisible()


def test_show_roi_region(ffapp, xrf_display):
    """Is the spectrum highlighted when the element row is selected."""
    # Check that the region is hidden at startup
    plot_widget = xrf_display.roi_plot_widget
    hovered_region = plot_widget.region(mca_num=1, roi_num=1)
    plot_widget.select_roi(mca_num=1, roi_num=0, is_selected=True)
    selected_region = plot_widget.region(mca_num=1, roi_num=0)
    assert not hovered_region.isVisible()
    assert selected_region.isVisible()
    # Now highlight a spectrum, and confirm it is visible
    plot_widget.highlight_spectrum(mca_num=1, roi_num=1, hovered=True)
    assert hovered_region.isVisible()
    assert not selected_region.isVisible()
    # assert region.brush.color().name() == "#ff7f0e"
    # Unhighlight and confirm it is invisible
    plot_widget.highlight_spectrum(mca_num=1, roi_num=0, hovered=False)
    assert not hovered_region.isVisible()
    assert selected_region.isVisible()


def test_mca_region_channels(ffapp, xrf_display):
    """Are the channel access connections between the ROI selection region
    and the hi/lo channel PVs correct?

    """
    plot_widget = xrf_display.mca_plot_widget
    plot_widget.device_name = "vortex_me4"
    mca_display = xrf_display.mca_displays[1]
    mca_display._embedded_widget = mca_display.open_file(force=True)
    xrf_display.mca_selected(is_selected=True, mca_num=2)
    correct_address = "oph://vortex_me4.mcas.mca2.rois.roi0.hi_chan._write_pv"
    region = plot_widget.region(mca_num=2, roi_num=0)
    assert region.hi_channel.address == correct_address
    region.hi_channel.value_slot(108)
    assert region.getRegion()[1] == 108
    region.lo_channel.value_slot(47)
    assert region.getRegion()[0] == 47


def test_mca_copyall_button(ffapp, xrf_display, qtbot):
    xrf_display.mca_selected(is_selected=True, mca_num=2)
    assert xrf_display.ui.mca_copyall_button.isEnabled()
    # Set up ROI displays to test
    this_display = xrf_display.mca_displays[1]
    this_display._embedded_widget = this_display.open_file(force=True)
    other_display = xrf_display.mca_displays[0]
    other_display._embedded_widget = other_display.open_file(force=True)
    # Change the values on the MCA displays
    this_display.embedded_widget.ui.lower_lineedit.setText("111")
    this_display.embedded_widget.ui.upper_lineedit.setText("131")
    this_display.embedded_widget.ui.label_lineedit.setText("Ni Ka")
    # Copy to the other MCA display
    qtbot.mouseClick(xrf_display.ui.mca_copyall_button, QtCore.Qt.LeftButton)
    assert other_display.embedded_widget.ui.lower_lineedit.text() == "111"
    assert other_display.embedded_widget.ui.upper_lineedit.text() == "131"
    # Does the button get disabled on un-select?
    xrf_display.mca_selected(is_selected=False, mca_num=2)
    assert not xrf_display.ui.mca_copyall_button.isEnabled()


def test_roi_copyall_button(ffapp, xrf_display, qtbot):
    # Set up ROI rows embedded display widgets
    for disp in xrf_display.roi_displays:
        disp._embedded_widget = disp.open_file(force=True)
    # Select an ROI
    xrf_display.roi_selected(is_selected=True, roi_num=1)
    assert xrf_display.ui.roi_copyall_button.isEnabled()
    # Set up ROI displays to test
    this_display = xrf_display.roi_displays[1]
    this_display._embedded_widget = this_display.open_file(force=True)
    other_display = xrf_display.roi_displays[0]
    other_display._embedded_widget = other_display.open_file(force=True)
    # Change the values on the MCA displays
    this_display.embedded_widget.ui.lower_lineedit.setText("111")
    this_display.embedded_widget.ui.upper_lineedit.setText("131")
    this_display.embedded_widget.ui.label_lineedit.setText("Ni Ka")
    # Copy to the other ROI display
    qtbot.mouseClick(xrf_display.ui.roi_copyall_button, QtCore.Qt.LeftButton)
    assert other_display.embedded_widget.ui.lower_lineedit.text() == "111"
    assert other_display.embedded_widget.ui.upper_lineedit.text() == "131"
    # Does the button get disabled on un-select?
    xrf_display.roi_selected(is_selected=False, roi_num=1)
    assert not xrf_display.ui.roi_copyall_button.isEnabled()


def test_mca_enableall_checkbox(ffapp, xrf_display):
    checkbox = xrf_display.ui.mca_enableall_checkbox
    assert checkbox.checkState() == QtCore.Qt.PartiallyChecked
    assert checkbox.isTristate()
    for display in xrf_display.mca_displays:
        display._embedded_widget = display.open_file(force=True)
        assert not display.embedded_widget.ui.enabled_checkbox.checkState()
    # Set it to checked and make sure all the ROI checkboxes respond
    checkbox.setCheckState(QtCore.Qt.Checked)
    assert not checkbox.isTristate()
    for display in xrf_display.mca_displays:
        assert display.embedded_widget.ui.enabled_checkbox.isChecked()
    # Un-enable all, does it go back?
    checkbox.setCheckState(QtCore.Qt.Unchecked)
    for display in xrf_display.mca_displays:
        assert not display.embedded_widget.ui.enabled_checkbox.isChecked()


def test_roi_enableall_checkbox(ffapp, xrf_display):
    checkbox = xrf_display.ui.roi_enableall_checkbox
    assert checkbox.checkState() == QtCore.Qt.PartiallyChecked
    assert checkbox.isTristate()
    for display in xrf_display.roi_displays:
        display._embedded_widget = display.open_file(force=True)
        assert not display.embedded_widget.ui.enabled_checkbox.checkState()
    # Set it to checked and make sure all the ROI checkboxes respond
    checkbox.setCheckState(QtCore.Qt.Checked)
    assert not checkbox.isTristate()
    for display in xrf_display.roi_displays:
        assert display.embedded_widget.ui.enabled_checkbox.isChecked()
    # Un-enable all, does it go back?
    checkbox.setCheckState(QtCore.Qt.Unchecked)
    for display in xrf_display.roi_displays:
        assert not display.embedded_widget.ui.enabled_checkbox.isChecked()


def test_oneshot_acquisition(xrf_display, qtbot):
    """Check that clicking the one-shot acquisition button works."""
    with qtbot.waitSignal(xrf_display.triggers.start_erase) as val:
        xrf_display.ui.oneshot_button.click()
    # Check the accumulate box and see that we don't erase
    xrf_display.ui.accumulate_checkbox.setChecked(True)
    with qtbot.waitSignal(xrf_display.triggers.start_all) as val:
        xrf_display.ui.oneshot_button.click()


def test_continuous_acquisition(xrf_display, qtbot):
    """Check that clicking the one-shot acquisition button works."""
    with qtbot.waitSignal(xrf_display.triggers.start_erase) as val:
        xrf_display.ui.continuous_button.click()
    # Simulated acquisition finishing and then set up the next one
    with qtbot.waitSignal(xrf_display.triggers.start_erase) as val:
        xrf_display.triggers.acquiring_channel.value_slot(0)
