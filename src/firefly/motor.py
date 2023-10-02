import warnings

import haven
from firefly import display


class MotorDisplay(display.FireflyDisplay):
    caqtdm_ui_file = "/APSshare/epics/synApps_6_2_1/support/motor-R7-2-2/motorApp/op/ui/autoconvert/motorx_all.ui"

    def ui_filename(self):
        return "motor.ui"

    def launch_caqtdm(self):
        device = haven.registry.find(self.macros()["MOTOR"])
        P, M = device.prefix.split(":")[0:2]
        caqtdm_macros = {
            "P": f"{P}:",
            "M": M,
        }
        super().launch_caqtdm(macros=caqtdm_macros)
