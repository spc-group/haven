import asyncio
import time
from collections import ChainMap
from unittest.mock import AsyncMock

import pytest
from qtpy.QtCore import QTimer
from qtpy.QtWidgets import QAction

from firefly import queue_client

qs_status = {
    "msg": "RE Manager v0.0.18",
    "items_in_queue": 0,
    "items_in_history": 0,
    "running_item_uid": None,
    "manager_state": "idle",
    "queue_stop_pending": False,
    "queue_autostart_enabled": False,
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
    api = AsyncMock()
    api.queue_start.return_value = {"success": True}
    api.status.return_value = qs_status
    api.queue_start.return_value = {
        "success": True,
    }
    api.re_resume.return_value = {
        "success": True,
    }
    api.re_stop.return_value = {
        "success": True,
    }
    api.re_abort.return_value = {
        "success": True,
    }
    api.re_halt.return_value = {
        "success": True,
    }
    api.devices_allowed.return_value = {"success": True, "devices_allowed": {}}
    api.environment_open.return_value = {"success": True}
    api.environment_close.return_value = {"success": True}
    api.queue_autostart.return_value = {"success": True}
    api.queue_stop.return_value = {"success": True}
    api.queue_stop_cancel.return_value = {"success": True}
    # Create the client using the fake API
    autoplay_action = QAction()
    autoplay_action.setCheckable(True)
    open_environment_action = QAction()
    open_environment_action.setCheckable(True)
    client = queue_client.QueueClient(api=api)
    yield client


@pytest.fixture()
def status():
    status_ = queue_client.queue_status(queue_client.QueueClient.parameter_mapping)
    next(status_)
    return status_


def test_client_timer(client):
    assert isinstance(client.timer, QTimer)


@pytest.mark.asyncio
async def test_queue_re_control(client):
    """Test if the run engine can be controlled from the queue client."""
    api = client.api
    # Try and pause the run engine
    await client.request_pause(defer=True)
    # Check if the API paused
    api.re_pause.assert_called_once_with(option="deferred")
    # Pause the run engine now!
    api.reset_mock()
    await client.request_pause(defer=False)
    # Check if the API paused now
    api.re_pause.assert_called_once_with(option="immediate")
    # Start the queue
    api.reset_mock()
    await client.start_queue()
    # Check if the queue started
    api.queue_start.assert_called_once()
    # Resume a paused queue
    api.reset_mock()
    await client.resume_runengine()
    api.re_resume.assert_called_once()
    # Stop a paused queue
    api.reset_mock()
    await client.stop_runengine()
    api.re_stop.assert_called_once()
    # Abort a paused queue
    api.reset_mock()
    await client.abort_runengine()
    api.re_abort.assert_called_once()
    # Halt a paused queue
    api.reset_mock()
    await client.halt_runengine()
    api.re_halt.assert_called_once()


@pytest.mark.asyncio
async def test_queue_plan(client, qtbot):
    """Test if a plan can be queued in the queueserver."""
    api = client.api
    api.item_add.return_value = {"success": True, "qsize": 2}
    new_status = qs_status.copy()
    new_status["items_in_queue"] = 2
    # Send a plan
    await client.add_queue_item({})
    # Check if the API sent it
    api.item_add.assert_called_once_with(item={})


@pytest.mark.asyncio
async def test_execute_plan(client, qtbot):
    """Test if a plan can be executed in the queueserver."""
    api = client.api
    api.item_execute.return_value = {"success": True, "qsize": 1}
    new_status = qs_status.copy()
    new_status["items_in_queue"] = 1
    # Send a plan
    await client.execute_queue_item({})
    # Check if the API sent it
    api.item_execute.assert_called_once_with(item={})


@pytest.mark.asyncio
async def test_toggle_autostart(client, qtbot):
    """Test how queuing a plan starts the runengine."""
    api = client.api
    # Check that it doesn't start the queue if the autoplay action is off
    assert not api.queue_autostart.called
    # Check the queue was started now that autoplay is on
    await client.toggle_autostart(True)
    api.queue_autostart.assert_called_once_with(True)


# def test_start_queue(ffapp, client, qtbot):
#     ffapp.start_queue_action.trigger()
#     qtbot.wait(1000)
#     client.api.queue_start.assert_called_once()


@pytest.mark.asyncio
async def test_stop_queue(client, qtbot):
    """Test how queuing a plan starts the runengine."""
    api = client.api
    # Check that it doesn't start the queue if the autoplay action is off
    assert not api.queue_autostart.called
    # Check the queue stop was requested
    await client.stop_queue(True)
    api.queue_stop.assert_called_once()
    # Check the queue stop can be cancelled
    await asyncio.sleep(0.5)
    await api.clear_mock()
    await client.stop_queue(False)
    api.queue_stop_cancel.assert_called_once()


@pytest.mark.asyncio
async def test_send_status(status, qtbot):
    to_update = status.send(qs_status)
    assert to_update == {
        "status_changed": (qs_status,),
        "environment_opened": (False,),
        "environment_state_changed": ("closed",),
        "re_state_changed": (None,),
        "autostart_changed": (False,),
        "manager_state_changed": ("idle",),
        "in_use_changed": (False,),
        "devices_allowed_changed": ("a5ddff29-917c-462e-ba66-399777d2442a",),
    }
    # Check that it isn't updated a second time
    to_update = status.send(qs_status)
    assert to_update == {}
    # Now check a non-empty length queue
    new_status = ChainMap({}, qs_status)
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
    to_update = status.send(new_status)
    assert to_update == {
        "environment_opened": (True,),
        "environment_state_changed": ("initializing",),
        "re_state_changed": ("idle",),
        "manager_state_changed": ("creating_environment",),
        "status_changed": (new_status,),
    }


@pytest.mark.asyncio
async def test_open_environment(client, qtbot):
    """Check that the 'open environment' action sends the right command to
    the queue.

    """
    api = client.api
    # Open the environment
    with qtbot.waitSignal(client.environment_opened) as blocker:
        await client.open_environment(True)
    assert blocker.args == [True]
    assert api.environment_open.called
    # Close the environment
    with qtbot.waitSignal(client.environment_opened) as blocker:
        await client.open_environment(False)
    assert blocker.args == [False]
    assert api.environment_close.called


@pytest.mark.asyncio
async def test_devices_available(client, qtbot):
    """Check that the queue client provides a list of devices that can be
    used in plans.

    """
    api = client.api
    api.devices_allowed.return_value = devices_allowed
    # Ask for updated list of devices
    with qtbot.waitSignal(client.devices_changed) as blocker:
        await client.update_devices()
    # Check that the data have the right form
    devices = blocker.args[0]
    assert "sim_detector" in devices.keys()


@pytest.mark.asyncio
async def test_update(client, monkeypatch):
    api = client.api
    # Set the last update timestamp to be long enough ago
    client.last_update = time.monotonic()
    client.timeout = 1
    # Update the client
    await client.update()
    assert api.status.called


@pytest.mark.asyncio
async def test_save_queue(client, tmp_path, mocker):
    queue_get = {
        "success": True,
        "msg": "",
        "items": [
            {
                "item_type": "plan",
                "name": "rel_scan",
                "args": [
                    ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                    "aerotech.horizontal",
                    -20.0,
                    20.0,
                ],
                "kwargs": {
                    "num": 41,
                    "livetime": 0.5,
                    "collections_per_event": 1,
                    "md": {
                        "sample_name": "Beam_H_withI0pinhole",
                        "dm_exp": "2026_3_Startup",
                    },
                },
                "user": "GUI Client",
                "user_group": "primary",
                "item_uid": "bd71443a-996b-4fb9-bff4-34e58e2df081",
            }
        ],
        "running_item": None,
        "plan_queue_uid": "97c6fac3-603a-40ac-883b-fd1b98336f5a",
    }
    client.api.queue_get.return_value = queue_get
    target_file = tmp_path / "queue_export.txt"
    mock_file_dialog = mocker.MagicMock()
    mock_file_dialog.selectedFiles.return_value = [str(target_file)]
    mocker.patch(
        "firefly.queue_client.QFileDialog",
        mocker.MagicMock(return_value=mock_file_dialog),
    )
    await client.save_queue()
    assert target_file.exists()
    with open(target_file, mode="r") as fd:
        lines = fd.readlines()
        assert len(lines) == 2  # 1 for header, 1 for plan
        assert lines[0] == '{"haven_spec_version": 1}\n'


json_text = """
{"haven_spec_version": 1}
{"item_type": "plan", "name": "rel_scan", "args": [["It", "I0", "Iref", "IpreKB", "Ipreslit"], "aerotech.horizontal", -20.0, 20.0], "kwargs": {"num": 41, "livetime": 0.5, "collections_per_event": 1, "md": {"sample_name": "Beam_H_withI0pinhole", "dm_exp": "2026_3_Startup"}}, "user": "GUI Client", "user_group": "primary", "item_uid": "bd71443a-996b-4fb9-bff4-34e58e2df081"}
"""


@pytest.mark.asyncio
async def test_restore_queue(client, tmp_path, mocker):
    target_file = tmp_path / "queue_export.txt"
    with open(target_file, mode="w") as fd:
        fd.write(json_text)
    mock_file_dialog = mocker.MagicMock()
    mock_file_dialog.selectedFiles.return_value = [str(target_file)]
    mocker.patch(
        "firefly.queue_client.QFileDialog",
        mocker.MagicMock(return_value=mock_file_dialog),
    )
    await client.restore_queue()
    assert client.api.item_add_batch.called


{
    "success": True,
    "msg": "",
    "items": [
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.horizontal",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 0.5,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_H_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "bd71443a-996b-4fb9-bff4-34e58e2df081",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.horizontal",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 0.5,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_H_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "54a16f19-647c-407c-9c68-1f1d3eae4fea",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.horizontal",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 0.5,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_H_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "827396cc-2715-407b-b4e8-c9969187ac57",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.horizontal",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 0.5,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_H_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "e4eb6083-d6d7-4cb4-a473-f345ebc18477",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.horizontal",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 0.5,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_H_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "c5c60669-c3fd-4a50-a9db-d0deef78cdcd",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.horizontal",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 0.5,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_H_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "abef637a-a475-4901-8bfd-e0ee848111e4",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.horizontal",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 0.5,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_H_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "6cd49624-842f-446f-90c5-5ad169a226d1",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.horizontal",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 0.5,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_H_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "0e5a349d-f6f1-469f-b496-53bf8d15f9ab",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.horizontal",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 1,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_H_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "fe185ded-8204-4d3b-b42a-f464f485917c",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.horizontal",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 1,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_H_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "7a6c55ca-a5db-459c-bf2e-1c71886aadaf",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.horizontal",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 1,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_H_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "172c92bc-0463-4a48-ac6f-37e7df49ac76",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.horizontal",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 1,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_H_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "d8071f31-8f2d-41e4-ad39-bd704f80a2fc",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.horizontal",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 1,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_H_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "247bda5e-a2e5-4453-b1bd-023b2e51c32f",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.horizontal",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 1,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_H_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "22644ee5-95ed-4b43-8194-caae29096029",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.horizontal",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 1,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_H_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "a3b8e88c-1771-4385-ba08-1a04a4d2fee0",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.horizontal",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 1,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_H_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "6d8bbf16-6d2d-499e-a1e3-dcce09cb14ed",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.horizontal",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 1,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_H_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "876ae84a-81b2-4ee3-8afa-07dfbd7d7090",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.horizontal",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 1,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_H_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "2ec47e8a-c5cc-425b-bf76-2961e5f340a4",
        },
        {
            "item_type": "plan",
            "name": "mv",
            "args": [
                "sam_beam",
                3154.5,
                "aerotech.horizontal",
                -7670.458,
                "aerotech.vertical",
                7760.014,
            ],
            "user": "Queue Server API User",
            "user_group": "primary",
            "item_uid": "2220df14-0b3e-471b-a2ec-db5bcdd35a79",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
                "livetime": 0.2,
                "collections_per_event": 1,
            },
            "user": "Queue Server API User",
            "user_group": "primary",
            "item_uid": "06e30627-627c-47d5-b1d4-68b6822ba194",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
                "livetime": 0.2,
                "collections_per_event": 1,
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "c13a42bf-7c54-4fdc-bd9f-97a9f8f66ec5",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
                "livetime": 0.2,
                "collections_per_event": 1,
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "9fcf61b3-1e10-438d-b6ec-23486c4f7815",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
                "livetime": 0.2,
                "collections_per_event": 1,
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "c7fa10a9-05bc-4504-8cf3-408c97d9a94d",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
                "livetime": 0.2,
                "collections_per_event": 1,
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "f0d3827c-88e8-4b01-b752-e86ea5e657a1",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
                "livetime": 0.2,
                "collections_per_event": 1,
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "060fdb1f-9ac6-46a4-88d1-82f2a06248fb",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
                "livetime": 0.2,
                "collections_per_event": 1,
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "0408779a-b3e1-4507-a479-90b5b611718f",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
                "livetime": 0.2,
                "collections_per_event": 1,
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "2da3c5c1-c22a-48a6-92de-be01ff54ed83",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
                "livetime": 0.2,
                "collections_per_event": 1,
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "c7f8d761-801c-40c1-a2c3-a4430bd7a6c2",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
                "livetime": 0.2,
                "collections_per_event": 1,
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "1554d014-4ebe-46fa-95ac-4d47135e8b34",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 0.5,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "402ca7a3-1c0c-4e0e-9db2-59aa5ac2bcfb",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 0.5,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "fe855d55-d8a0-4a5e-9253-f5d6a7c49b3e",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 0.5,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "d808f998-175a-4014-92d6-6a95b275d318",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 0.5,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "7f023c92-9330-4ae8-9b29-436d40867a8f",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 0.5,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "10e46271-3a8f-4d81-b67a-0b297db22590",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 0.5,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "ee67cb19-8d50-4485-867c-b2d8c95f9c19",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 0.5,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "f06568b3-1fa1-4c12-8cc7-db15fcc1865f",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 0.5,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "af032d03-fab9-480d-b0c1-21ddd8e080b6",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 0.5,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "5c4b275c-e833-4ca2-80eb-973e674ed7ad",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 0.5,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "49bc8eb1-4f96-4cef-8429-a70407023365",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 1,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "8ff0c724-9ccc-4a9b-942f-fee305e9ebfa",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 1,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "83066457-45b2-48ad-998a-9887dd7e6866",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 1,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "0fdf66aa-31cd-4dfe-81fa-92d655220b8d",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 1,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "a8f46a8e-c249-41b9-9793-143c6aef7636",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 1,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "e4120a4c-9cc8-42f3-8be1-35a363f34c3c",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 1,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "37547475-81a7-4bf1-b54e-57ad59b2e25c",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 1,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "aa3d0880-bfd9-4f50-ba95-e6fd4bf0a64a",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 1,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "cfd65670-a31f-4489-9eb2-0f6619d66d9d",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 1,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "830667cf-9925-4598-8a3f-5bece17ba515",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.vertical",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 1,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_V_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "46169ca3-7250-4162-877f-b25a065b5407",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [["It", "I0", "Iref", "IpreKB", "Ipreslit"], "I0_H", -200.0, 200.0],
            "kwargs": {
                "num": 41,
                "md": {"sample_name": "I0_H_withpinhole", "dm_exp": "2026_3_Startup"},
                "livetime": 0.2,
                "collections_per_event": 1,
            },
            "user": "Queue Server API User",
            "user_group": "primary",
            "item_uid": "84a89ccd-98db-4a5b-b1b2-b8a3c2c9cecb",
        },
        {
            "item_type": "plan",
            "name": "record_dark_current",
            "kwargs": {
                "shutters": ["endstation_shutter"],
                "preamps": ["I0.preamp", "Iref.preamp", "IpreKB.preamp", "It.preamp"],
                "detectors": ["Ipreslit", "IpreKB", "I0", "It", "Iref"],
            },
            "user": "Queue Server API User",
            "user_group": "primary",
            "item_uid": "3ad9434c-8bef-4074-86db-27dc791d966f",
        },
        {
            "item_type": "plan",
            "name": "mv",
            "args": [
                "sam_beam",
                2954.5,
                "aerotech.horizontal",
                2329.501,
                "aerotech.vertical",
                -1476.934,
            ],
            "user": "Queue Server API User",
            "user_group": "primary",
            "item_uid": "ee622691-945c-413f-9fd0-0d47f5a5e030",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.horizontal",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "md": {
                    "sample_name": "Beam_H_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
                "livetime": 0.2,
                "collections_per_event": 1,
            },
            "user": "Queue Server API User",
            "user_group": "primary",
            "item_uid": "8f09755b-6e71-4f4c-88b4-709949f376c8",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.horizontal",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "md": {
                    "sample_name": "Beam_H_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
                "livetime": 0.2,
                "collections_per_event": 1,
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "412ae84f-1460-4747-8bcd-534768d75def",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.horizontal",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "md": {
                    "sample_name": "Beam_H_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
                "livetime": 0.2,
                "collections_per_event": 1,
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "b536dd1d-98bc-4cf1-adfb-4941cdf8b00d",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.horizontal",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "md": {
                    "sample_name": "Beam_H_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
                "livetime": 0.2,
                "collections_per_event": 1,
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "8d67371e-2165-479a-80cb-b61634edbb8e",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.horizontal",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "md": {
                    "sample_name": "Beam_H_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
                "livetime": 0.2,
                "collections_per_event": 1,
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "6e6e8bc7-131e-45fe-8f7f-0e8fbed83f49",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.horizontal",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "md": {
                    "sample_name": "Beam_H_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
                "livetime": 0.2,
                "collections_per_event": 1,
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "933e9e37-66b5-4b77-8fe8-1900bd3546f9",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.horizontal",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "md": {
                    "sample_name": "Beam_H_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
                "livetime": 0.2,
                "collections_per_event": 1,
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "b8882b44-1405-42a2-959f-c71f8d0f5f49",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.horizontal",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "md": {
                    "sample_name": "Beam_H_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
                "livetime": 0.2,
                "collections_per_event": 1,
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "96ef7721-7dc9-431d-8ef9-42bb87314f57",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.horizontal",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "md": {
                    "sample_name": "Beam_H_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
                "livetime": 0.2,
                "collections_per_event": 1,
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "576e09ad-ff14-48e7-b9d8-c42059b1125d",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.horizontal",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "md": {
                    "sample_name": "Beam_H_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
                "livetime": 0.2,
                "collections_per_event": 1,
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "fae83a58-ca5c-4b08-9ca1-a851a832e026",
        },
        {
            "item_type": "plan",
            "name": "rel_scan",
            "args": [
                ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
                "aerotech.horizontal",
                -20.0,
                20.0,
            ],
            "kwargs": {
                "num": 41,
                "livetime": 0.5,
                "collections_per_event": 1,
                "md": {
                    "sample_name": "Beam_H_withI0pinhole",
                    "dm_exp": "2026_3_Startup",
                },
            },
            "user": "GUI Client",
            "user_group": "primary",
            "item_uid": "8ccff135-05b7-4c6c-b6cd-bfd53301f8bc",
        },
    ],
    "running_item": {
        "item_type": "plan",
        "name": "rel_scan",
        "args": [
            ["It", "I0", "Iref", "IpreKB", "Ipreslit"],
            "aerotech.horizontal",
            -20.0,
            20.0,
        ],
        "kwargs": {
            "num": 41,
            "livetime": 0.5,
            "collections_per_event": 1,
            "md": {"sample_name": "Beam_H_withI0pinhole", "dm_exp": "2026_3_Startup"},
        },
        "user": "GUI Client",
        "user_group": "primary",
        "item_uid": "f60ec4bb-be8d-4012-a2e8-d05090f9f578",
        "properties": {"time_start": 1789265861.6850863},
    },
    "plan_queue_uid": "97c6fac3-603a-40ac-883b-fd1b98336f5a",
}

# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2023, UChicago Argonne, LLC
#
# Distributed under the terms of the 3-Clause BSD License
#
# The full license is in the file LICENSE, distributed with this software.
#
# DISCLAIMER
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# -----------------------------------------------------------------------------
