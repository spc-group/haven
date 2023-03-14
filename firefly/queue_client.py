import time
from typing import Optional
import logging
import warnings

from qtpy.QtWidgets import QAction
from qtpy.QtCore import QThread, QObject, Signal, Slot, QTimer
from bluesky_queueserver_api.zmq import REManagerAPI
from bluesky_queueserver_api import BPlan, comm_base

from haven import RunEngine


log = logging.getLogger()


class QueueClientThread(QThread):
    timer: QTimer

    def __init__(self, *args, client, **kwargs):
        self.client = client
        super().__init__(*args, **kwargs)
        # Timer for polling the queueserver
        self.timer = QTimer()
        self.timer.timeout.connect(self.client.update)
        self.timer.start(1000)

    def quit(self, *args, **kwargs):
        self.timer.stop()
        # del self.timer
        # del self.client
        super().quit(*args, **kwargs)


class QueueClient(QObject):
    api: REManagerAPI
    _last_queue_length: Optional[int] = None
    last_update: float = -1
    timeout: float = 1

    # Signals responding to queue changes
    state_changed = Signal()
    length_changed = Signal(int)

    # Actions for changing the queue settings in menubars
    autoplay_action: QAction

    def __init__(self, *args, api, **kwargs):
        self.api = api
        super().__init__(*args, **kwargs)
        self.setup_actions()

    def setup_actions(self):
        self.autoplay_action = QAction()
        self.autoplay_action.setCheckable(True)
        self.autoplay_action.setObjectName("queue_autoplay_action")
        self.autoplay_action.setText("Autoplay queue")
        self.autoplay_action.setChecked(True)

    def update(self):
        now = time.time()
        if now >= self.last_update + self.timeout:
            log.debug("Updating queue client.")
            try:
                self.check_queue_length()
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
            # from pprint import pprint
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
    def check_queue_length(self):
        queue = self.api.queue_get()
        queue_length = len(queue["items"])
        log.debug(f"Queue length updated: {queue_length}")
        self.length_changed.emit(queue_length)
        self._last_queue_length = queue_length
