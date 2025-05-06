from ophyd_async.core import Device
from bluesky_queueserver_api import BPlan
from qtpy import QtWidgets
from pydm.widgets import PyDMLabel, PyDMLineEdit

from firefly import display


class AxilonMonochromatorDisplay(display.FireflyDisplay):
    def show_calibrate_dialog(self):
        dialog = EnergyCalibrationDialog(self, device=self.device)
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

    def queue_calibration(self):
        truth = self.ui.truth_spinbox.value()
        dial = self.ui.dial_spinbox.value()
        plan = BPlan("calibrate", self.device.energy.name, truth, dial=dial, relative=True)
        self.execute_item_submitted.emit(plan)
