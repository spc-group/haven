import logging
from collections import OrderedDict
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Union, Mapping, Sequence
from functools import partial
import subprocess

from qtpy import QtWidgets, QtCore
from qtpy.QtWidgets import QAction
from qtpy.QtCore import Slot, QThread, Signal, QObject
from PyQt5.QtWidgets import QStyleFactory
import qtawesome as qta
import pydm
from pydm.application import PyDMApplication
from pydm.display import load_file
from pydm.utilities.stylesheet import apply_stylesheet
from bluesky_queueserver_api import BPlan
from bluesky_queueserver_api.zmq import REManagerAPI
import pyqtgraph as pg

from haven.exceptions import ComponentNotFound
from haven import HavenMotor, registry, load_config
import haven
from .main_window import FireflyMainWindow, PlanMainWindow
from .ophyd_plugin import OphydPlugin
from .queue_client import QueueClient, QueueClientThread, queueserver_api

generator = type((x for x in []))

__all__ = ["ui_dir", "FireflyApplication"]


log = logging.getLogger(__name__)


ui_dir = Path(__file__).parent


pg.setConfigOption("background", (252, 252, 252))
pg.setConfigOption("foreground", (0, 0, 0))


class FireflyApplication(PyDMApplication):
    default_display = None
    xafs_scan_window = None
    count_plan_window = None

    # Actions for showing window
    show_status_window_action: QtWidgets.QAction
    show_runs_window_action: QtWidgets.QAction
    show_energy_window_action: QtWidgets.QAction
    show_bss_window_action: QtWidgets.QAction
    launch_queuemonitor_action: QtWidgets.QAction

    # Keep track of motors
    motor_actions: Sequence = []
    motor_window_slots: Sequence = []

    # Keep track of cameras
    camera_actions: Mapping = {}
    camera_window_slots: Sequence

    # Keep track of area detectors
    area_detector_actions: Mapping = {}
    area_detector_window_slots: Sequence

    # Keep track of XRF detectors
    xrf_detector_actions: Mapping = {}
    xrf_detector_window_slots: Sequence

    # Signals for running plans on the queueserver
    queue_item_added = Signal(object)

    # Signals responding to queueserver changes
    queue_length_changed = Signal(int)
    queue_status_changed = Signal(dict)
    queue_environment_opened = Signal(bool)  # Opened or closed
    queue_environment_state_changed = Signal(str)  # New state
    queue_manager_state_changed = Signal(str)  # New state
    queue_re_state_changed = Signal(str)  # New state
    queue_devices_changed = Signal(dict)  # New list of devices

    # Actions for controlling the queueserver
    start_queue_action: QAction
    pause_runengine_action: QAction
    pause_runengine_now_action: QAction
    resume_runengine_action: QAction
    stop_runengine_action: QAction
    abort_runengine_action: QAction
    halt_runengine_action: QAction
    start_queue: QAction
    queue_autoplay_action: QAction
    queue_open_environment_action: QAction
    check_queue_status_action: QAction

    def __init__(self, display="status", use_main_window=False, *args, **kwargs):
        # Instantiate the parent class
        # (*ui_file* and *use_main_window* let us render the window here instead)
        self.default_display = display
        super().__init__(ui_file=None, use_main_window=use_main_window, *args, **kwargs)
        qss_file = Path(__file__).parent / "firefly.qss"
        self.setStyleSheet(qss_file.read_text())
        log.info(f"Available styles: {QStyleFactory.keys()}")
        # self.setStyle("Adwaita-dark")
        # qdarktheme.setup_theme(additional_qss=qss_file.read_text())
        self.windows = OrderedDict()
        self.queue_re_state_changed.connect(self.enable_queue_controls)

    def __del__(self):
        if hasattr(self, "_queue_thread"):
            self._queue_thread.quit()

    def _setup_window_action(self, action_name: str, text: str, slot: QtCore.Slot):
        action = QtWidgets.QAction(self)
        action.setObjectName(action_name)
        action.setText(text)
        action.triggered.connect(slot)
        setattr(self, action_name, action)

    def load_instrument(self):
        """Set up the application to use a previously loaded instrument.

        Expects devices, plans, etc to have been created already.

        """
        # Make actions for launching other windows
        self.setup_window_actions()
        # Actions for controlling the bluesky run engine
        self.setup_runengine_actions()
        # Prepare the client for interacting with the queue server
        self.prepare_queue_client()
        # Launch the default display
        show_default_window = getattr(self, f"show_{self.default_display}_window")
        default_window = show_default_window()
        # Set up the window to show list of PV connections
        pydm.utilities.shortcuts.install_connection_inspector(parent=default_window)

    def setup_window_actions(self):
        """Create QActions for clicking on menu items, shortcuts, etc.

        These actions should be usable by multiple
        windows. Window-specific actions belong with the window.

        """
        self.prepare_motor_windows()
        self.prepare_ion_chamber_windows()
        self.prepare_camera_windows()
        self.prepare_area_detector_windows()
        self.prepare_xrf_detector_windows()
        # Action for showing the beamline status window
        self._setup_window_action(
            action_name="show_status_window_action",
            text="Beamline Status",
            slot=self.show_status_window,
        )
        # Action for showing the run browser window
        self._setup_window_action(
            action_name="show_run_browser_action",
            text="Browse Runs",
            slot=self.show_run_browser,
        )
        # Action for launch queue-monitor
        self._setup_window_action(
            action_name="launch_queuemonitor_action",
            text="Queue Monitor",
            slot=self.launch_queuemonitor,
        )
        # Action for showing the beamline status window
        self._setup_window_action(
            action_name="show_bss_window_action",
            text="Scheduling (&BSS)",
            slot=self.show_bss_window,
        )
        # Launch energy window
        self._setup_window_action(
            action_name="show_energy_window_action",
            text="Energy",
            slot=self.show_energy_window,
        )
        # Launch camera overview
        self._setup_window_action(
            action_name="show_cameras_window_action",
            text="All Cameras",
            slot=self.show_cameras_window,
        )
        # Launch windows for plans
        self._setup_window_action(
            action_name="show_count_plan_window_action",
            text="&Count",
            slot=self.show_count_plan_window,
        )

    def launch_queuemonitor(self):
        config = load_config()["queueserver"]
        zmq_info_addr = f"tcp://{config['info_host']}:{config['info_port']}"
        zmq_ctrl_addr = f"tcp://{config['control_host']}:{config['control_port']}"
        cmds = [
            "queue-monitor",
            "--zmq-control-addr",
            zmq_ctrl_addr,
            "--zmq-info-addr",
            zmq_info_addr,
        ]
        subprocess.Popen(cmds)

    def setup_runengine_actions(self):
        """Create QActions for controlling the bluesky runengine."""
        # Internal actions for interacting with the run engine
        self.check_queue_status_action = QtWidgets.QAction(self)
        # Navbar actions for controlling the run engine
        actions = [
            ("pause_runengine_action", "Pause", "fa5s.stopwatch"),
            ("pause_runengine_now_action", "Pause Now", "fa5s.pause"),
            ("resume_runengine_action", "Resume", "fa5s.play"),
            ("stop_runengine_action", "Stop", "fa5s.stop"),
            ("abort_runengine_action", "Abort", "fa5s.eject"),
            ("halt_runengine_action", "Halt", "fa5s.ban"),
            ("start_queue_action", "Start", "fa5s.play"),
        ]
        self.queue_action_group = QtWidgets.QActionGroup(self)
        for name, text, icon_name in actions:
            action = QtWidgets.QAction(self.queue_action_group)
            icon = qta.icon(icon_name)
            action.setText(text)
            action.setCheckable(True)
            action.setIcon(icon)
            setattr(self, name, action)

    def _prepare_device_windows(self, device_label: str, attr_name: str):
        """Generic routine to be called for individual classes of devices.

        Sets up window actions, windows and window slots for each
        instance of the this device class (specified by *device_label*).

        """
        try:
            devices = sorted(registry.findall(label=device_label), key=lambda x: x.name)
        except ComponentNotFound:
            log.warning(f"No {device_label} found, menu will be empty.")
            devices = []
        # Create menu actions for each device
        actions = {}
        setattr(self, f"{attr_name}_actions", actions)
        window_slots = []
        setattr(self, f"{attr_name}_window_slots", window_slots)
        setattr(self, f"{attr_name}_windows", {})
        # if attr_name == "ion_chamber":
        #     breakpoint()
        for device in devices:
            action = QtWidgets.QAction(self)
            action.setObjectName(f"actionShow_{attr_name}_{device.name}")
            action.setText(device.name)
            actions[device.name] = action
            # Create a slot for opening the motor window
            slot = getattr(self, f"show_{attr_name}_window")
            slot = partial(slot, device=device)
            action.triggered.connect(slot)
            window_slots.append(slot)

    def prepare_area_detector_windows(self):
        """Prepare the support for opening area detector windows."""
        self._prepare_device_windows(
            device_label="area_detectors", attr_name="area_detector"
        )

    def prepare_xrf_detector_windows(self):
        """Prepare support to open X-ray fluorescence detector windows."""
        self._prepare_device_windows(
            device_label="xrf_detectors", attr_name="xrf_detector"
        )

    def prepare_camera_windows(self):
        self._prepare_device_windows(device_label="cameras", attr_name="camera")

    def prepare_ion_chamber_windows(self):
        self._prepare_device_windows(
            device_label="ion_chambers", attr_name="ion_chamber"
        )

    def prepare_motor_windows(self):
        """Prepare the support for opening motor windows."""
        ### TODO: Can we re-factor this to use _prepare_device_windows()?
        # Get active motors
        try:
            motors = sorted(registry.findall(label="motors"), key=lambda x: x.name)
        except ComponentNotFound:
            log.warning(
                "No motors found, [Positioners] -> [Motors] menu will be empty."
            )
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

    def prepare_queue_client(self, start_thread: bool = True, api=None):
        """Set up the QueueClient object that talks to the queue server.

        Parameters
        ==========
        api
          queueserver API. Used for testing.
        start_thread
          Whether to start the newly create queue client thread.
        
        """
        if api is None:
            api = queueserver_api()
        client = QueueClient(api=api)
        thread = QueueClientThread(client=client)
        client.moveToThread(thread)
        self._queue_client = client
        self._queue_thread = thread
        # Connect actions to slots for controlling the queueserver
        self.pause_runengine_action.triggered.connect(
            partial(client.request_pause, defer=True)
        )
        self.pause_runengine_now_action.triggered.connect(
            partial(client.request_pause, defer=False)
        )
        self.start_queue_action.triggered.connect(client.start_queue)
        self.check_queue_status_action.triggered.connect(
            partial(client.check_queue_status, True)
        )
        # Connect signals to slots for executing plans on queueserver
        self.queue_item_added.connect(client.add_queue_item)
        # Connect signals/slots for queueserver state changes
        client.status_changed.connect(self.queue_status_changed)
        client.length_changed.connect(self.queue_length_changed)
        client.environment_opened.connect(self.queue_environment_opened)
        self.queue_environment_opened.connect(self.set_open_environment_action_state)
        client.environment_state_changed.connect(self.queue_environment_state_changed)
        client.manager_state_changed.connect(self.queue_manager_state_changed)
        client.re_state_changed.connect(self.queue_re_state_changed)
        client.devices_changed.connect(self.queue_devices_changed)
        self.queue_autoplay_action = client.autoplay_action
        self.queue_autoplay_action.toggled.connect(
            self.check_queue_status_action.trigger
        )
        self.queue_open_environment_action = client.open_environment_action
        # Start the thread
        if start_thread:
            thread.start()

    def enable_queue_controls(self, re_state):
        """Enable/disable the navbar buttons that control the queue.

        Most buttons are only relevant when the run engine is in
        certain states. For exmple, you can't click Play if the run
        engine is already running.

        """
        all_actions = [
            self.start_queue_action,
            self.stop_runengine_action,
            self.pause_runengine_action,
            self.pause_runengine_now_action,
            self.resume_runengine_action,
            self.abort_runengine_action,
            self.halt_runengine_action,
        ]
        # Decide which signals to enable
        if re_state == "idle":
            enabled_signals = [self.start_queue_action]
        elif re_state == "paused":
            enabled_signals = [
                self.stop_runengine_action,
                self.resume_runengine_action,
                self.halt_runengine_action,
                self.abort_runengine_action
            ]
        elif re_state == "running":
            enabled_signals = [
                self.pause_runengine_action,
                self.pause_runengine_now_action,
            ]
        else:
            raise ValueError(f"Unknown run engine state: {re_state}")
        # Enable/disable the relevant signals
        for action in all_actions:
            action.setEnabled(action in enabled_signals)

    def add_queue_item(self, item):
        log.debug(f"Application received item to add to queue: {item}")
        self.queue_item_added.emit(item)

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
        window.actionShow_Sample_Viewer.triggered.connect(
            self.show_sample_viewer_window
        )

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
        if hasattr(self, "windows"):
            del self.windows[name]

    def create_window(self, WindowClass, ui_file, macros={}):
        # Create and save this window
        main_window = WindowClass(
            hide_menu_bar=self.hide_menu_bar, hide_status_bar=self.hide_status_bar
        )
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
        self.check_queue_status_action.trigger()
        return main_window

    def show_motor_window(self, *args, motor: HavenMotor):
        """Instantiate a new main window for this application."""
        motor_name = motor.name.replace(" ", "_")
        self.show_window(
            FireflyMainWindow,
            ui_dir / "motor.py",
            name=f"FireflyMainWindow_motor_{motor_name}",
            macros={"MOTOR": motor.name},
        )

    def show_camera_window(self, *args, device):
        """Instantiate a new main window for this application."""
        device_name = device.name.replace(" ", "_")
        self.show_window(
            FireflyMainWindow,
            ui_dir / "area_detector_viewer.py",
            name=f"FireflyMainWindow_camera_{device_name}",
            macros={"AD": device.name},
        )

    def show_ion_chamber_window(self, *args, device):
        """Instantiate a window for an ion chamber."""
        device_name = device.name.replace(" ", "_")
        self.show_window(
            FireflyMainWindow,
            ui_dir / "ion_chamber.ui",
            name=f"FireflyMainWindow_ion_chamber_{device_name}",
            macros={"IC": device.name},
        )

    def show_area_detector_window(self, *args, device):
        """Instantiate a new main window for this application."""
        device_name = device.name.replace(" ", "_")
        self.show_window(
            FireflyMainWindow,
            ui_dir / "area_detector_viewer.py",
            name=f"FireflyMainWindow_area_detector_{device_name}",
            macros={"AD": device.name},
        )

    def show_xrf_detector_window(self, *args, device):
        """Instantiate a new main window for this application."""
        device_name = device.name.replace(" ", "_")
        self.show_window(
            FireflyMainWindow,
            ui_dir / "xrf_detector.py",
            name=f"FireflyMainWindow_xrf_detector_{device_name}",
            macros={"DEV": device.name},
        )

    def show_status_window(self, stylesheet_path=None):
        """Instantiate a new main window for this application."""
        self.show_window(
            FireflyMainWindow, ui_dir / "status.py", name="beamline_status"
        )

    @QtCore.Slot()
    def show_run_browser(self):
        return self.show_window(
            PlanMainWindow, ui_dir / "run_browser.py", name="run_browser"
        )

    @QtCore.Slot()
    def show_log_viewer_window(self):
        self.show_window(FireflyMainWindow, ui_dir / "log_viewer.ui", name="log_viewer")

    @QtCore.Slot()
    def show_xafs_scan_window(self):
        return self.show_window(
            PlanMainWindow, ui_dir / "xafs_scan.py", name="xafs_scan"
        )

    @QtCore.Slot()
    def show_count_plan_window(self):
        return self.show_window(
            PlanMainWindow, ui_dir / "plans" / "count.py", name="count_plan"
        )

    @QtCore.Slot()
    def show_voltmeters_window(self):
        return self.show_window(
            FireflyMainWindow, ui_dir / "voltmeters.py", name="voltmeters"
        )

    @QtCore.Slot()
    def show_sample_viewer_window(self):
        return self.show_window(
            FireflyMainWindow, ui_dir / "sample_viewer.ui", name="sample_viewer"
        )

    @QtCore.Slot()
    def show_cameras_window(self):
        return self.show_window(
            FireflyMainWindow, ui_dir / "cameras.py", name="cameras"
        )

    @QtCore.Slot()
    def show_energy_window(self):
        return self.show_window(PlanMainWindow, ui_dir / "energy.py", name="energy")

    @QtCore.Slot()
    def show_bss_window(self):
        return self.show_window(FireflyMainWindow, ui_dir / "bss.py", name="bss")

    @QtCore.Slot(bool)
    def set_open_environment_action_state(self, is_open: bool):
        self.queue_open_environment_action.blockSignals(True)
        self.queue_open_environment_action.setChecked(is_open)
        self.queue_open_environment_action.blockSignals(False)
