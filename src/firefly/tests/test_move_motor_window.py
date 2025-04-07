from unittest import mock

import pytest
from bluesky_queueserver_api import BPlan
from ophyd_async.testing import set_mock_value
from qtpy import QtCore

from firefly.plans.move_motor_window import MoveMotorDisplay
from haven.devices import Motor


@pytest.fixture()
async def motor():
    m1 = Motor(prefix="", name="m1")
    await m1.connect(mock=True)
    description = {
        m1.name: {
            "dtype": "number",
            "shape": [],
            "dtype_numpy": "<f8",
            "source": "ca://25idc:simMotor:m2.RBV",
            "units": "degrees",
            "precision": 5,
            "limits": {
                "control": {"low": -32000.0, "high": 32000.0},
                "display": {"low": -32000.0, "high": 32000.0},
            },
        }
    }
    m1.describe = mock.AsyncMock(return_value=description)
    return m1


@pytest.fixture()
async def display(qtbot, sim_registry, sync_motors, async_motors):
    display = MoveMotorDisplay()
    qtbot.addWidget(display)
    await display.update_devices(sim_registry)
    return display


@pytest.mark.asyncio
async def test_move_motor_plan_queued(display, qtbot):
    display.ui.run_button.setEnabled(True)
    # uncheck relative
    display.ui.relative_scan_checkbox.setChecked(False)
    await display.update_regions(2)
    # set up a test motor 1
    display.regions[0].motor_box.combo_box.setCurrentText("async_motor_1")
    display.regions[0].position_spin_box.setValue(111)
    # set up a test motor 2
    display.regions[1].motor_box.combo_box.setCurrentText("sync_motor_2")
    display.regions[1].position_spin_box.setValue(222)
    # Confirm that the correct plan arguments are built
    args, kwargs = display.plan_args()
    assert args == ("async_motor_1",111.0,"sync_motor_2",222.0,)
    assert kwargs == {}


async def test_full_motor_parameters(display, motor):
    set_mock_value(motor.user_readback, 420)
    region = display.regions[0]
    await region.update_device_parameters(motor)
    spin_box = region.position_spin_box
    assert spin_box.minimum() == -32000
    assert spin_box.maximum() == 32000
    assert spin_box.decimals() == 5
    assert spin_box.suffix() == " °"
    assert spin_box.value() == 420


async def test_nonnumeric_motor_parameters(display, motor):
    region = display.regions[0]
    spin_box = region.position_spin_box
    description = {
        motor.name: {
            "dtype": "string",
            "shape": [],
            "dtype_numpy": "<f8",
            "source": "ca://25idc:simMotor:m2.RBV",
        }
    }
    motor.describe = mock.AsyncMock(return_value=description)
    await region.update_device_parameters(motor)
    assert not spin_box.isEnabled()


async def test_relative_positioning(display, motor):
    region = display.regions[0]
    set_mock_value(motor.user_readback, 410)
    region.motor_box.current_component = mock.MagicMock(return_value=motor)
    region.position_spin_box.setValue(420)
    # Relative positioning mode
    await region.set_relative_position(True)
    assert region.position_spin_box.value() == 10
    assert region.position_spin_box.maximum() == 32000 - 410
    assert region.position_spin_box.minimum() == -32000 - 410
    # Absolute positioning mode
    await region.set_relative_position(False)
    assert region.position_spin_box.value() == 420
    assert region.position_spin_box.maximum() == 32000
    assert region.position_spin_box.minimum() == -32000
