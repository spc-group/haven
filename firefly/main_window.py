from pydm.main_window import PyDMMainWindow
from qtpy.QtCore import Slot

from .firefly_ui import Ui_MainWindow


class FireflyMainWindow(PyDMMainWindow):
    UiClass = Ui_MainWindow
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.export_actions()
    
    def export_actions(self):
        """Expose specific signals that might be useful for responding to window changes."""
        self.actionShow_Xafs_Scan = self.ui.actionShow_Xafs_Scan
        self.actionShow_Voltmeters = self.ui.actionShow_Voltmeters
