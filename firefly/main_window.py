from pydm.main_window import PyDMMainWindow
# from qtpy.QtCore import Slot
from qtpy import QtCore, QtGui, QtWidgets

from .firefly_ui import Ui_MainWindow


class FireflyMainWindow(PyDMMainWindow):
    UiClass = Ui_MainWindow
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.customize_menu()
        self.export_actions()

    def customize_menu(self):
        # self.ui.menubar.addAction(self.ui.menuScans.menuAction())
        # Scans menu
        self.ui.menuScans = QtWidgets.QMenu(self.ui.menubar)
        self.ui.menuScans.setObjectName("menuScans")
        self.ui.menuScans.setTitle("Scans")
        self.ui.menubar.addAction(self.ui.menuScans.menuAction())
        # XAFS scan window
        self.ui.actionShow_Xafs_Scan = QtWidgets.QAction(self)
        self.ui.actionShow_Xafs_Scan.setObjectName("actionShow_Xafs_Scan")
        self.ui.actionShow_Xafs_Scan.setText("XAFS Scan")
        self.ui.menuScans.addAction(self.ui.actionShow_Xafs_Scan)
        # Detectors menu
        self.ui.menuDetectors = QtWidgets.QMenu(self.ui.menubar)
        self.ui.menuDetectors.setObjectName("menuDetectors")
        self.ui.menuDetectors.setTitle("Detectors")
        self.ui.menubar.addAction(self.ui.menuDetectors.menuAction())        
        # Voltmeters window
        self.ui.actionShow_Voltmeters = QtWidgets.QAction(self)
        self.ui.actionShow_Voltmeters.setObjectName("actionShow_Voltmeters")
        self.ui.actionShow_Voltmeters.setText("Ion Chambers")
        self.ui.menuDetectors.addAction(self.ui.actionShow_Voltmeters)
        self.ui.menubar.addAction(self.ui.menuScans.menuAction())
    
    def export_actions(self):
        """Expose specific signals that might be useful for responding to window changes."""
        self.actionShow_Xafs_Scan = self.ui.actionShow_Xafs_Scan
        self.actionShow_Voltmeters = self.ui.actionShow_Voltmeters
