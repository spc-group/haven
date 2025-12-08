from pathlib import Path

from qtpy import uic
from qtpy.QtWidgets import QWidget


class FlyScanWidget(QWidget):
    ui_file = Path(__file__).parent / "fly_scan.ui"

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.ui = uic.loadUi(self.ui_file, self)
