from qtpy import QtWidgets


class EnergyCalibrationDialog(QtWidgets.QDialog):
    """A dialog box for calibrating the energy."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowTitle("Energy calibration")

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        # Widgets for inputting calibration parameters
        self.form_layout = QFormLayout()
        self.layout.addLayout(self.form_layout)
        self.form_layout.addRow(
            "Energy readback:", PyDMLabel(self, init_channel="haven://energy.readback")
        )
        self.form_layout.addRow(
            "Energy setpoint:",
            PyDMLineEdit(self, init_channel="haven://energy.setpoint"),
        )
        self.form_layout.addRow(
            "Calibrated energy:",
            QLineEdit(),
        )
        # Button for accept/close
        buttons = QDialogButtonBox.Apply | QDialogButtonBox.Close
        self.buttonBox = QDialogButtonBox(buttons)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonBox)


class MonochromatorDisplay(display.FireflyDisplay):
    def customize_ui(self):
        # Respond to the "calibrate" button
        self.ui.calibrate_button.clicked.connect(self.show_calibrate_dialog)
        
