import logging
from pathlib import Path

from pydm.main_window import PyDMMainWindow

# from qtpy.QtCore import Slot
from qtpy import QtCore, QtGui, QtWidgets
from pydm import data_plugins
from haven.instrument import motor
from haven.instrument import motor
from haven import load_config

log = logging.getLogger(__name__)


class FireflyMainWindow(PyDMMainWindow):
    hide_nav_bar: bool = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.customize_ui()
        self.export_actions()

    def open(self, *args, **kwargs):
        widget = super().open(*args, **kwargs)
        # Connect signals for showing message in the window's status bar
        widget.status_message_changed.connect(self.show_status)
        return widget

    def closeEvent(self, event):
        super().closeEvent(event)
        # Delete the window so it's recreated next time it's opened
        self.deleteLater()

    def add_menu_action(self, action_name: str, text: str, menu: QtWidgets.QMenu):
        """Add a new QAction to a menubar menu.

        The action triggers when the menu item is activated.

        Parameters
        ==========
        action_name
          The name of the parameter to the save the action. Will be
          accessible via *action_name* on the window, and window.ui.
        text
          Human-readable text to show on the menu item.
        menu
          The QMenu object in which to put this menu item.

        Returns
        =======
        action
          A QAction for the menu item.

        """
        action = QtWidgets.QAction(self)
        action.setObjectName(action_name)
        action.setText(text)
        menu.addAction(action)
        # Save the action as object parameters
        setattr(self.ui, action_name, action)
        setattr(self, action_name, action)
        return action

    def customize_ui(self):
        # Add window icon
        root_dir = Path(__file__).parent.absolute()
        icon_path = root_dir / "splash.png"
        self.setWindowIcon(QtGui.QIcon(str(icon_path)))
        # Hide the nav bar
        if self.hide_nav_bar:
            self.toggle_nav_bar(False)
            self.ui.actionShow_Navigation_Bar.setChecked(False)
        # Setup menu
        self.ui.menuSetup = QtWidgets.QMenu(self.ui.menubar)
        self.ui.menuSetup.setObjectName("menuSetup")
        self.ui.menuSetup.setTitle("&Setup")
        self.ui.menubar.addAction(self.ui.menuSetup.menuAction())
        # XAFS scan window
        self.add_menu_action(
            action_name="actionShow_Log_Viewer", text="Logs", menu=self.ui.menuView
        )
        # Positioners menu
        self.ui.menuPositioners = QtWidgets.QMenu(self.ui.menubar)
        self.ui.menuPositioners.setObjectName("menuPositioners")
        self.ui.menuPositioners.setTitle("Positioners")
        self.ui.menubar.addAction(self.ui.menuPositioners.menuAction())
        # Sample viewer
        self.add_menu_action(
            action_name="actionShow_Sample_Viewer",
            text="Sample",
            menu=self.ui.menuPositioners,
        )
        # Motors sub-menu
        self.ui.menuMotors = QtWidgets.QMenu(self.ui.menubar)
        self.ui.menuMotors.setObjectName("menuMotors")
        self.ui.menuMotors.setTitle("Motors")
        self.ui.menuPositioners.addAction(self.ui.menuMotors.menuAction())
        # Scans menu
        self.ui.menuScans = QtWidgets.QMenu(self.ui.menubar)
        self.ui.menuScans.setObjectName("menuScans")
        self.ui.menuScans.setTitle("Scans")
        self.ui.menubar.addAction(self.ui.menuScans.menuAction())
        # XAFS scan window
        self.add_menu_action(
            action_name="actionShow_Xafs_Scan", text="XAFS Scan", menu=self.ui.menuScans
        )
        # Detectors menu
        self.ui.menuDetectors = QtWidgets.QMenu(self.ui.menubar)
        self.ui.menuDetectors.setObjectName("menuDetectors")
        self.ui.menuDetectors.setTitle("Detectors")
        self.ui.menubar.addAction(self.ui.menuDetectors.menuAction())
        # Voltmeters window
        self.add_menu_action(
            action_name="actionShow_Voltmeters",
            text="Ion Chambers",
            menu=self.ui.menuDetectors,
        )
        # Cameras sub-menu
        self.ui.menuCameras = QtWidgets.QMenu(self.ui.menubar)
        self.ui.menuCameras.setObjectName("menuCameras")
        self.ui.menuCameras.setTitle("Cameras")
        self.ui.menuDetectors.addAction(self.ui.menuCameras.menuAction())
        # Add actions to the motors sub-menus
        from .application import FireflyApplication

        app = FireflyApplication.instance()
        for action in app.motor_actions:
            self.ui.menuMotors.addAction(action)
        # Add actions to the cameras sub-menus
        self.ui.menuCameras.addAction(app.show_cameras_window_action)
        self.ui.menuCameras.addSeparator()
        for action in app.camera_actions:
            self.ui.menuCameras.addAction(action)
        # Add area detectors to detectors menu
        if len(app.area_detector_actions) > 0:
            self.ui.menuDetectors.addSeparator()
        for action in app.area_detector_actions:
            self.ui.menuDetectors.addAction(action)
        # Add other menu actions
        self.ui.menuView.addAction(app.show_status_window_action)
        self.ui.menuView.addAction(app.launch_queuemonitor_action)
        self.ui.menuSetup.addAction(app.show_bss_window_action)
        self.ui.menuPositioners.addAction(app.show_energy_window_action)
        self.ui.menuScans.addSeparator()
        self.ui.menuScans.addAction(app.show_run_browser_action)

    def show_status(self, message, timeout=0):
        """Show a message in the status bar."""
        bar = self.statusBar()
        bar.showMessage(message, timeout)

    def update_window_title(self):
        if self.showing_file_path_in_title_bar:
            title = self.current_file()
        else:
            title = self.display_widget().windowTitle()
        # Add the beamline name
        config = load_config()
        beamline_name = config["beamline"]["name"]
        title += f" - {beamline_name} - Firefly"
        if data_plugins.is_read_only():
            title += " [Read Only Mode]"
        self.setWindowTitle(title)

    def export_actions(self):
        """Expose specific signals that might be useful for responding to window changes."""
        self.actionShow_Log_Viewer = self.ui.actionShow_Log_Viewer
        self.actionShow_Xafs_Scan = self.ui.actionShow_Xafs_Scan
        self.actionShow_Voltmeters = self.ui.actionShow_Voltmeters


class PlanMainWindow(FireflyMainWindow):
    """A Qt window that has extra controls for a bluesky runengine."""

    hide_nav_bar: bool = True

    def setup_navbar(self):
        # Remove previous navbar actions
        navbar = self.ui.navbar
        for action in navbar.actions():
            navbar.removeAction(action)
        # Add applications runengine actions
        from .application import FireflyApplication

        app = FireflyApplication.instance()
        navbar.addAction(app.start_queue_action)
        navbar.addSeparator()
        navbar.addAction(app.pause_runengine_action)
        navbar.addAction(app.pause_runengine_now_action)
        navbar.addSeparator()
        navbar.addAction(app.resume_runengine_action)
        navbar.addAction(app.stop_runengine_action)
        navbar.addAction(app.abort_runengine_action)
        navbar.addAction(app.halt_runengine_action)

    def customize_ui(self):
        super().customize_ui()
        self.setup_navbar()
        # Connect signals/slots
        from .application import FireflyApplication

        app = FireflyApplication.instance()
        app.queue_length_changed.connect(self.set_navbar_visibility)

    @QtCore.Slot(int)
    def set_navbar_visibility(self, queue_length: int):
        """Determine whether to make the navbar be visible."""
        log.debug(f"Setting navbar visibility. Queue length: {queue_length}")
        navbar = self.ui.navbar
        navbar.setVisible(queue_length > 0)
