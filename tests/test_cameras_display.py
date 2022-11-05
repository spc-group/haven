import haven

from firefly.main_window import FireflyMainWindow
from firefly.cameras import CamerasDisplay


def test_embedded_displays(qtbot):
    """Test that the embedded displays get loaded."""
    FireflyMainWindow()
    # Set up fake cameras
    camera = haven.Camera(prefix="camera_ioc", name="Camera A", labels={"cameras"})
    haven.registry.register(camera)
    # Load the display
    display = CamerasDisplay()
    # Check that the embedded display widgets get added correctly
    assert hasattr(display, "_camera_displays")
    assert len(display._camera_displays) == 1
    expected_macros = {"PREFIX": "camera_ioc", "DESC": "Camera A"}
    assert display._camera_displays[0].macros == expected_macros

    
