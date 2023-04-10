import logging

import haven

from firefly import display, FireflyApplication

log = logging.getLogger(__name__)


class StatusDisplay(display.FireflyDisplay):
    def customize_ui(self):
        app = FireflyApplication.instance()
        self.ui.bss_modify_button.clicked.connect(app.show_bss_window_action.trigger)

    def ui_filename(self):
        return "status.ui"
