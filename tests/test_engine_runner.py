import time
import pytest
from unittest.mock import MagicMock
import asyncio

from bluesky import RunEngine, plans as bp
from qtpy.QtCore import QThread
from qtpy.QtTest import QSignalSpy

from firefly.engine_runner import EngineRunner, FireflyRunEngine
from firefly.application import FireflyApplication


@pytest.fixture
def app():
    yield FireflyApplication()


@pytest.fixture
def run_engine():
    engine = FireflyRunEngine
    yield engine


def test_setup(run_engine, app):
    app.prepare_run_engine(run_engine)
    print("Test (post prepare_run_engine):", asyncio.get_event_loop())
    # Check that objects are created
    assert isinstance(app._engine_runner, EngineRunner)
    runner = app._engine_runner
    run_engine.runner = runner
    assert isinstance(app._engine_runner_thread, QThread)
    thread = app._engine_runner_thread
    # Start a plan
    spy = QSignalSpy(runner.state_changed)
    assert len(spy) == 0
    plan = bp.count([])
    print("Test (pre run_plan):", asyncio.get_event_loop())
    app.run_plan.emit(plan)
    # app.run_plan.emit((x for x in [0, 1, 2, 3]))
    time.sleep(1)
    assert len(spy) == 1
    # Try and pause the run engine
    # app.pause_run_engine.trigger()
    # Shutdown the thread
    thread.quit()
    # Wait for the thread to finish
    while thread.isRunning():
        time.sleep(0.01)
    assert False
