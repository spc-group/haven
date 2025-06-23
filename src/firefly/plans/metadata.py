from pathlib import Path
from typing import Any

from qtpy import QtWidgets, uic
from qtpy.QtWidgets import QWidget

from firefly.plans.util import is_valid_value


class MetadataWidget(QWidget):
    ui_file = Path(__file__).parent / "metadata.ui"

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.ui = uic.loadUi(self.ui_file, self)
        self.ui.purpose_combo_box.lineEdit().setPlaceholderText(
            "e.g. commissioning, alignment…"
        )
        self.ui.purpose_combo_box.setCurrentText("")
        self.ui.standard_check_box.clicked.connect(self.confirm_public_standard)

    def confirm_public_standard(self, is_checked):
        """If 'Is standard' is checked, warn that the data will be public."""
        if is_checked:
            response = QtWidgets.QMessageBox.warning(
                self,
                "Notice",
                "When checking this option, you acknowledge that these data may be made publicly available.",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if response != QtWidgets.QMessageBox.Yes:
                self.ui.standard_check_box.setChecked(False)

    def metadata(self) -> dict[str, Any]:
        md = {
            "sample_name": self.ui.sample_line_edit.text(),
            "scan_name": self.scan_line_edit.text(),
            "purpose": self.purpose_combo_box.currentText(),
            "notes": self.notes_text_edit.toPlainText(),
            "sample_formula": self.formula_line_edit.text(),
            "is_standard": self.standard_check_box.isChecked(),
        }
        # Only include metadata that isn't an empty string
        md = {key: val for key, val in md.items() if is_valid_value(val)}
        return md
