import logging

from bluesky_queueserver_api import BPlan

from firefly import display

log = logging.getLogger()


class CountDisplay(display.FireflyDisplay):
    def customize_ui(self):
        self.ui.run_button.clicked.connect(self.queue_plan)

    def queue_plan(self, *args, **kwargs):
        """Execute this plan on the queueserver."""
        # Get scan parameters from widgets
        num_readings = self.ui.num_spinbox.value()
        delay = self.ui.delay_spinbox.value()
        detectors = self.ui.detectors_list.selected_detectors()
        # Build the queue item
        
        item = BPlan("count", delay=delay, num=num_readings, detectors=detectors)
        # Submit the item to the queueserver
        from firefly.application import FireflyApplication

        app = FireflyApplication.instance()
        log.info("Add ``count()`` plan to queue.")
        app.add_queue_item(item)

    def ui_filename(self):
        return "plans/count.ui"
