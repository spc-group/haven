import logging
import subprocess

import haven
from firefly import display


log = logging.getLogger(__name__)


class CameraViewerDisplay(display.FireflyDisplay):
    def customize_ui(self):
        self.caqtdm_button.clicked.connect(self.launch_caqtdm)

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
