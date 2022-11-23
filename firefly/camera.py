from enum import IntEnum
from pathlib import Path
import datetime as dt
import subprocess
import logging
import os

import haven
from pydm.data_plugins.epics_plugin import EPICSPlugin
from qtpy.QtGui import QColor

from firefly import display


log = logging.getLogger(__name__)


class DetectorStates(IntEnum):
    IDLE = 0
    ACQUIRE = 1
    READOUT = 2
    CORRECT = 3
    SAVING = 4
    ABORTING = 5
    ERROR = 6
    WAITING = 7
    INITIALIZING = 8
    DISCONNECTED = 9
    ABORTED = 10


class AcquireStates(IntEnum):
    DONE = 0
    ACQUIRE = 1


class CameraDisplay(display.FireflyDisplay):
    prefix: str = ""
    properties_file: Path = Path("~/EPICS_AD_Viewer.properties").expanduser()

    def __init__(self, *, args=None, macros={}, **kwargs):
        self.prefix = macros.get("PREFIX", "")
        super().__init__(args=args, macros=macros, **kwargs)
        Connection = EPICSPlugin().connection_class
        self.detector_state = Connection(channel=None, pv=f"{self.prefix}cam1:DetectorState_RBV")
        self.acquire_state = Connection(channel=None, pv=f"{self.prefix}cam1:Acquire")
        # Color for various states
        self._ioc_disconnected_color = QColor(255, 255, 255)
        self._detector_disconnected_color = QColor(255, 0, 0)
        self._idle_color = QColor(0, 255, 0)
        self._acquire_color = QColor(255, 255, 0)
        
    def ui_filename(self):
        return "camera.ui"
    
    def customize_ui(self):
        self.imageJ_button.clicked.connect(self.launch_imageJ)
        self.caqtdm_button.clicked.connect(self.launch_caqtdm)

    def launch_caqtdm(self):
        # Determine for which IOC to launch caQtDM panels
        prefix = self.macros()["PREFIX"]
        prefix = prefix.strip(":")  # Remove trailing ':'s
        cmd = f"start_{prefix}_caqtdm"
        # Launch caQtDM for the given IOC
        log.info(f"Launching caQtDM: {cmd}")
        self.imagej_process = subprocess.Popen(cmd)

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

    def update_status_indicator(self):
        bit = self.camera_status_indicator._indicators[0]
        lbl = self.camera_status_label
        if not self.detector_state.connected:
            # IOC is not running or not available
            bit.setColor(self._ioc_disconnected_color)
            lbl.setVisible(False)
        elif self.detector_state.value == DetectorStates.IDLE:
            # Camera is idle
            bit.setColor(self._idle_color)
            lbl.setVisible(False)
        elif self.detector_state.value == DetectorStates.ACQUIRE:
            bit.setColor(self._acquire_color)
            lbl.setVisible(False)
        else:
            # Camera is disconnected or in an otherwise unexpected state
            bit.setColor(self._detector_disconnected_color)
            lbl.setVisible(True)
