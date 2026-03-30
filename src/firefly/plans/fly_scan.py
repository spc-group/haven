from pathlib import Path

from guarneri import Registry
from qtpy import uic
from qtpy.QtWidgets import QWidget


class FlyScanWidget(QWidget):
    ui_file = Path(__file__).parent / "fly_scan.ui"

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.ui = uic.loadUi(self.ui_file, self)

    async def update_devices(self, registry: Registry):
        """Update the list of available flyer controllers."""
        controllers = registry.findall("flyer_controllers", allow_none=True)
        controller_names = [ctrl.name for ctrl in controllers]
        self.ui.controller_list.clear()
        self.ui.controller_list.addItems(controller_names)
