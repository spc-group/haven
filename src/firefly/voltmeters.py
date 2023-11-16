import json
import logging
import warnings
from typing import Mapping, Optional, Sequence

import qtawesome as qta
from pydm.widgets import PyDMEmbeddedDisplay
from qtpy import QtWidgets

import haven
from firefly import display

# from .voltmeter import VoltmeterDisplay


log = logging.getLogger(__name__)


class VoltmetersDisplay(display.FireflyDisplay):
    _ion_chamber_displays = []
    caqtdm_scaler_ui_file: str = "/net/s25data/xorApps/ui/scaler32_full_offset.ui"
    caqtdm_mcs_ui_file: str = "/APSshare/epics/synApps_6_2_1/support/mca-R7-9//mcaApp/op/ui/autoconvert/SIS38XX.ui"

    def __init__(
        self,
        args: Optional[Sequence] = None,
        macros: Mapping = {},
        **kwargs,
    ):
        ion_chambers = haven.registry.findall(label="ion_chambers", allow_none=True)
        self.ion_chambers = sorted(ion_chambers, key=lambda c: c.ch_num)
        macros_ = macros.copy()
        if "SCALER" not in macros_.keys():
            macros_["SCALER"] = self.ion_chambers[0].scaler_prefix
        super().__init__(args=args, macros=macros_, **kwargs)

    def prepare_caqtdm_actions(self):
        """Create QActions for opening scaler/MCS caQtDM panels.

        Creates two actions, one for the scaler counter and one for
        the multi-channel-scaler (MCS) controls.

        """
        self.caqtdm_actions = []
        # Create an action for launching the scaler caQtDM file
        action = QtWidgets.QAction(self)
        action.setObjectName("launch_scaler_caqtdm_action")
        action.setText("Scaler caQtDM")
        action.triggered.connect(self.launch_scaler_caqtdm)
        action.setIcon(qta.icon("fa5s.wrench"))
        action.setToolTip("Launch the caQtDM panel for the scaler.")
        self.caqtdm_actions.append(action)
        # Create an action for launching the MCS caQtDM file
        action = QtWidgets.QAction(self)
        action.setObjectName("launch_mcs_caqtdm_action")
        action.setText("MCS caQtDM")
        action.triggered.connect(self.launch_mcs_caqtdm)
        action.setIcon(qta.icon("fa5s.wrench"))
        action.setToolTip(
            "Launch the caQtDM panel for the multi-channel scaler controls."
        )
        self.caqtdm_actions.append(action)

    def customize_ui(self):
        # Delete existing voltmeter widgets
        for idx in reversed(range(self.voltmeters_layout.count())):
            self.voltmeters_layout.takeAt(idx).widget().deleteLater()
        # Add embedded displays for all the ion chambers
        self._ion_chamber_displays = []
        for idx, ic in enumerate(self.ion_chambers):
            # Add a separator
            if idx > 0:
                line = QtWidgets.QFrame(self.ui)
                line.setObjectName("line")
                # line->setGeometry(QRect(140, 80, 118, 3));
                line.setFrameShape(QtWidgets.QFrame.HLine)
                line.setFrameShadow(QtWidgets.QFrame.Sunken)
                self.voltmeters_layout.addWidget(line)
            # Create the display object
            disp = PyDMEmbeddedDisplay(parent=self)
            disp.macros = json.dumps({"IC": ic.name})
            disp.filename = "voltmeter.py"
            # Add the Embedded Display to the Results Layout
            self.voltmeters_layout.addWidget(disp)
            self._ion_chamber_displays.append(disp)

    def ui_filename(self):
        return "voltmeters.ui"

    def launch_scaler_caqtdm(self):
        device = self.ion_chambers[0]
        caqtdm_macros = {
            "P": f"{device.scaler_prefix}:",
            "S": "scaler1",
        }
        super().launch_caqtdm(macros=caqtdm_macros, ui_file=self.caqtdm_scaler_ui_file)

    def launch_mcs_caqtdm(self):
        device = self.ion_chambers[0]
        caqtdm_macros = {
            "P": f"{device.scaler_prefix}:",
        }
        super().launch_caqtdm(macros=caqtdm_macros, ui_file=self.caqtdm_mcs_ui_file)
