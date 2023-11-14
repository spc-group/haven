from qtpy import QtWidgets
from qtpy.QtGui import QIcon
import qtawesome as qta


class RevealButton(QtWidgets.QPushButton):
    closed_icon: QIcon
    open_icon: QIcon

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Load icons
        self.closed_icon = qta.icon("fa5s.angle-up")
        self.open_icon = qta.icon("fa5s.angle-down")
        # Set up signals
        self.toggled.connect(self.toggle_icon)
        self.toggle_icon(self.isChecked())

    def toggle_icon(self, checked):
        if checked:
            self.setIcon(self.open_icon)
        else:
            self.setIcon(self.closed_icon)
