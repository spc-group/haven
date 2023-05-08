import qtawesome as qta
from pydm import PyDMChannel
from qtpy.QtCore import Signal

from firefly import display

class XRFROIDisplay(display.FireflyDisplay):
    enabled_background = "rgb(212, 237, 218)"  # Pale green
    selected_background = "rgb(204, 229, 255)"  # Pale blue

    # Signals
    selected = Signal(bool)
    
    def ui_filename(self):
        return "xrf_roi.ui"

    def customize_ui(self):
        self.ui.set_roi_button.setIcon(qta.icon("fa5s.chart-line"))
        self.ui.enabled_checkbox.toggled.connect(self.set_backgrounds)
        self.ui.set_roi_button.toggled.connect(self.set_backgrounds)        
        self.ui.enabled_checkbox.toggled.connect(self.enable_roi)
        self.ui.set_roi_button.toggled.connect(self.selected)
    
    def set_backgrounds(self):
        is_selected = self.ui.set_roi_button.isChecked()
        if is_selected:
            self.setStyleSheet(f"background: {self.selected_background}")
        else:
            self.setStyleSheet("")

    def enable_roi(self, is_enabled):
        if not is_enabled:
            # Unselect this channel so we don't get locked out
            self.ui.set_roi_button.setChecked(False)
