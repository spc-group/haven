import time
from ophyd import Kind

import numpy as np
from pyqtgraph import PlotItem

from firefly.main_window import FireflyMainWindow
from firefly.xrf_detector import XRFDetectorDisplay, XRFPlotWidget
from firefly.xrf_roi import XRFROIDisplay


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
    display = XRFROIDisplay(macros={"DEV": sim_vortex.name,
                                    "NUM": 2,
                                    "MCA": 2,
                                    "ROI": 2})
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
    spectra = np.random.default_rng(seed=0).integers(0, 65536, dtype=np.int_, size=(4, 1024))
    roi_plot_widget = display.ui.roi_plot_widget
    assert roi_plot_widget.ui.plot_widget.getItem(0, 0) is None
    # plot_widget.update_spectrum(spectrum=spectra[0], mca_idx=1)
    with qtbot.waitSignal(roi_plot_widget.plot_changed):
        display._spectrum_channels[0].value_slot(spectra[0])
        display._spectrum_channels[1].value_slot(spectra[1])
    # Check that a PlotItem was created
    plot_item = roi_plot_widget.ui.plot_widget.getItem(0, 0)
    assert isinstance(plot_item, PlotItem)
    # Check that the spectrum was plotted
    data_items = plot_item.listDataItems()
    assert len(data_items) == 2
    # Check that previous plots get cleared
    spectra2 = np.random.default_rng(seed=1).integers(0, 65536, dtype=np.int_, size=(4, 1024))
    with qtbot.waitSignal(roi_plot_widget.plot_changed):
        display._spectrum_channels[0].value_slot(spectra2[0])
    data_items = plot_item.listDataItems()
    assert len(data_items) == 2


def test_update_mca_spectra(ffapp, qtbot, sim_vortex):
    FireflyMainWindow()
    display = XRFDetectorDisplay(macros={"DEV": sim_vortex.name})
    spectra = np.random.default_rng(seed=0).integers(0, 65536, dtype=np.int_, size=(4, 1024))
    mca_plot_widget = display.ui.mca_plot_widget
    assert mca_plot_widget.ui.plot_widget.getItem(0, 0) is None
    # plot_widget.update_spectrum(spectrum=spectra[0], mca_idx=1)
    with qtbot.waitSignal(mca_plot_widget.plot_changed):
        display._spectrum_channels[0].value_slot(spectra[0])
        display._spectrum_channels[1].value_slot(spectra[1])
    # Check that a PlotItem was created
    plot_item = mca_plot_widget.ui.plot_widget.getItem(0, 0)
    assert isinstance(plot_item, PlotItem)
    # Check that the spectrum was plotted
    data_items = plot_item.listDataItems()
    assert len(data_items) == 2
    # Check that previous plots get cleared
    spectra2 = np.random.default_rng(seed=1).integers(0, 65536, dtype=np.int_, size=(4, 1024))
    with qtbot.waitSignal(mca_plot_widget.plot_changed):
        display._spectrum_channels[0].value_slot(spectra2[0])
    data_items = plot_item.listDataItems()
    assert len(data_items) == 2
