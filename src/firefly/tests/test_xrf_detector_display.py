import numpy as np
import pytest
from pyqtgraph import PlotItem
from qtpy import QtCore

from firefly.xrf_detector import XRFDetectorDisplay
from firefly.xrf_roi import XRFROIDisplay

detectors = ["dxp", "xspress"]


@pytest.fixture()
def xrf_display(request, qtbot):
    """Parameterized fixture for creating a display based on a specific
    detector class.

    """
    # Figure out which detector we're using
    det = request.getfixturevalue(request.param)
    # Create the display
    display = XRFDetectorDisplay(macros={"DEV": det.name})
    qtbot.addWidget(display)
    # Set sensible starting values
    spectra = np.random.default_rng(seed=0).integers(
        0, 65536, dtype=np.int_, size=(4, 1024)
    )
    plot_widget = display.mca_plot_widget
    plot_widget.update_spectrum(0, spectra[0])
    plot_widget.update_spectrum(1, spectra[1])
    plot_widget.update_spectrum(2, spectra[2])
    plot_widget.update_spectrum(3, spectra[3])
    yield display


@pytest.mark.parametrize("xrf_display", detectors, indirect=True)
def test_roi_widgets(xrf_display):
    xrf_display.draw_roi_widgets(2)
    # Check that the widgets were drawn
    assert len(xrf_display.roi_displays) == xrf_display.device.num_rois
    disp = xrf_display.roi_displays[0]


@pytest.mark.parametrize("xrf_display", detectors, indirect=True)
def test_roi_element_comboboxes(xrf_display):
    # Check that the comboboxes have the right number of entries
    element_cb = xrf_display.ui.mca_combobox
    assert element_cb.count() == xrf_display.device.num_elements
    roi_cb = xrf_display.ui.roi_combobox
    assert roi_cb.count() == xrf_display.device.num_rois


@pytest.mark.parametrize("det_fixture", detectors)
def test_roi_selection(qtbot, det_fixture, request):
    det = request.getfixturevalue(det_fixture)
    display = XRFROIDisplay(macros={"DEV": det.name, "NUM": 2, "MCA": 2, "ROI": 2})
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


@pytest.mark.parametrize("xrf_display", detectors, indirect=True)
def test_all_rois_selection(xrf_display):
    """Are all the other ROIs disabled when one is selected?"""
    roi_display = xrf_display.roi_displays[0]
    # Pretend an ROI display was selected
    roi_display.selected.emit(True)
    # Check that a different ROI display was disabled
    assert not xrf_display.roi_displays[1].isEnabled()


@pytest.mark.parametrize("xrf_display", detectors, indirect=True)
def test_all_mcas_selection(xrf_display):
    """Are all the other ROIs disabled when one is selected?"""
    mca_display = xrf_display.mca_displays[0]
    # Pretend an ROI display was selected
    mca_display.selected.emit(True)
    # Check that a different ROI display was disabled
    assert not xrf_display.mca_displays[1].isEnabled()


@pytest.mark.parametrize("xrf_display", detectors, indirect=True)
def test_update_roi_spectra(qtbot, xrf_display):
    spectra = np.random.default_rng(seed=0).integers(
        0, 65536, dtype=np.int_, size=(4, 1024)
    )
    roi_plot_widget = xrf_display.ui.roi_plot_widget
    with qtbot.waitSignal(roi_plot_widget.plot_changed):
        xrf_display._spectrum_channels[0].value_slot(spectra[0])
        xrf_display._spectrum_channels[1].value_slot(spectra[1])
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
        xrf_display._spectrum_channels[0].value_slot(spectra2[0])
    data_items = plot_item.listDataItems()
    assert len(data_items) == 1


@pytest.mark.parametrize("xrf_display", detectors, indirect=True)
def test_update_mca_spectra(xrf_display, qtbot):
    spectra = np.random.default_rng(seed=0).integers(
        0, 65536, dtype=np.int_, size=(4, 1024)
    )
    mca_plot_widget = xrf_display.ui.mca_plot_widget
    # Check that a PlotItem was created in the fixture
    plot_item = mca_plot_widget.ui.plot_widget.getPlotItem()
    assert isinstance(plot_item, PlotItem)
    # Clear the data items so we can test them later
    plot_item.clear()
    # plot_widget.update_spectrum(spectrum=spectra[0], mca_idx=1)
    with qtbot.waitSignal(mca_plot_widget.plot_changed):
        xrf_display._spectrum_channels[0].value_slot(spectra[0])
        xrf_display._spectrum_channels[1].value_slot(spectra[1])
    # Check that the spectrum was plotted
    data_items = plot_item.listDataItems()
    assert len(data_items) == 2
    # Check that previous plots get cleared
    spectra2 = np.random.default_rng(seed=1).integers(
        0, 65536, dtype=np.int_, size=(4, 1024)
    )
    with qtbot.waitSignal(mca_plot_widget.plot_changed):
        xrf_display._spectrum_channels[0].value_slot(spectra2[0])
    data_items = plot_item.listDataItems()
    assert len(data_items) == 2


@pytest.mark.parametrize("xrf_display", detectors, indirect=True)
def test_mca_selected_highlights(qtbot, xrf_display):
    """Is the spectrum highlighted when the element row is selected."""
    mca_display = xrf_display.mca_displays[1]
    spectra = np.random.default_rng(seed=0).integers(
        0, 65536, dtype=np.int_, size=(4, 1024)
    )
    plot_widget = xrf_display.mca_plot_widget
    plot_widget.update_spectrum(0, spectra[0])
    plot_widget.update_spectrum(1, spectra[1])
    this_data_item = xrf_display.mca_plot_widget._data_items[1]
    other_data_item = xrf_display.mca_plot_widget._data_items[0]
    this_data_item.setOpacity(0.77)
    # Select this display and check if the spectrum is highlighted
    mca_display.selected.emit(True)
    assert this_data_item.opacity() == 1.0
    assert other_data_item.opacity() == 0.15
    # Hovering other rows should not affect the opacity
    xrf_display.mca_displays[0].enterEvent()
    assert this_data_item.opacity() == 0.55
    assert other_data_item.opacity() == 1.0
    xrf_display.mca_displays[0].leaveEvent()
    assert this_data_item.opacity() == 1.0
    assert other_data_item.opacity() == 0.15


@pytest.mark.parametrize("xrf_display", detectors, indirect=True)
def test_show_mca_region_visibility(xrf_display):
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


@pytest.mark.parametrize("xrf_display", detectors, indirect=True)
def test_show_roi_region(xrf_display):
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


@pytest.mark.parametrize("xrf_display", detectors, indirect=True)
def test_mca_region_channels(xrf_display):
    """Are the channel access connections between the ROI selection region
    and the hi/lo channel PVs correct?

    """
    plot_widget = xrf_display.mca_plot_widget
    plot_widget.device_name = "vortex_me4"
    mca_display = xrf_display.mca_displays[1]
    mca_display._embedded_widget = mca_display.open_file(force=True)
    xrf_display.mca_selected(is_selected=True, mca_num=2)
    correct_address = "haven://vortex_me4.mcas.mca2.rois.roi0.hi_chan"
    region = plot_widget.region(mca_num=2, roi_num=0)
    assert region.hi_channel.address == correct_address
    region.hi_channel.value_slot(108)
    assert region.getRegion()[1] == 108
    region.lo_channel.value_slot(47)
    assert region.getRegion()[0] == 47


@pytest.mark.parametrize("xrf_display", detectors, indirect=True)
def test_mca_copyall_button(xrf_display, qtbot):
    xrf_display.mca_selected(is_selected=True, mca_num=1)
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


@pytest.mark.parametrize("xrf_display", detectors, indirect=True)
def test_roi_copyall_button(xrf_display, qtbot):
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


@pytest.mark.parametrize("xrf_display", detectors, indirect=True)
def test_mca_enableall_checkbox(xrf_display):
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


@pytest.mark.parametrize("xrf_display", detectors, indirect=True)
def test_roi_enableall_checkbox(xrf_display):
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
