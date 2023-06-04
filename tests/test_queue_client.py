import time
import pytest
from unittest.mock import MagicMock
import asyncio
from collections import ChainMap

from bluesky import RunEngine, plans as bp
from qtpy.QtCore import QThread
from qtpy.QtTest import QSignalSpy
from bluesky_queueserver_api import BPlan
from bluesky_queueserver_api.zmq import REManagerAPI
from pytestqt.exceptions import TimeoutError

from firefly.queue_client import QueueClient
from firefly.application import REManagerAPI
from firefly.main_window import FireflyMainWindow


qs_status = {
    'msg': 'RE Manager v0.0.18',
    'items_in_queue': 0,
    'items_in_history': 0,
    'running_item_uid': None,
    'manager_state': 'idle',
    'queue_stop_pending': False,
    'worker_environment_exists': False,
    'worker_environment_state': 'closed',
    'worker_background_tasks': 0,
    're_state': None,
    'pause_pending': False,
    'run_list_uid': '4f2d48cc-980d-4472-b62b-6686caeb3833',
    'plan_queue_uid': '2b99ccd8-f69b-4a44-82d0-947d32c5d0a2',
    'plan_history_uid': '9af8e898-0f00-4e7a-8d97-0964c8d43f47',
    'devices_existing_uid': '51d8b88d-7457-42c4-b67f-097b168be96d',
    'plans_existing_uid': '65f11f60-0049-46f5-9eb3-9f1589c4a6dd',
    'devices_allowed_uid': 'a5ddff29-917c-462e-ba66-399777d2442a',
    'plans_allowed_uid': 'd1e907cd-cb92-4d68-baab-fe195754827e',
    'plan_queue_mode': {'loop': False},
    'task_results_uid': '159e1820-32be-4e01-ab03-e3478d12d288',
    'lock_info_uid': 'c7fe6f73-91fc-457d-8db0-dfcecb2f2aba',
    'lock': {'environment': False, 'queue': False}
}


def test_setup(ffapp):
    ffapp.setup_window_actions()
    ffapp.setup_runengine_actions()
    api = MagicMock()
    ffapp.prepare_queue_client(api=api)
    FireflyMainWindow()


def test_queue_re_control(ffapp):
    """Test if the run engine can be controlled from the queue client."""
    api = MagicMock()
    api.queue_start.return_value = {"success": True}
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
    api = MagicMock()
    api.item_add.return_value = {"success": True, "qsize": 2}
    api.queue_start.return_value = {"success": True}
    ffapp.prepare_queue_client(api=api)
    FireflyMainWindow()
    # Send a plan
    with qtbot.waitSignal(
        ffapp.queue_length_changed, timeout=1000, check_params_cb=lambda l: l == 2
    ):
        ffapp.queue_item_added.emit({})
    # Check if the API sent it
    api.item_add.assert_called_once_with(item={})


def test_autoplay(ffapp, qtbot):
    """Test how queuing a plan starts the runengine."""
    ffapp.setup_window_actions()
    ffapp.setup_runengine_actions()
    FireflyMainWindow()
    api = MagicMock()
    api.item_add.return_value = {"success": True, "qsize": 1}
    api.queue_start.return_value = {"success": True}
    ffapp.prepare_queue_client(api=api)
    # Send a plan
    plan = BPlan("set_energy", energy=8333)
    ffapp._queue_client.add_queue_item(plan)
    api.item_add.assert_called_once()
    # Check the queue was started
    api.queue_start.assert_called_once()
    # Check that it doesn't start the queue if the autoplay action is off
    api.reset_mock()
    ffapp._queue_client.autoplay_action.trigger()
    ffapp._queue_client.add_queue_item(plan)
    # Check that the queue wasn't started
    assert not api.queue_start.called


def test_check_queue_status(queue_app, qtbot):
    # Check that the queue length is changed
    signals = [
        queue_app.queue_status_changed,
        queue_app.queue_environment_opened,
        queue_app.queue_environment_state_changed,
        queue_app.queue_re_state_changed,
        queue_app.queue_manager_state_changed,
    ]
    with qtbot.waitSignals(signals):
        queue_app._queue_client.check_queue_status()
    # Check that it isn't emitted a second time
    with pytest.raises(TimeoutError):
        with qtbot.waitSignals(signals, timeout=10):
            queue_app._queue_client.check_queue_status()
    # Now check a non-empty length queue
    new_status = qs_status.copy()
    new_status.update({
        "worker_environment_exists": True,
        "worker_environment_state": "initializing",
        "manager_state": "creating_environment",
        "re_state": "idle",
        # "success": True,
        # "msg": "",
        # "items": ["hello", "world"],
        # "running_item": {},
        # "plan_queue_uid": "f682e6fa-983c-4bd8-b643-b3baec2ec764",
    })
    queue_app._queue_client.api.status.return_value = new_status
    with qtbot.waitSignals(signals):
        queue_app._queue_client.check_queue_status()
   

def test_open_environment(queue_app, qtbot):
    """Check that the 'open environment' action sends the right command to
    the queue.

    """
    api = queue_app._queue_client.api
    # Open the environment
    queue_app.queue_open_environment_action.setChecked(False)
    with qtbot.waitSignal(queue_app.queue_environment_opened) as blocker:
        queue_app.queue_open_environment_action.trigger()
    assert blocker.args == [True]
    assert api.environment_open.called
    # Close the environment
    with qtbot.waitSignal(queue_app.queue_environment_opened) as blocker:
        queue_app.queue_open_environment_action.trigger()
    assert blocker.args == [False]
    assert api.environment_close.called
