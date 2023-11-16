import logging
import subprocess
import sys

import matplotlib.pyplot as plt
import numpy as np
import pydm
import pyqtgraph

import haven
from firefly import display

np.set_printoptions(threshold=sys.maxsize)


log = logging.getLogger(__name__)


pyqtgraph.setConfigOption("imageAxisOrder", "row-major")


class AreaDetectorViewerDisplay(display.FireflyDisplay):
    caqtdm_ui_file: str = "/APSshare/epics/synApps_6_2_1/support/areaDetector-R3-12-1/ADAravis/aravisApp/op/ui/autoconvert/ADAravis.ui"
    image_is_new: bool = True

    def customize_device(self):
        device_name = name = self.macros()["AD"]
        device = haven.registry.find(device_name)
        self.device = device
        img_pv = device.pva.pv_name.get(as_string=True)
        addr = f"pva://{img_pv}"
        self.image_channel = pydm.PyDMChannel(
            address=addr, value_slot=self.update_image
        )
        self.image_channel.connect()

    def customize_ui(self):
        # Create the pyqtgraph image viewer
        self.image_view = self.ui.image_view
        # Connect signals for showing/hiding controls
        self.ui.settings_button.clicked.connect(self.toggle_controls)
        # Set some text about the camera
        use_name = getattr(self.device, "description", None) in [self.device.name, None]
        if use_name:
            lbl_text = self.device.cam.name
        else:
            lbl_text = f"{self.device.description} ({self.device.cam.prefix})"
        self.ui.camera_description_label.setText(lbl_text)
        self.setWindowTitle(lbl_text)

    def toggle_controls(self):
        # Show or hide the controls frame
        controls_frame = self.ui.controls_frame
        controls_frame.setVisible(not controls_frame.isVisible())

    def update_image(self, img):
        # For some reason the image comes out mishapen
        new_shape = img.shape[::-1]
        img = np.reshape(img, new_shape)
        # Show the image data
        self.image_view.setImage(
            img, autoRange=self.image_is_new, autoLevels=self.image_is_new
        )
        # Update the display to indicate that we don't need to update levels/scale in the future
        self.image_is_new = False

    def ui_filename(self):
        return "area_detector_viewer.ui"

    def launch_caqtdm(self):
        # Determine for which IOC to launch caQtDM panels
        cmd = f"start_{self.device.prefix.strip(':')}_caqtdm"
        # Launch caQtDM for the given IOC
        log.info(f"Launching caQtDM: {cmd}")
        self._open_caqtdm_subprocess(cmd)
