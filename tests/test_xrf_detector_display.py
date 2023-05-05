from firefly.main_window import FireflyMainWindow
from firefly.xrf_detector import XRFDetectorDisplay

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


