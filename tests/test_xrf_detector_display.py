def test_open_xrf_detector_viewer_actions(ffapp, qtbot, sim_vortex):
    # Get the area detector parts ready
    ffapp.prepare_xrf_detector_windows()
    assert hasattr(ffapp, "xrf_detector_actions")
    assert len(ffapp.xrf_detector_actions) == 1
    # Launch an action and see that a window opens
    ffapp.xrf_detector_actions[0].trigger()
    assert "FireflyMainWindow_xrf_detector_vortex_me4" in ffapp.windows.keys()
