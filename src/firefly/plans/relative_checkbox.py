from qtpy.QtWidgets import QCheckBox

RED = "rgb(255, 85, 127)"
BLUE = "rgb(0, 170, 255)"


class RelativeCheckbox(QCheckBox):
    """A checkbox to control whether a scan is relative or absolute.

    Has some additional markup to make it clear which is happening,
    and a standard way of reporting the scan type.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.change_background(self.isChecked())
        self.stateChanged.connect(self.change_background)

    def change_background(self, is_checked: bool):
        """
        Change the background color of the relative scan checkbox based on its state.
        """
        color = RED if is_checked else BLUE
        self.setStyleSheet(
            "padding: 3px; border-radius: 7px; " f"background-color: {color}"
        )

    @property
    def relative(self):
        return self.isChecked()
