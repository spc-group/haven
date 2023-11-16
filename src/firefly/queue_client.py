import logging
import time
import warnings
from typing import Optional

from bluesky_queueserver_api import BPlan, comm_base
from bluesky_queueserver_api.zmq import REManagerAPI
from qtpy.QtCore import QObject, QThread, QTimer, Signal, Slot
from qtpy.QtWidgets import QAction

from haven import load_config

log = logging.getLogger()


def queueserver_api():
    config = load_config()["queueserver"]
    ctrl_addr = f"tcp://{config['control_host']}:{config['control_port']}"
    info_addr = f"tcp://{config['info_host']}:{config['info_port']}"
    api = REManagerAPI(zmq_control_addr=ctrl_addr, zmq_info_addr=info_addr)
    return api


class QueueClientThread(QThread):
    """A thread for handling the queue client.

    Every *poll_time* seconds, the timer will emit its *timeout*
    signal. You can connect a slot to the
    :py:cls:`QueueClientThread.timer.timeout()` signal.

    """

    timer: QTimer

    def __init__(self, *args, poll_time=1000, **kwargs):
        super().__init__(*args, **kwargs)
        self.timer = QTimer()

    def quit(self, *args, **kwargs):
        if hasattr(self, "timer"):
            self.timer.stop()
        super().quit(*args, **kwargs)

    def start(self, *args, **kwargs):
        super().start(*args, **kwargs)
        self.timer.start(1000)


class QueueClient(QObject):
    api: REManagerAPI
    _last_queue_status: Optional[dict] = None
    last_update: float = -1
    timeout: float = 1

    # Signals responding to queue changes
    status_changed = Signal(dict)
    length_changed = Signal(int)
    environment_opened = Signal(bool)  # Opened (True) or closed (False)
    environment_state_changed = Signal(str)  # New state
    manager_state_changed = Signal(str)  # New state
    re_state_changed = Signal(str)  # New state
    devices_changed = Signal(dict)

    # Actions for changing the queue settings in menubars
    autoplay_action: QAction
    open_environment_action: QAction

    def __init__(self, *args, api, autoplay_action, open_environment_action, **kwargs):
        self.api = api
        super().__init__(*args, **kwargs)
        # Set up actions coming from the parent
        self.autoplay_action = autoplay_action
        self.open_environment_action = open_environment_action
        self.setup_actions()
        self._last_queue_status = {}

    def setup_actions(self):
        # Connect actions to signal handlers
        if self.open_environment_action is not None:
            self.open_environment_action.triggered.connect(self.open_environment)

    def open_environment(self):
        to_open = self.open_environment_action.isChecked()
        if to_open:
            api_call = self.api.environment_open
        else:
            api_call = self.api.environment_close
        result = api_call()
        print(result, to_open)
        if result["success"]:
            self.environment_opened.emit(to_open)
        else:
            log.error(f"Failed to open/close environment: {result['msg']}")

    @Slot()
    def update(self):
        now = time.time()
        if now >= self.last_update + self.timeout:
            if not load_config()["beamline"]["is_connected"]:
                log.warning("Beamline not connected, skipping queue client update.")
                self.timeout = 60  # Just update every 1 minute
                self.last_update = now
                return
            log.debug("Updating queue client.")
            try:
                self._check_queue_status()
            except comm_base.RequestTimeoutError as e:
                # If we can't reach the server, wait for a minute and retry
                self.timeout = min(60, self.timeout * 2)
                log.warn(str(e))
                warnings.warn(str(e))
                log.info(f"Retrying in {self.timeout} seconds.")
            else:
                # Update succeeded, so wait for a second
                self.timeout = 1
            finally:
                self.last_update = now

    @Slot(bool)
    def request_pause(self, defer: bool = True):
        """Ask the queueserver run engine to pause.

        Parameters
        ==========
        defer
          If true, the run engine will be paused at the next
          checkpoint. Otherwise, it will pause now.

        """
        option = "deferred" if defer else "immediate"
        self.api.re_pause(option=option)

    @Slot(object)
    def add_queue_item(self, item):
        log.info(f"Client adding item to queue: {item}")
        result = self.api.item_add(item=item)
        if result["success"]:
            log.info(f"Item added. New queue length: {result['qsize']}")
            new_length = result["qsize"]
            self.length_changed.emit(result["qsize"])
            # Automatically run the queue if this is the first item
            print(self.autoplay_action.isChecked())
            if self.autoplay_action.isChecked():
                self.start_queue()
        else:
            log.error(f"Did not add queue item to queue: {result}")
            raise RuntimeError(result)

    @Slot()
    def start_queue(self):
        result = self.api.queue_start()
        # Report results
        if result["success"] is True:
            log.debug(f"Started queue server: {result}")
        else:
            log.error(f"Failed to start queue server: {result}")
            raise RuntimeError(result)

    @Slot()
    def check_queue_status(self, force=False, *args, **kwargs):
        """Get an update queue status from queue server and notify slots.

        Parameters
        ==========
        force
          If false (default), the ``queue_status_changed`` signal will
          be emitted only if the queue status has changed since last
          check.
        *args, *kwargs
          Unused arguments from qt widgets

        Emits
        =====
        self.status_changed
          With the updated queue status.

        """
        try:
            self._check_queue_status(force=force)
        except comm_base.RequestTimeoutError as e:
            log.warn(str(e))
            warnings.warn(str(e))

    def _check_queue_status(self, force: bool = False):
        """Get an update queue status from queue server and notify slots.

        Similar to ``check_queue_status`` but without the exception
        handling.

        Parameters
        ==========
        force
          If false (default), the ``queue_status_changed`` signal will
          be emitted only if the queue status has changed since last
          check.

        Emits
        =====
        self.status_changed
          With the updated queue status.

        """
        new_status = self.api.status()
        # Check individual components of the status if they've changed
        signals_to_check = [
            # (status key, signal to emit)
            ("worker_environment_exists", self.environment_opened),
            ("worker_environment_state", self.environment_state_changed),
            ("manager_state", self.manager_state_changed),
            ("re_state", self.re_state_changed),
        ]
        if force:
            log.debug(f"Forcing queue server status update: {new_status}")
        for key, signal in signals_to_check:
            is_new = key not in self._last_queue_status
            has_changed = new_status[key] != self._last_queue_status.get(key)
            if is_new or has_changed or force:
                signal.emit(new_status[key])
        # Check for new available devices
        if new_status["devices_allowed_uid"] != self._last_queue_status.get(
            "devices_allowed_uid"
        ):
            self.update_devices()
        # check the whole status to see if it's changed
        has_changed = new_status != self._last_queue_status
        if has_changed or force:
            self.status_changed.emit(new_status)
            self._last_queue_status = new_status

    def update_devices(self):
        "Emit the latest dict of available devices."
        response = self.api.devices_allowed()
        if response["success"]:
            devices = response["devices_allowed"]
            self.devices_changed.emit(devices)
        else:
            log.warning(
                "Could not poll devices_allowed:"
                f" {response.get('msg', 'reason unknown.')}"
            )
