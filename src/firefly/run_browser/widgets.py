import logging
from typing import Optional, Sequence

from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QFileDialog, QWidget

log = logging.getLogger(__name__)


class FiltersWidget(QWidget):
    returnPressed = Signal()

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        # Check for return keys pressed
        if event.key() in [Qt.Key_Enter, Qt.Key_Return]:
            self.returnPressed.emit()


class ExportDialog(QFileDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFileMode(QFileDialog.FileMode.AnyFile)
        self.setAcceptMode(QFileDialog.AcceptSave)

    def ask(self, mimetypes: Optional[Sequence[str]] = None):
        """Get the name of the file to save for exporting."""
        self.setMimeTypeFilters(mimetypes)
        # Show the file dialog
        if self.exec_() == QFileDialog.Accepted:
            return self.selectedFiles()
        else:
            return None
