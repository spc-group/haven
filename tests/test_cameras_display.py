import json

import haven
from pydm.data_plugins.epics_plugin import EPICSPlugin
from qtpy.QtGui import QColor

from firefly.main_window import FireflyMainWindow
from firefly.cameras import CamerasDisplay
from firefly.camera import CameraDisplay, DetectorStates


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


def test_camera_connection_status(qtbot):
    """Test that the camera status indicator responds to camera connection
    status PV.

    """
    FireflyMainWindow()
    macros = {"PREFIX": "camera_ioc:", "DESC": "Camera A"}
    display = CameraDisplay(macros=macros)
    # Check that the pydm connections have been made to EPICS
    assert isinstance(display.detector_state, EPICSPlugin.connection_class)
    assert display.detector_state.pv.pvname == "camera_ioc:cam1:DetectorState_RBV"
    assert isinstance(display.acquire_state, EPICSPlugin.connection_class)
    assert display.acquire_state.pv.pvname == "camera_ioc:cam1:Acquire"

def test_set_status_byte(qtbot):
    FireflyMainWindow()
    display = CameraDisplay()
    display.show()
    # All devices are disconnected
    assert not display.detector_state.connected
    assert not display.acquire_state.connected
    byte = display.camera_status_indicator
    bit = byte._indicators[0]
    label = display.camera_status_label
    # Set the color to something else, then check that it gets set back to white
    bit.setColor(QColor(255, 0, 0))
    display.update_status_indicator()
    assert bit._brush.color().getRgb() == (255, 255, 255, 255)
    assert not label.isVisible(), "State label should be hidden by default"
    # Make the signals connected and see that it's green
    display.detector_state.connected = True
    display.acquire_state.connected = True
    display.detector_state.value = DetectorStates.IDLE
    display.update_status_indicator()
    assert bit._brush.color().getRgb() == (0, 255, 0, 255)
    assert not label.isVisible(), "State label should be hidden by default"
    # Make the camera be disconnected and see if it's red
    display.detector_state.value = DetectorStates.DISCONNECTED
    display.update_status_indicator()
    assert bit._brush.color().getRgb() == (255, 0, 0, 255)
    assert  label.isVisible(), "State label should be visible when disconnected"
    # Make the camera be acquiring and see if it's yellow
    display.detector_state.value = DetectorStates.ACQUIRE
    display.update_status_indicator()
    assert bit._brush.color().getRgb() == (255, 255, 0, 255)
    assert not label.isVisible(), "State label should be hidden by default"
