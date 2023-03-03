import haven
from firefly import display


class MotorDisplay(display.FireflyDisplay):
    caqtdm_ui_file = "/APSshare/epics/synApps_6_2_1/support/motor-R7-2-2//motorApp/op/ui/autoconvert/motorx_all.ui"

    def customize_ui(self):
        self.debug_button.clicked.connect(self.launch_caqtdm)

    def ui_filename(self):
        return "motor.ui"
