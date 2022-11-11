import subprocess

import haven
from firefly import display


class MotorDisplay(display.FireflyDisplay):
    caqtdm_ui_file = "/APSshare/epics/synApps_6_2_1/support/motor-R7-2-2//motorApp/op/ui/autoconvert/motorx_all.ui"
    caqtdm_command = "/APSshare/bin/caQtDM -style plastique -noMsg"
    def customize_ui(self):
        self.debug_button.clicked.connect(self.launch_caqtdm)

    def launch_caqtdm(self):
        cmds = self.caqtdm_command.split()
        P, M = self.macros()['PREFIX'].split(":")
        cmds = [*cmds, "-macro", f"P={P}:,M={M}", self.caqtdm_ui_file]
        print(cmds)
        subprocess.Popen(cmds)

    def ui_filename(self):
        return "motor.ui"
        
