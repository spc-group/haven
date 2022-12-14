import time
import pytest
from unittest.mock import MagicMock
import asyncio

from bluesky import RunEngine, plans as bp
from qtpy.QtCore import QThread
from qtpy.QtTest import QSignalSpy
from bluesky_queueserver_api.zmq import REManagerAPI

from firefly.queue_client import QueueClient
from firefly.application import REManagerAPI


def test_setup(qapp, mocker):
    mocker.patch('firefly.application.REManagerAPI')
    qapp.prepare_queue_client()
    # Try and pause the run engine
    qapp.pause_run_engine.trigger()
    # Check if the API paused
    REManagerAPI.assert_called_once_with("immediately")
    # print("Test (post prepare_run_engine):", asyncio.get_event_loop())
    # # Check that objects are created
    # assert isinstance(app._engine_runner, EngineRunner)
    # runner = app._engine_runner
    # run_engine.runner = runner
    # assert isinstance(app._engine_runner_thread, QThread)
    # thread = app._engine_runner_thread
    # # Start a plan
    # spy = QSignalSpy(runner.state_changed)
    # assert len(spy) == 0
    # plan = bp.count([])
    # print("Test (pre run_plan):", asyncio.get_event_loop())
    # app.run_plan.emit(plan)
    # # app.run_plan.emit((x for x in [0, 1, 2, 3]))
    # time.sleep(1)
    # assert len(spy) == 1
    # # Try and pause the run engine
    # # app.pause_run_engine.trigger()
    # # Shutdown the thread
    # thread.quit()
    # # Wait for the thread to finish
    # while thread.isRunning():
    #     time.sleep(0.01)
    # assert False
