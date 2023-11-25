import qtawesome as qta

from firefly import display


class SlitsMotorDisplay(display.FireflyDisplay):
    def customize_ui(self):
        # Make the tweak buttons use proper arrow icons
        self.ui.tweak_forward_button.setIcon(qta.icon("fa5s.arrow-right"))
        self.ui.tweak_reverse_button.setIcon(qta.icon("fa5s.arrow-left"))
        for btn in [self.ui.tweak_reverse_button, self.ui.tweak_forward_button]:
            btn.setText("")
        
    def ui_filename(self):
        return "slits_motor.ui"
