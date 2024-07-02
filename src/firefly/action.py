import logging
from typing import Mapping

from qtpy.QtCore import Signal
from qtpy.QtGui import QIcon, QKeySequence
from qtpy.QtWidgets import QAction, QMainWindow

log = logging.getLogger(__name__)


class Action(QAction):
    """An action with a few useful setup shortcuts."""

    window: QMainWindow = None

    def __init__(
        self,
        name: str,
        text: str,
        shortcut: str = None,
        icon: QIcon = None,
        tooltip: str = "",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        # Set action properties
        self.setObjectName(name)
        self.setToolTip(tooltip)
        self.setText(text)
        if shortcut is not None:
            self.setShortcut(QKeySequence(shortcut))
        if icon is not None:
            self.setIcon(icon)

    @property
    def display(self):
        if self.window is not None:
            return self.window.display_widget()


class WindowAction(Action):
    """An action that opens a desired window when triggered."""

    window_created = Signal(QAction)
    window_shown = Signal(QAction)

    def __init__(
        self,
        name: str,
        text: str,
        display_file,
        shortcut: str = None,
        icon: QIcon = None,
        WindowClass: type = QMainWindow,
        macros=None,
        *args,
        **kwargs,
    ):
        super().__init__(
            name=name, text=text, shortcut=shortcut, icon=icon, *args, **kwargs
        )
        self.macros = macros
        self.display_file = display_file
        self.WindowClass = WindowClass
        # Connect signals
        self.triggered.connect(self.show_window)

    def show_window(self):
        if self.window is None:
            self.create_window()
        self.window.show()
        self.window.activateWindow()
        self.window_shown.emit(self)

    def forget_window(self):
        self.window = None

    def create_window(self):
        # Create the window
        window = self.WindowClass()
        self.window = window
        # Make it look pretty
        # window.update_tools_menu()
        kwargs = {}
        if self.macros is not None:
            kwargs["macros"] = self.macros
        window.open(str(self.display_file.resolve()), **kwargs)
        self.window_created.emit(self)
        # Properly remove the window if it's closed
        window.destroyed.connect(self.forget_window)


class ActionsRegistry:
    """A common namespace for keeping track of global actions."""

    # Actions for showing specific windows
    bss: WindowAction = None
    camera_overview: WindowAction = None
    energy: WindowAction = None
    iocs: WindowAction = None
    log: WindowAction = None
    status: WindowAction = None
    run_browser: WindowAction = None
    voltmeter: WindowAction = None
    xray_filter: WindowAction = None

    # Show windows for launching plans
    plans: Mapping[str, WindowAction]

    # Interactions with the queueserver
    queue_monitor: WindowAction = None
    queue_settings: Mapping[str, QAction]
    queue_controls: Mapping[str, QAction]

    # Show windows for controlling devices
    area_detectors: Mapping[str, WindowAction]
    cameras: Mapping[str, WindowAction]
    ion_chambers: Mapping[str, WindowAction]
    kb_mirrors: Mapping[str, WindowAction]
    mirrors: Mapping[str, WindowAction]
    motors: Mapping[str, WindowAction]
    robots: Mapping[str, WindowAction]
    slits: Mapping[str, WindowAction]
    tables: Mapping[str, WindowAction]
    xrf_detectors: Mapping[str, WindowAction]

    def __init__(self):
        self.plans = {}
        self.queue_settings = {}
        self.queue_controls = {}
        self.motors = {}
        self.cameras = {}
        self.area_detectors = {}
        self.slits = {}
        self.mirrors = {}
        self.ion_chambers = {}
        self.kb_mirrors = {}
        self.robots = {}
        self.tables = {}
        self.xrf_detectors = {}

    @property
    def all_actions(self):
        return [
            self.bss,
            self.camera_overview,
            self.energy,
            self.iocs,
            self.log,
            self.status,
            self.run_browser,
            self.voltmeter,
            self.xray_filter,
            *self.plans.values(),
            self.queue_monitor,
            *self.queue_settings.values(),
            *self.queue_controls.values(),
            *self.area_detectors.values(),
            *self.cameras.values(),
            *self.ion_chambers.values(),
            *self.kb_mirrors.values(),
            *self.mirrors.values(),
            *self.motors.values(),
            *self.robots.values(),
            *self.slits.values(),
            *self.tables.values(),
            *self.xrf_detectors.values(),
        ]
