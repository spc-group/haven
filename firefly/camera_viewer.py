import logging
import subprocess

import pyqtgraph
import pydm
import numpy as np

import haven
from firefly import display


log = logging.getLogger(__name__)


class CameraViewerDisplay(display.FireflyDisplay):
    def customize_device(self):
        addr = f"pva://{self.macros()['PREFIX']}Pva1:Image"
        self.image_channel = pydm.PyDMChannel(address=addr, value_slot=self.update_image)
        self.image_channel.connect()
    
    def customize_ui(self):
        self.caqtdm_button.clicked.connect(self.launch_caqtdm)
        # Create the pyqtgraph image viewer
        self.image_view = pyqtgraph.ImageView(parent=self)
        self.ui.left_column_layout.addWidget(self.image_view)

    def update_image(self, img):
        # Put the RGB axis at the end
        if img.ndim == 3:
            img = np.moveaxis(img, 0, -1)
        # Show the image data
        self.image_view.setImage(img)

    def ui_filename(self):
        return "camera_viewer.ui"

    def launch_caqtdm(self):
        # Determine for which IOC to launch caQtDM panels
        prefix = self.macros()["PREFIX"]
        prefix = prefix.strip(":")  # Remove trailing ':'s
        cmd = f"start_{prefix}_caqtdm"
        # Launch caQtDM for the given IOC
        log.info(f"Launching caQtDM: {cmd}")
        self.caqtdm_process = subprocess.Popen(cmd)
