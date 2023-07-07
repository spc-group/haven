from qtpy import QtWidgets
import qtawesome as qta


class RevealButton(QtWidgets.QPushButton):
    closed_icon = qta.icon("fa5s.angle-up")
    open_icon = qta.icon("fa5s.angle-down")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set up signals
        self.toggled.connect(self.toggle_icon)
        self.toggle_icon(self.isChecked())

    def toggle_icon(self, checked):
        if checked:
            self.setIcon(self.open_icon)
        else:
            self.setIcon(self.closed_icon)
