import json
import logging

from pydm.widgets import PyDMEmbeddedDisplay
import haven

from firefly import display


log = logging.getLogger(__name__)


class CamerasDisplay(display.FireflyDisplay):
    _camera_displays = []

    def __init__(self, args=None, macros={}, **kwargs):
        self._camera_displays = []
        super().__init__(args=args, macros=macros, **kwargs)

    def customize_ui(self):
        # Delete existing camera widgets
        for idx in reversed(range(self.cameras_layout.count())):
            self.cameras_layout.takeAt(idx).widget().deleteLater()
        # Add embedded displays for all the ion chambers
        try:
            cameras = haven.registry.findall(label="cameras")
        except haven.exceptions.ComponentNotFound:
            log.warning(
                "No cameras found, [Detectors] -> [Cameras] panel will be empty."
            )
            cameras = []
        for cam in sorted(cameras, key=lambda c: c.name):
            disp = PyDMEmbeddedDisplay(parent=self)
            disp.macros = json.dumps(
                {
                    "PREFIX": cam.prefix,
                    "DESC": cam.description,
                }
            )
            disp.filename = "camera.py"
            # Add the Embedded Display to the Results Layout
            self.cameras_layout.addWidget(disp)
            self._camera_displays.append(disp)

    def ui_filename(self):
        return "cameras.ui"
