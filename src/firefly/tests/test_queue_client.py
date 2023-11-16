from unittest.mock import MagicMock

import pytest
from bluesky_queueserver_api import BPlan
from pytestqt.exceptions import TimeoutError
from qtpy.QtWidgets import QAction

from firefly.queue_client import QueueClient

qs_status = {
    "msg": "RE Manager v0.0.18",
    "items_in_queue": 0,
    "items_in_history": 0,
    "running_item_uid": None,
    "manager_state": "idle",
    "queue_stop_pending": False,
    "worker_environment_exists": False,
    "worker_environment_state": "closed",
    "worker_background_tasks": 0,
    "re_state": None,
    "pause_pending": False,
    "run_list_uid": "4f2d48cc-980d-4472-b62b-6686caeb3833",
    "plan_queue_uid": "2b99ccd8-f69b-4a44-82d0-947d32c5d0a2",
    "plan_history_uid": "9af8e898-0f00-4e7a-8d97-0964c8d43f47",
    "devices_existing_uid": "51d8b88d-7457-42c4-b67f-097b168be96d",
    "plans_existing_uid": "65f11f60-0049-46f5-9eb3-9f1589c4a6dd",
    "devices_allowed_uid": "a5ddff29-917c-462e-ba66-399777d2442a",
    "plans_allowed_uid": "d1e907cd-cb92-4d68-baab-fe195754827e",
    "plan_queue_mode": {"loop": False},
    "task_results_uid": "159e1820-32be-4e01-ab03-e3478d12d288",
    "lock_info_uid": "c7fe6f73-91fc-457d-8db0-dfcecb2f2aba",
    "lock": {"environment": False, "queue": False},
}


devices_allowed = {
    "devices_allowed": {
        "cpt": {
            "classname": "Signal",
            "is_flyable": False,
            "is_movable": True,
            "is_readable": True,
            "module": "ophyd.signal",
        },
        "sim_detector": {
            "classname": "SynGauss",
            "components": {
                "Imax": {
                    "classname": "Signal",
                    "is_flyable": False,
                    "is_movable": True,
                    "is_readable": True,
                    "module": "ophyd.signal",
                },
                "center": {
                    "classname": "Signal",
                    "is_flyable": False,
                    "is_movable": True,
                    "is_readable": True,
                    "module": "ophyd.signal",
                },
                "noise": {
                    "classname": "EnumSignal",
                    "is_flyable": False,
                    "is_movable": True,
                    "is_readable": True,
                    "module": "ophyd.sim",
                },
                "noise_multiplier": {
                    "classname": "Signal",
                    "is_flyable": False,
                    "is_movable": True,
                    "is_readable": True,
                    "module": "ophyd.signal",
                },
                "sigma": {
                    "classname": "Signal",
                    "is_flyable": False,
                    "is_movable": True,
                    "is_readable": True,
                    "module": "ophyd.signal",
                },
                "val": {
                    "classname": "SynSignal",
                    "is_flyable": False,
                    "is_movable": True,
                    "is_readable": True,
                    "module": "ophyd.sim",
                },
            },
            "is_flyable": False,
            "is_movable": False,
            "is_readable": True,
            "module": "ophyd.sim",
        },
        "sim_detector_Imax": {
            "classname": "Signal",
            "is_flyable": False,
            "is_movable": True,
            "is_readable": True,
            "module": "ophyd.signal",
        },
        "sim_detector_center": {
            "classname": "Signal",
            "is_flyable": False,
            "is_movable": True,
            "is_readable": True,
            "module": "ophyd.signal",
        },
        "sim_detector_noise": {
            "classname": "EnumSignal",
            "is_flyable": False,
            "is_movable": True,
            "is_readable": True,
            "module": "ophyd.sim",
        },
        "sim_detector_noise_multiplier": {
            "classname": "Signal",
            "is_flyable": False,
            "is_movable": True,
            "is_readable": True,
            "module": "ophyd.signal",
        },
        "sim_detector_sigma": {
            "classname": "Signal",
            "is_flyable": False,
            "is_movable": True,
            "is_readable": True,
            "module": "ophyd.signal",
        },
        "sim_motor": {
            "classname": "SynAxis",
            "components": {
                "acceleration": {
                    "classname": "Signal",
                    "is_flyable": False,
                    "is_movable": True,
                    "is_readable": True,
                    "module": "ophyd.signal",
                },
                "readback": {
                    "classname": "_ReadbackSignal",
                    "is_flyable": False,
                    "is_movable": True,
                    "is_readable": True,
                    "module": "ophyd.sim",
                },
                "setpoint": {
                    "classname": "_SetpointSignal",
                    "is_flyable": False,
                    "is_movable": True,
                    "is_readable": True,
                    "module": "ophyd.sim",
                },
                "unused": {
                    "classname": "Signal",
                    "is_flyable": False,
                    "is_movable": True,
                    "is_readable": True,
                    "module": "ophyd.signal",
                },
                "velocity": {
                    "classname": "Signal",
                    "is_flyable": False,
                    "is_movable": True,
                    "is_readable": True,
                    "module": "ophyd.signal",
                },
            },
            "is_flyable": False,
            "is_movable": True,
            "is_readable": True,
            "module": "ophyd.sim",
        },
        "sim_motor_acceleration": {
            "classname": "Signal",
            "is_flyable": False,
            "is_movable": True,
            "is_readable": True,
            "module": "ophyd.signal",
        },
        "sim_motor_setpoint": {
            "classname": "_SetpointSignal",
            "is_flyable": False,
            "is_movable": True,
            "is_readable": True,
            "module": "ophyd.sim",
        },
        "sim_motor_unused": {
            "classname": "Signal",
            "is_flyable": False,
            "is_movable": True,
            "is_readable": True,
            "module": "ophyd.signal",
        },
        "sim_motor_velocity": {
            "classname": "Signal",
            "is_flyable": False,
            "is_movable": True,
            "is_readable": True,
            "module": "ophyd.signal",
        },
    },
    "devices_allowed_uid": "3664551b-368c-4a47-906a-b9f1ff6c8a91",
    "msg": "",
    "success": True,
}


@pytest.fixture()
def client():
    # Create a fake API with known responses
    api = MagicMock()
    api.queue_start.return_value = {"success": True}
    api.status.return_value = qs_status
    api.queue_start.return_value = {
        "success": True,
    }
    api.devices_allowed.return_value = {"success": True, "devices_allowed": {}}
    api.environment_open.return_value = {"success": True}
    api.environment_close.return_value = {"success": True}
    # Create the client using the fake API
    autoplay_action = QAction()
    autoplay_action.setCheckable(True)
    open_environment_action = QAction()
    open_environment_action.setCheckable(True)
    client = QueueClient(
        api=api,
        autoplay_action=autoplay_action,
        open_environment_action=open_environment_action,
    )
    yield client


def test_queue_re_control(client):
    """Test if the run engine can be controlled from the queue client."""
    api = client.api
    # Try and pause the run engine
    client.request_pause(defer=True)
    # Check if the API paused
    api.re_pause.assert_called_once_with(option="deferred")
    # Pause the run engine now!
    api.reset_mock()
    client.request_pause(defer=False)
    # Check if the API paused now
    api.re_pause.assert_called_once_with(option="immediate")
    # Start the queue
    api.reset_mock()
    client.start_queue()
    # Check if the queue started
    api.queue_start.assert_called_once()


def test_run_plan(client, qtbot):
    """Test if a plan can be queued in the queueserver."""
    api = client.api
    api.item_add.return_value = {"success": True, "qsize": 2}
    # Send a plan
    with qtbot.waitSignal(
        client.length_changed, timeout=1000, check_params_cb=lambda l: l == 2
    ):
        client.add_queue_item({})
    # Check if the API sent it
    api.item_add.assert_called_once_with(item={})


def test_autoplay(client, qtbot):
    """Test how queuing a plan starts the runengine."""
    api = client.api
    # Check that it doesn't start the queue if the autoplay action is off
    plan = BPlan("set_energy", energy=8333)
    client.add_queue_item(plan)
    assert not api.queue_start.called
    # Check the queue was started now that autoplay is on
    client.autoplay_action.toggle()
    client.add_queue_item(plan)
    api.queue_start.assert_called_once()


def test_check_queue_status(client, qtbot):
    # Check that the queue length is changed
    signals = [
        client.status_changed,
        client.environment_opened,
        client.environment_state_changed,
        client.re_state_changed,
        client.manager_state_changed,
    ]
    with qtbot.waitSignals(signals):
        client.check_queue_status()
    return
    # Check that it isn't emitted a second time
    with pytest.raises(TimeoutError):
        with qtbot.waitSignals(signals, timeout=10):
            client.check_queue_status()
    # Now check a non-empty length queue
    new_status = qs_status.copy()
    new_status.update(
        {
            "worker_environment_exists": True,
            "worker_environment_state": "initializing",
            "manager_state": "creating_environment",
            "re_state": "idle",
            # "success": True,
            # "msg": "",
            # "items": ["hello", "world"],
            # "running_item": {},
            # "plan_queue_uid": "f682e6fa-983c-4bd8-b643-b3baec2ec764",
        }
    )
    client.api.status.return_value = new_status
    with qtbot.waitSignals(signals):
        client.check_queue_status()


def test_open_environment(client, qtbot):
    """Check that the 'open environment' action sends the right command to
    the queue.

    """
    api = client.api
    # Open the environment
    client.open_environment_action.setChecked(False)
    print(client.open_environment_action.isCheckable())
    with qtbot.waitSignal(client.environment_opened) as blocker:
        client.open_environment_action.trigger()
    assert blocker.args == [True]
    assert api.environment_open.called
    # Close the environment
    with qtbot.waitSignal(client.environment_opened) as blocker:
        client.open_environment_action.trigger()
    assert blocker.args == [False]
    assert api.environment_close.called


def test_devices_available(client, qtbot):
    """Check that the queue client provides a list of devices that can be
    used in plans.

    """
    api = client.api
    api.devices_allowed.return_value = devices_allowed
    # Ask for updated list of devices
    with qtbot.waitSignal(client.devices_changed) as blocker:
        client.update_devices()
    # Check that the data have the right form
    devices = blocker.args[0]
    assert "sim_detector" in devices.keys()
