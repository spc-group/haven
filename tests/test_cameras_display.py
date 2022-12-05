import json

import haven
from pydm.data_plugins.epics_plugin import EPICSPlugin
from pydm.widgets.channel import PyDMChannel
from qtpy.QtGui import QColor

from firefly.main_window import FireflyMainWindow
from firefly.cameras import CamerasDisplay
from firefly.camera import CameraDisplay, DetectorStates


macros = {"PREFIX": "camera_ioc:", "DESC": "Camera A"}


def test_embedded_displays(qtbot):
    """Test that the embedded displays get loaded."""
    FireflyMainWindow()
    # Set up fake cameras
    camera = haven.Camera(prefix="camera_ioc:", name="Camera A", labels={"cameras"})
    haven.registry.register(camera)
    # Load the display
    display = CamerasDisplay()
    # Check that the embedded display widgets get added correctly
    assert hasattr(display, "_camera_displays")
    assert len(display._camera_displays) == 1
    # Check the embedded display macros
    # assert isinstance(display._camera_displays[0].macros, dict)
    expected_macros = {"PREFIX": "camera_ioc:", "DESC": "Camera A"}
    assert json.loads(display._camera_displays[0].macros) == expected_macros


def test_camera_channel_status(qtbot):
    """Test that the camera status indicator responds to camera connection
    status PV.

    """
    FireflyMainWindow()
    display = CameraDisplay(macros=macros)
    # Check that the pydm connections have been made to EPICS
    assert isinstance(display.detector_state, PyDMChannel)
    assert display.detector_state.address == "camera_ioc:cam1:DetectorState_RBV"


def test_set_status_byte(qtbot):
    FireflyMainWindow()
    display = CameraDisplay(macros=macros)
    display.show()
    # All devices are disconnected
    state = display.detector_state
    byte = display.camera_status_indicator
    bit = byte._indicators[0]
    label = display.camera_status_label
    # Set the color to something else, then check that it gets set back to white
    bit.setColor(QColor(255, 0, 0))
    # Simulated the IOC being disconnected
    display.update_camera_connection(False)
    assert bit._brush.color().getRgb() == (255, 255, 255, 255)
    assert not label.isVisible(), "State label should be hidden by default"
    # Make the signals connected and see that it's green
    display.update_camera_connection(True)
    display.update_camera_state(DetectorStates.IDLE)
    assert bit._brush.color().getRgb() == (0, 255, 0, 255)
    assert not label.isVisible(), "State label should be hidden by default"
    # Make the camera be disconnected and see if it's red
    display.update_camera_state(DetectorStates.DISCONNECTED)
    assert bit._brush.color().getRgb() == (255, 0, 0, 255)
    assert  label.isVisible(), "State label should be visible when disconnected"
    # Make the camera be acquiring and see if it's yellow
    display.update_camera_state(DetectorStates.ACQUIRE)
    assert bit._brush.color().getRgb() == (255, 255, 0, 255)
    assert not label.isVisible(), "State label should be hidden by default"
