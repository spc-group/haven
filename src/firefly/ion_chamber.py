import warnings

import haven
from firefly import display


class IonChamberDisplay(display.FireflyDisplay):
    def ui_filename(self):
        return "ion_chamber.ui"
