import logging
import subprocess

import pyqtgraph
import pydm
import numpy as np
import matplotlib.pyplot as plt

import haven
from firefly import display

import sys

np.set_printoptions(threshold=sys.maxsize)


log = logging.getLogger(__name__)


pyqtgraph.setConfigOption("imageAxisOrder", "row-major")


class CameraViewerDisplay(display.FireflyDisplay):
    image_is_new: bool = True

    def customize_device(self):
        device_name = name=self.macros()["CAMERA"]
        camera = haven.registry.find(device_name)
        self.camera = camera
        img_pv = camera.pva.pv_name.get(as_string=True)
        addr = f"pva://{img_pv}"
        self.image_channel = pydm.PyDMChannel(
            address=addr, value_slot=self.update_image
        )
        self.image_channel.connect()

    def customize_ui(self):
        self.caqtdm_button.clicked.connect(self.launch_caqtdm)
        # Create the pyqtgraph image viewer
        self.image_view = pyqtgraph.ImageView(parent=self)
        self.ui.left_column_layout.addWidget(self.image_view)
        # Connect signals for showing/hiding controls
        self.ui.settings_button.clicked.connect(self.toggle_controls)

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
        return "camera_viewer.ui"

    def launch_caqtdm(self):
        # Determine for which IOC to launch caQtDM panels
        cmd = f"start_{self.camera.prefix}_caqtdm"
        # Launch caQtDM for the given IOC
        log.info(f"Launching caQtDM: {cmd}")
        self._open_caqtdm_subprocess(cmd)
