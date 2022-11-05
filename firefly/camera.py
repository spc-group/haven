from pathlib import Path
import datetime as dt
import subprocess
import logging
import os

import haven

from firefly import display


log = logging.getLogger(__name__)


class CameraDisplay(display.FireflyDisplay):
    prefix: str = ""
    properties_file: Path = Path("~/EPICS_AD_Viewer.properties").expanduser()

    def __init__(self, *, args=None, macros={}, **kwargs):
        self.prefix = macros.get("PREFIX", "")
        super().__init__(args=args, macros=macros, **kwargs)
    
    def customize_ui(self):
        self.imageJ_button.clicked.connect(self.launch_imageJ)

    def ui_filename(self):
        return "camera.ui"

    def launch_imageJ(self):
        # Set the imageJ properties file
        prefix = self.macros()["PREFIX"]
        with open(self.properties_file, mode='w') as fd:
            fd.write("#EPICS_AD_Viewer Properties\n")
            # Write a line to match "#Fri Nov 04 15:44:30 CDT 2022"
            now_string = dt.datetime.now().strftime("%a %b %d %H:%M:%S %Y")
            fd.write(f"#{now_string}\n")
            # Write out the PV prefix (e.g. "PVPrefix=25idgigeB\:image1\:")
            prefix_str = prefix.replace(':', '\\:')
            fd.write(f"PVPrefix={prefix_str}image1\\:\n")
        # Launch ImageJ with AD viewer plugin
        imagej_env = os.environ.copy()
        imagej_env["EPICS_CA_ARRAY_MAX_BYTES"] = "10000000"
        imagej_cmd = haven.load_config()["camera"]["imagej_command"]
        cmds = [imagej_cmd, "--run", "EPICS_AD_Viewer"]
        log.info(f"Launching ImageJ: {cmds}")
        self.imagej_process = subprocess.Popen(cmds, env=imagej_env)
