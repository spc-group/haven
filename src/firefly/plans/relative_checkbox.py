from qtpy.QtWidgets import QCheckBox

BLUE = "rgb(0, 186, 254)"
RED = "rgb(255, 98, 125)"


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
            f"padding: 4px; border-radius: 7px; background-color: {color}; "
        )

    @property
    def relative(self):
        return self.isChecked()
