import qtawesome as qta

from firefly import display


class SlitsMotorDisplay(display.FireflyDisplay):
    def customize_ui(self):
        # Make the tweak buttons use proper arrow icons
        title = self.macros()["TITLE"]
        if "Size" in title:
            forward_icon = qta.icon("fa5s.plus")
            reverse_icon = qta.icon("fa5s.minus")
        elif "Vertical Center" in title:
            forward_icon = qta.icon("fa5s.arrow-up")
            reverse_icon = qta.icon("fa5s.arrow-down")
        else:
            forward_icon = qta.icon("fa5s.arrow-right")
            reverse_icon = qta.icon("fa5s.arrow-left")
        self.ui.tweak_forward_button.setIcon(forward_icon)
        self.ui.tweak_reverse_button.setIcon(reverse_icon)
        for btn in [self.ui.tweak_reverse_button, self.ui.tweak_forward_button]:
            btn.setText("")

    def ui_filename(self):
        return "slits_motor.ui"
