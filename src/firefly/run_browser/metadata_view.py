from pathlib import Path
from typing import Mapping

import yaml
from qtpy import QtWidgets, uic


class MetadataView(QtWidgets.QWidget):
    ui_file = Path(__file__).parent / "metadata_view.ui"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = uic.loadUi(self.ui_file, self)

    def display_metadata(self, metadata: Mapping):
        """Render metadata from runs into the metadata widget."""
        # Combine the metadata in a human-readable output
        text = ""
        for uid, md in metadata.items():
            text += f"# {uid}"
            text += yaml.dump(md)
            text += f"\n\n{'=' * 20}\n\n"
        self.ui.metadata_textedit.setPlainText(text)
