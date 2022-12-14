import asyncio

from qtpy.QtCore import QThread, QObject, Signal, Slot
from bluesky_queueserver_api.zmq import REManagerAPI

from haven import RunEngine


generator = type((x for x in []))


class QueueClient(QObject):
    api: REManagerAPI
    state_changed = Signal()
    progress_updated = Signal(int)

    def __init__(self, *args, api, **kwargs):
        self.api = api
        super().__init__(*args, **kwargs)

    # def __init__(self, thread, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     # print("__init__1: ", asyncio.get_event_loop())
    #     self.moveToThread(thread)
    #     # print("__init__2: ", asyncio.get_event_loop())
    #     # Create the runengine object
    #     # loop = asyncio.new_event_loop()
    #     # asyncio.set_event_loop(loop)
    #     # self.RE = FireflyRunEngine()
    #     # print("__init__3: ", asyncio.get_event_loop())
    #     # Create a new event loop
    #     # Turn certain run engine methods into slots so they can be connected to

    # @Slot()
    # def request_pause(self, defer=False):
    #     self.RE.request_pause(defer=defer)

    # @Slot()
    # def setup_run_engine(self, run_engine):
    #     loop = asyncio.new_event_loop()
    #     asyncio.set_event_loop(loop)
    #     print("setup_run_engine (pre RunEngine()):", asyncio.get_event_loop())
    #     self.RE = run_engine
    #     print("setup_run_engine (post RunEngine()):", asyncio.get_event_loop())

    # @Slot(generator)
    # def run_plan(self, plan):
    #     print("run_plan (pre RE()):", asyncio.get_event_loop())
    #     self.RE(plan)
    #     print("run_plan (post RE()):", asyncio.get_event_loop())
        
