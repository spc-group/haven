import warnings
from pathlib import Path
from typing import Mapping, Sequence
import json

from pydm.widgets import PyDMEmbeddedDisplay
import haven
from haven import registry

from firefly import display, FireflyApplication


class FiltersDisplay(display.FireflyDisplay):
    filters: Sequence

    def ui_filename(self):
        return "filters.ui"

    def customize_device(self):
        filters = registry.findall(label="filters", allow_none=True)
        self.filters = sorted(filters, key=lambda dev: (dev.material.get(), dev.thickness.get()))

    def customize_ui(self):
        # Delete existing filter widgets
        for idx in reversed(range(self.filters_layout.count())):
            self.filters_layout.takeAt(idx).widget().deleteLater()
        # Add embedded displays for all the ion chambers
        self._filter_displays = []
        for idx, device in enumerate(self.filters):
            # Create the display object
            disp = PyDMEmbeddedDisplay(parent=self)
            disp.macros = json.dumps({"DEV": device.name})
            disp.filename = "filters_row.ui"
            # Add the Embedded Display to the Results Layout
            self.filters_layout.addWidget(disp)
            self._filter_displays.append(disp)

