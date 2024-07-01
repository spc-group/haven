from firefly import display


class TweakDisplay(display.FireflyDisplay):
    """A small set of widgets for tweaking a signal by specified value."""

    def customize_ui(self):
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
