import time
from typing import Optional
import logging

from qtpy.QtCore import QThread, QObject, Signal, Slot, QTimer
from bluesky_queueserver_api.zmq import REManagerAPI
from bluesky_queueserver_api import BPlan

from haven import RunEngine


log = logging.getLogger()


class QueueClientThread(QThread):
    
    def __init__(self, *args, client, **kwargs):
        self.client = client
        super().__init__(*args, **kwargs)
        # Timer for polling the queueserver
        self.timer = QTimer()
        self.timer.timeout.connect(self.client.update)
        self.timer.start(1000)


class QueueClient(QObject):
    api: REManagerAPI
    _last_queue_length: Optional[int] = None

    # Signals responding to queue changes
    state_changed = Signal()
    length_changed = Signal(int)

    def __init__(self, *args, api, **kwargs):
        self.api = api
        super().__init__(*args, **kwargs)

    def update(self):
        log.debug("Updating queue client.")
        self.check_queue_length()

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
        if result['success']:
            log.info(f"Item added. New queue length: {result['qsize']}")
            self.length_changed.emit(result['qsize'])
        else:
            log.error(f"Did not add queue item to queue: {result}")
            raise RuntimeError(result)

    @Slot()
    def start_queue(self):
        self.api.queue_start()

    @Slot()
    def check_queue_length(self):
        queue = self.api.queue_get()
        queue_length = len(queue['items'])
        log.debug(f"Queue length updated: {queue_length}")
        self.length_changed.emit(queue_length)
        self._last_queue_length = queue_length
