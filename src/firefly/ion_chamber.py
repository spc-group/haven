from firefly import display


class IonChamberDisplay(display.FireflyDisplay):
    """A GUI window for changing settings in an ion chamber."""

    def ui_filename(self):
        return "ion_chamber.ui"
