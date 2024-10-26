import qtawesome as qta

from firefly import display


class TweakDisplay(display.FireflyDisplay):
    """A small set of widgets for tweaking a signal by specified value."""

    def customize_ui(self):
        # Set button icons
        direction = self.macros().get("DIRECTION", "").lower()
        if direction == "vertical":
            forward_icon = qta.icon("fa5s.arrow-up")
            reverse_icon = qta.icon("fa5s.arrow-down")
        elif direction == "horizontal":
            forward_icon = qta.icon("fa5s.arrow-right")
            reverse_icon = qta.icon("fa5s.arrow-left")
        else:
            forward_icon = qta.icon("fa5s.plus")
            reverse_icon = qta.icon("fa5s.minus")
        self.ui.forward_button.setIcon(forward_icon)
        self.ui.reverse_button.setIcon(reverse_icon)
        for btn in [self.ui.reverse_button, self.ui.forward_button]:
            btn.setText("")
        if hasattr(self.ui, "value_spin_box"):
            self.ui.value_spin_box.valueChanged.connect(self.update_press_values)

    def update_press_values(self, tweak_value):
        """Update the press values for the buttons.

        This makes them move in increments of the tweak value.

        """
        self.ui.reverse_button.pressValue = -tweak_value
        self.ui.forward_button.pressValue = tweak_value

    def ui_filename(self):
        return "tweak.ui"
