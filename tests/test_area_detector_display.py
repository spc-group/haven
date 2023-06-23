import pyqtgraph
import numpy as np
import pydm
from unittest import mock

from firefly.main_window import FireflyMainWindow
from firefly.area_detector_viewer import AreaDetectorViewerDisplay
from haven.instrument.camera import load_cameras


def test_open_camera_viewer_actions(ffapp, qtbot, sim_camera):
    # Now get the cameras ready
    ffapp.prepare_camera_windows()
    assert hasattr(ffapp, "camera_actions")
    assert len(ffapp.camera_actions) == 1
    # Launch an action and see that a window opens
    list(ffapp.camera_actions.values())[0].trigger()
    assert "FireflyMainWindow_camera_s255id-gige-A" in ffapp.windows.keys()


def test_open_area_detector_viewer_actions(ffapp, qtbot, sim_camera):
    # Get the area detector parts ready
    ffapp.prepare_area_detector_windows()
    assert hasattr(ffapp, "area_detector_actions")
    assert len(ffapp.area_detector_actions) == 1
    # Launch an action and see that a window opens
    list(ffapp.area_detector_actions.values())[0].trigger()
    assert "FireflyMainWindow_area_detector_s255id-gige-A" in ffapp.windows.keys()


def test_image_plotting(ffapp, qtbot, sim_camera):
    FireflyMainWindow()
    display = AreaDetectorViewerDisplay(macros={"AD": sim_camera.name})
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


def test_caqtdm_window(ffapp, sim_camera):
    FireflyMainWindow()
    display = AreaDetectorViewerDisplay(macros={"AD": sim_camera.name})
    display._open_caqtdm_subprocess = mock.MagicMock()
    # Launch the caqtdm display
    display.launch_caqtdm()
    display._open_caqtdm_subprocess.assert_called_once_with(
        f"start_{sim_camera.prefix}_caqtdm"
    )
