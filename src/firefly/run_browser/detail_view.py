import logging
from pathlib import Path
from typing import Mapping

from qtpy import QtWidgets, uic
from qtpy.QtCore import Slot

log = logging.getLogger(__name__)


class DetailView(QtWidgets.QWidget):
    ui_file = Path(__file__).parent / "detail_view.ui"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = uic.loadUi(self.ui_file, self)
        # Connect internal signals/slots

    @Slot()
    @Slot(dict)
    def plot(self, dataframes: Mapping | None = None):
        """Take loaded run data and plot it.

        Parameters
        ==========
        dataframes
          Dictionary with pandas series for each run with run UIDs for
          keys.

        """
        # self.ui.lineplot_view.plot(dataframes)
