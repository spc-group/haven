import logging

from bluesky_queueserver_api import BPlan

from firefly import display

log = logging.getLogger()


class LineScanDisplay(display.FireflyDisplay):
    def customize_ui(self):
        # self.ui.run_button.setEnabled(True) for testing
        self.ui.run_button.clicked.connect(self.queue_plan)

    def queue_plan(self, *args, **kwargs):
        """Execute this plan on the queueserver."""
        # Get scan parameters from widgets
        detectors = self.ui.detectors_list.selected_detectors()
        motor = self.ui.motor_selector.current_component()
        start = float(self.ui.scan_start_lineEdit.text())
        stop = float(self.ui.scan_stop_lineEdit.text())
        num_points = self.ui.scan_pts_spin_box.value()

        # # Build the queue item
        item = BPlan("scan", detectors, motor, start, stop, num=num_points, per_step=None, md=None)

        # Submit the item to the queueserver
        from firefly.application import FireflyApplication

        app = FireflyApplication.instance()
        log.info("Add ``scan()`` plan to queue.")
        app.add_queue_item(item)

    def ui_filename(self):
        return "plans/line_scan.ui"
