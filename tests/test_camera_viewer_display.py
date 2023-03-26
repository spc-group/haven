from haven.instrument.camera import load_cameras


def test_open_camera_viewer_actions(ffapp, qtbot):
    assert hasattr(ffapp, 'camera_actions')
    assert len(ffapp.camera_actions) == 0
    # Now get the cameras ready
    load_cameras()
    ffapp.prepare_camera_windows()
    assert len(ffapp.camera_actions) > 0
    # Launch an action and see that a window opens
    ffapp.camera_actions[0].trigger()
    assert "FireflyMainWindow_camera_s25id-gige-A" in ffapp.windows.keys()



