from bluesky_queueserver_api import BPlan

from firefly import display
from firefly.component_selector import dotted_name


class AxilonMonochromatorDisplay(display.FireflyDisplay):
    def customize_device(self):
        super().customize_device()
        self.setWindowTitle(self.device.name.title())

    def customize_ui(self):
        self.ui.dial_spinbox.setMaximum(float("inf"))
        self.ui.dial_spinbox.setMinimum(-float("inf"))
        self.ui.truth_spinbox.setMaximum(float("inf"))
        self.ui.truth_spinbox.setMinimum(-float("inf"))
        # Respond to the "calibrate" button
        self.ui.calibrate_button.clicked.connect(self.queue_calibration)

    def update_queue_status(self, status):
        self.calibrate_button.update_queue_style(status)

    def ui_filename(self):
        return "devices/axilon_monochromator.ui"

    def queue_calibration(self):
        truth = self.ui.truth_spinbox.value()
        dial = self.ui.dial_spinbox.value()
        plan = BPlan(
            "calibrate",
            dotted_name(self.device.energy),
            truth,
            dial=dial,
            relative=True,
        )
        self.execute_item_submitted.emit(plan)
