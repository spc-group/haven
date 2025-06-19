from unittest import mock

import pytest
from ophyd_async.testing import set_mock_value

from firefly.devices.robot import RobotDisplay
from haven.devices import Motor


@pytest.fixture()
async def motor(sim_registry):
    m1 = Motor(prefix="", name="motor1")
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
    sim_registry.register(m1)
    return m1


@pytest.fixture
async def display(qtbot, motor, sim_registry, robot):
    display = RobotDisplay(macros={"DEVICE": robot.name})
    qtbot.addWidget(display)
    await display.update_devices(sim_registry)
    display.ui.run_button.setEnabled(True)
    display.ui.num_regions_spin_box.setValue(1)
    await display.regions.set_region_count(1)
    return display


def test_sample_numbers(display):
    # Check that the display has the right number of rows to start with
    assert display.ui.sample_combo_box.count() == 10


@pytest.mark.asyncio
async def test_plan_args(qtbot, motor, display, sim_registry):
    await display.update_devices(sim_registry)
    display.ui.run_button.setEnabled(True)
    display.ui.num_regions_spin_box.setValue(1)
    await display.regions.set_region_count(1)

    # set up a test motor
    widgets = display.regions.row_widgets(1)
    widgets.device_selector.combo_box.setCurrentText("motor1")
    widgets.position_spin_box.setValue(100)
    # Check arguments that will be given to the plan
    args, kwargs = display.plan_args()
    assert args == ("robotA", 8, "motor1", 100)
    assert kwargs == {}


async def test_full_motor_parameters(display, motor):
    set_mock_value(motor.user_readback, 420)
    await display.regions.update_device_parameters(motor, row=1)
    spin_box = display.regions.row_widgets(1).position_spin_box
    assert spin_box.minimum() == -32000
    assert spin_box.maximum() == 32000
    assert spin_box.decimals() == 5
    assert spin_box.suffix() == "\u202F°"
    assert spin_box.value() == 420


async def test_nonnumeric_motor_parameters(display, motor):
    spin_box = display.regions.row_widgets(1).position_spin_box
    description = {
        motor.name: {
            "dtype": "string",
            "shape": [],
            "dtype_numpy": "<f8",
            "source": "ca://25idc:simMotor:m2.RBV",
        }
    }
    motor.describe = mock.AsyncMock(return_value=description)
    await display.regions.update_device_parameters(motor, row=1)
    assert not spin_box.isEnabled()
