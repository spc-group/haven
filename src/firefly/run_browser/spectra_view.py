import logging
from pathlib import Path

from qtpy import QtWidgets, uic

log = logging.getLogger("run_browser")


class SpectraView(QtWidgets.QWidget):
    ui_file = Path(__file__).parent / "spectra_view.ui"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = uic.loadUi(self.ui_file, self)

    def plot(self, *args, **kwargs):
        log.exception(NotImplementedError())

    def clear(self):
        pass
