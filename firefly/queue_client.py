import asyncio

from qtpy.QtCore import QThread, QObject, Signal, Slot
from bluesky_queueserver_api.zmq import REManagerAPI

from haven import RunEngine


class QueueClient(QObject):
    api: REManagerAPI
    state_changed = Signal()
    progress_updated = Signal(int)

    def __init__(self, *args, api, **kwargs):
        self.api = api
        super().__init__(*args, **kwargs)

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
