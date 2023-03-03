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
from firefly.main_window import FireflyMainWindow


def test_setup(ffapp):
    ffapp.setup_window_actions()
    ffapp.setup_runengine_actions()
    api = MagicMock()
    FireflyMainWindow()
    ffapp.prepare_queue_client(api=api)


def test_queue_re_control(ffapp):
    """Test if the run engine can be controlled from the queue client."""
    api = MagicMock()
    ffapp.setup_window_actions()
    ffapp.setup_runengine_actions()
    ffapp.prepare_queue_client(api=api)
    window = FireflyMainWindow()
    window.show()
    # Try and pause the run engine
    ffapp.pause_runengine_action.trigger()
    # Check if the API paused
    time.sleep(0.1)
    api.re_pause.assert_called_once_with(option="deferred")
    # Pause the run engine now!
    api.reset_mock()
    ffapp.pause_runengine_now_action.trigger()
    # Check if the API paused now
    time.sleep(0.1)
    api.re_pause.assert_called_once_with(option="immediate")
    # Start the queue
    api.reset_mock()
    ffapp.start_queue_action.trigger()
    # Check if the queue started
    time.sleep(0.1)
    api.queue_start.assert_called_once()


def test_run_plan(ffapp, qtbot):
    """Test if a plan can be queued in the queueserver."""
    ffapp.setup_window_actions()
    ffapp.setup_runengine_actions()
    FireflyMainWindow()
    api = MagicMock()
    api.item_add.return_value = {"success": True, "qsize": 2}
    ffapp.prepare_queue_client(api=api)
    # Send a plan
    with qtbot.waitSignal(
        ffapp.queue_length_changed, timeout=1000, check_params_cb=lambda l: l == 2
    ):
        ffapp.queue_item_added.emit({})
    # Check if the API sent it
    api.item_add.assert_called_once_with(item={})


def test_check_queue_length(ffapp, qtbot):
    ffapp.setup_window_actions()
    ffapp.setup_runengine_actions()
    FireflyMainWindow()
    api = MagicMock()
    ffapp.prepare_queue_client(api=api)
    # Check that the queue length is changed
    api.get_queue.return_value = {
        "success": True,
        "msg": "",
        "items": [],
        "running_item": {},
        "plan_queue_uid": "f682e6fa-983c-4bd8-b643-b3baec2ec764",
    }
    with qtbot.waitSignal(
        ffapp.queue_length_changed, timeout=1000, check_params_cb=lambda l: l == 0
    ):
        ffapp._queue_client.check_queue_length()
    # Check that it isn't emitted a second time
    # with qtbot.waitSignal(ffapp.queue_length_changed):
    #     ffapp._queue_client.check_queue_length()
    # Now check a non-empty length queue
    api.queue_get.return_value = {
        "success": True,
        "msg": "",
        "items": ["hello", "world"],
        "running_item": {},
        "plan_queue_uid": "f682e6fa-983c-4bd8-b643-b3baec2ec764",
    }
    with qtbot.waitSignal(
        ffapp.queue_length_changed, timeout=1000, check_params_cb=lambda l: l == 2
    ):
        ffapp._queue_client.check_queue_length()
