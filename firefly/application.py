import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Union, Mapping
from functools import partial

from qtpy import QtWidgets, QtCore
from pydm.application import PyDMApplication
from pydm.display import load_file
from pydm.utilities.stylesheet import apply_stylesheet
from haven.exceptions import ComponentNotFound
from haven import HavenMotor, registry

from .main_window import FireflyMainWindow


__all__ = ["ui_dir", "FireflyApplication"]


log = logging.getLogger(__name__)


ui_dir = Path(__file__).parent


class FireflyApplication(PyDMApplication):
    xafs_scan_window = None
    
    def __init__(self, ui_file=None, use_main_window=False, *args, **kwargs):
        # Instantiate the parent class
        # (*ui_file* and *use_main_window* let us render the window here instead)
        super().__init__(ui_file=None, use_main_window=use_main_window, *args, **kwargs)
        self.windows = {}
        # Make actions for launching other windows
        self.setup_window_actions()
        # Launch the default display
        self.show_status_window()

    def _setup_window_action(self, action_name: str, text: str, slot: QtCore.Slot):
        action = QtWidgets.QAction(self)
        action.setObjectName(action_name)
        action.setText(text)
        action.triggered.connect(slot)
        setattr(self, action_name, action)

    def setup_window_actions(self):
        """Create QActions for clicking on menu items, shortcuts, etc.

        These actions should be usable by multiple
        windows. Window-specific actions belong with the window.

        """
        self.prepare_motor_windows()
        # Action for showing the beamline status window
        self.show_status_window_action = QtWidgets.QAction(self)
        self.show_status_window_action.setObjectName(f"show_status_window_action")
        self.show_status_window_action.setText("Beamline Status")
        self.show_status_window_action.triggered.connect(self.show_status_window)
        self._setup_window_action(action_name="show_energy_window_action", text="Energy", slot=self.show_energy_window)

    def prepare_motor_windows(self):
        """Prepare the support for opening motor windows."""
        # Get active motors
        try:
            motors = sorted(registry.findall(label="motors"), key=lambda x: x.name)
        except ComponentNotFound:
            log.warning("No motors found, [Positioners] -> [Motors] menu will be empty.")
            motors = []
        # Create menu actions for each motor
        self.motor_actions = []
        self.motor_window_slots = []
        self.motor_windows = {}
        for motor in motors:
            action = QtWidgets.QAction(self)
            action.setObjectName(f"actionShow_Motor_{motor.name}")
            action.setText(motor.name)
            self.motor_actions.append(action)
            # Create a slot for opening the motor window
            slot = partial(self.show_motor_window, motor=motor)
            action.triggered.connect(slot)
            self.motor_window_slots.append(slot)

    def connect_menu_signals(self, window):
        """Connects application-level signals to the associated slots.
        
        These signals should generally be applicable to multiple
        windows. If the signal and/or slot is specific to a given
        window, then it should be in that widnow's class definition
        and setup code.
        
        """
        window.actionShow_Log_Viewer.triggered.connect(self.show_log_viewer_window)
        window.actionShow_Xafs_Scan.triggered.connect(self.show_xafs_scan_window)
        window.actionShow_Voltmeters.triggered.connect(self.show_voltmeters_window)
        window.actionShow_Sample_Viewer.triggered.connect(self.show_sample_viewer_window)
        window.actionShow_Cameras.triggered.connect(self.show_cameras_window)

    def show_window(self, WindowClass, ui_file, name=None, macros={}):
        # Come up with the default key for saving in the windows dictionary
        if name is None:
            name = f"{WindowClass.__name__}_{ui_file.name}"
        # Check if the window has already been created
        if (w := self.windows.get(name)) is None:
            # Window is not yet created, so create one
            w = self.create_window(WindowClass, ui_dir / ui_file, macros=macros)
            self.windows[name] = w
            # Connect signals to remove the window when it closes
            w.destroyed.connect(partial(self.forget_window, name=name))
        else:
            # Window already exists so just bring it to the front
            w.show()
            w.activateWindow()
        return w

    def forget_window(self, obj, name):
        """Forget this window exists."""
        del self.windows[name]

    def create_window(self, WindowClass, ui_file, macros={}):
        # Create and save this window
        main_window = WindowClass(hide_menu_bar=self.hide_menu_bar,
                                  hide_status_bar=self.hide_status_bar)
        # Make it look pretty
        apply_stylesheet(self.stylesheet_path, widget=main_window)
        main_window.update_tools_menu()
        # Load the UI file for this window
        display = main_window.open(str(ui_file.resolve()), macros=macros)
        self.connect_menu_signals(window=main_window)
        # Show the display
        if self.fullscreen:
            main_window.enter_fullscreen()
        else:
            main_window.show()
        return main_window

    def show_motor_window(self, *args, motor: HavenMotor):
        """Instantiate a new main window for this application."""
        motor_name = motor.name.replace(" ", "_")
        self.show_window(FireflyMainWindow, ui_dir / "motor.py",
                         name=f"FireflyMainWindow_motor_{motor_name}",
                         macros={"PREFIX": motor.prefix})

    def show_status_window(self, stylesheet_path=None):
        """Instantiate a new main window for this application."""
        self.show_window(FireflyMainWindow, ui_dir / "status.py", name="beamline_status")

    make_main_window = show_status_window

    @QtCore.Slot()
    def show_log_viewer_window(self):
        self.show_window(FireflyMainWindow, ui_dir / "log_viewer.ui", name="log_viewer")

    @QtCore.Slot()
    def show_xafs_scan_window(self):
        self.show_window(FireflyMainWindow, ui_dir / "xafs_scan.py", name="xafs_scan")

    @QtCore.Slot()
    def show_voltmeters_window(self):
        self.show_window(FireflyMainWindow, ui_dir / "voltmeters.py", name="voltmeters")

    @QtCore.Slot()
    def show_sample_viewer_window(self):
        self.show_window(FireflyMainWindow, ui_dir / "sample_viewer.ui", name="sample_viewer")

    @QtCore.Slot()
    def show_cameras_window(self):
        self.show_window(FireflyMainWindow, ui_dir / "cameras.py", name="cameras")

    @QtCore.Slot()
    def show_energy_window(self):
        self.show_window(FireflyMainWindow, ui_dir / "energy.py", name="energy")
