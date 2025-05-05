from bluesky_queueserver_api import BPlan
from qtpy import QtWidgets

from firefly import display


class EnergyCalibrationDialog(QtWidgets.QDialog):
    """A dialog box for calibrating the energy."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowTitle("Monochromator calibration")

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


class AxilonMonochromatorDisplay(display.FireflyDisplay):

    def show_calibrate_dialog(self):
        dialog = EnergyCalibrationDialog(self)
        accepted = dialog.exec()
        if accepted:
            self.calibrate()

    def customize_device(self):
        super().customize_device()
        self.setWindowTitle(self.device.name.title())
    
    def customize_ui(self):
        # Respond to the "calibrate" button
        self.ui.calibrate_button.clicked.connect(self.show_calibrate_dialog)
        
    def ui_filename(self):
        return "devices/axilon_monochromator.ui"

    def queue_calibration(self, truth: float, target: float):
        plan = BPlan("calibrate", self.device.energy.name, truth, target=target)
        self.execute_item_submitted.emit(plan)
