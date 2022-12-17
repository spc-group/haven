from typing import Optional

from qtpy.QtCore import QThread, QObject, Signal, Slot
from bluesky_queueserver_api.zmq import REManagerAPI

from haven import RunEngine


class QueueClient(QObject):
    api: REManagerAPI
    _last_queue_length: Optional[int] = None

    # Signals responding to queue changes
    state_changed = Signal()
    length_changed = Signal(int)

    def __init__(self, *args, api, **kwargs):
        self.api = api
        super().__init__(*args, **kwargs)

    def run(self):
        self.check_queue_length()
        super().run()

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

    @Slot(dict)
    def add_queue_item(self, item):
        result = self.api.item_add(item=item)
        if result['success']:
            self.length_changed.emit(result['qsize'])

    @Slot()
    def start_queue(self):
        self.api.queue_start()

    def check_queue_length(self):
        queue_length = len(self.api.get_queue())
        if queue_length != self._last_queue_length:
            self.length_changed.emit(queue_length)
            self._last_queue_length = queue_length
