from qtpy import QtWidgets
from pprint import pprint as print

from .main_window import FireflyMainWindow


class VoltmetersWindow(FireflyMainWindow):
    def customize_ui(self):
        super().customize_ui()
        print(self.findChildren(QtWidgets.QPushButton))
        print(self.ui.centralwidget.findChild(QtWidgets.QPushButton, "btnGainDown"))
