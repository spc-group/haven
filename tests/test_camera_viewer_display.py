import pyqtgraph
import numpy as np
import pydm

from firefly.main_window import FireflyMainWindow
from firefly.camera_viewer import CameraViewerDisplay
from haven.instrument.camera import load_cameras


def test_open_camera_viewer_actions(ffapp, qtbot):
    assert hasattr(ffapp, 'camera_actions')
    # Now get the cameras ready
    load_cameras()
    ffapp.prepare_camera_windows()
    assert len(ffapp.camera_actions) == 1
    # Launch an action and see that a window opens
    ffapp.camera_actions[0].trigger()
    assert "FireflyMainWindow_camera_s25id-gige-A" in ffapp.windows.keys()


def test_image_plotting(ffapp, qtbot):
    FireflyMainWindow()
    display = CameraViewerDisplay(macros={"PREFIX": "99idSimDet:",
                                          "DESC": "Simulated detector"})
    assert isinstance(display.image_view, pyqtgraph.ImageView)
    assert isinstance(display.image_channel, pydm.PyDMChannel)
    # Give it some grayscale data
    source_img = np.random.randint(0, 256, size=(54, 64))
    # For some reason, PyDMConnection mis-shapes the data
    reshape_img = np.reshape(source_img, source_img.shape[::-1])
    display.image_channel.value_slot(reshape_img)
    # See if we get a plottable image out
    new_image = display.image_view.getImageItem()
    assert new_image.image is not None
    assert new_image.image.shape == (54, 64)
    np.testing.assert_equal(new_image.image, source_img)
    # Give it some RGB data
    source_img = np.random.randint(0, 256, size=(54, 64, 3))
    # For some reason, PyDMConnection mis-shapes the data
    reshape_img = np.reshape(source_img, source_img.shape[::-1])
    display.image_channel.value_slot(reshape_img)
    # See if we get a plottable image out
    new_image = display.image_view.getImageItem()
    assert new_image.image.shape == (54, 64, 3)
    display.image_channel.disconnect()
