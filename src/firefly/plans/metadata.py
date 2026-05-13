from pathlib import Path
from typing import Any

from qtpy import QtWidgets, uic
from qtpy.QtWidgets import QWidget

from firefly.display import SampleMetadata
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
            "sample_name": self.ui.sample_combo_box.currentText(),
            "scan_name": self.scan_line_edit.text(),
            "purpose": self.purpose_combo_box.currentText(),
            "notes": self.notes_text_edit.toPlainText(),
            "sample_formula": self.formula_combo_box.currentText(),
            "dm_exp": self.dm_experiment_combo_box.currentText(),
        }
        if self.standard_check_box.isChecked():
            md["is_standard"] = True
        # Only include metadata that isn't an empty string
        md = {key: val for key, val in md.items() if is_valid_value(val)}
        return md

    def update_sample_metadata(self, md: SampleMetadata):
        self.dm_experiment_combo_box.setCurrentText(md.dm_experiment)
        self.formula_combo_box.setCurrentText(md.chemical_formula)
        self.sample_combo_box.setCurrentText(md.sample_name)
        self.standard_check_box.setChecked(md.is_standard)


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2023, UChicago Argonne, LLC
#
# Distributed under the terms of the 3-Clause BSD License
#
# The full license is in the file LICENSE, distributed with this software.
#
# DISCLAIMER
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# -----------------------------------------------------------------------------
