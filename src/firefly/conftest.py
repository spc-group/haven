import subprocess

import psutil
import pydm
import pytest
from ophyd.sim import make_fake_device
from ophyd_async.core import wait_for_connection

from haven.devices.motor import HavenMotor, Motor


def tiled_is_running(port, match_command=True):
    lsof = subprocess.run(["lsof", "-i", f":{port}", "-F"], capture_output=True)
    assert lsof.stderr.decode() == ""
    stdout = lsof.stdout.decode().split("\n")
    is_running = len(stdout) >= 3
    if match_command:
        is_running = is_running and stdout[3] == "ctiled"
    return is_running


def kill_process(process_name):
    processes = []
    for proc in psutil.process_iter():
        # check whether the process name matches
        if proc.name() == process_name:
            proc.kill()
            processes.append(proc)
    # Wait for them all the terminate
    [proc.wait(timeout=5) for proc in processes]


@pytest.fixture(scope="session")
def pydm_ophyd_plugin():
    return pydm.data_plugins.plugin_for_address("haven://")


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


@pytest.fixture
def sync_motors(sim_registry):
    motor_names = ["sync_motor_1", "sync_motor_2"]
    motors = []
    for name in motor_names:
        this_motor = make_fake_device(HavenMotor)(name=name, labels={"motors"})
        motors.append(this_motor)
        sim_registry.register(this_motor)
    return motors


@pytest.fixture
async def async_motors(sim_registry):
    motors = [
        Motor(prefix="255idc:m1", name="async_motor_1"),
        Motor(prefix="255idc:m2", name="async_motor_2"),
    ]
    await wait_for_connection(**{m.name: m.connect(mock=True) for m in motors})
    for motor in motors:
        sim_registry.register(motor)
    return motors
