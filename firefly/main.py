import sys
from pathlib import Path

import display
from pydm import Display, PyDMApplication
from qtpy import QtWidgets
from qtpy.QtWidgets import QApplication

__all__ = ["MainDisplay"]


ui_dir = Path(__file__).parent


class MainDisplay(display.FireflyDisplay):
    def ui_filename(self):
        return "main.ui"
