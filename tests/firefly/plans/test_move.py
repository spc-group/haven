from unittest import mock

import pytest
from ophyd_async.testing import set_mock_value

from firefly.plans.move import MoveMotorDisplay
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
async def test_plan_args(display):
    display.ui.run_button.setEnabled(True)
    # uncheck relative
    display.ui.relative_scan_checkbox.setChecked(False)
    await display.regions.set_region_count(2)
    # set up a test motor 1
    widgets = display.regions.row_widgets(1)
    widgets.device_selector.combo_box.setCurrentText("async_motor_1")
    widgets.position_spin_box.setValue(111)
    # set up a test motor 2
    widgets = display.regions.row_widgets(2)
    widgets.device_selector.combo_box.setCurrentText("sync_motor_2")
    widgets.position_spin_box.setValue(222)
    # Confirm that the correct plan arguments are built
    args, kwargs = display.plan_args()
    assert args == (
        "async_motor_1",
        111.0,
        "sync_motor_2",
        222.0,
    )
    assert kwargs == {}


async def test_full_motor_parameters(display, motor):
    await display.regions.set_region_count(1)
    display.regions.is_relative = False
    set_mock_value(motor.user_readback, 420)
    await display.regions.update_device_parameters(motor, row=1)
    spin_box = display.regions.row_widgets(1).position_spin_box
    assert spin_box.minimum() == -32000
    assert spin_box.maximum() == 32000
    assert spin_box.decimals() == 5
    assert spin_box.suffix() == "\u202f°"
    assert spin_box.value() == 420


async def test_nonnumeric_motor_parameters(display, motor):
    await display.regions.set_region_count(1)
    display.regions.is_relative = False
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


async def test_relative_positioning(display, motor):
    await display.regions.set_region_count(1)
    display.regions.is_relative = False
    set_mock_value(motor.user_readback, 410)
    widgets = display.regions.row_widgets(1)
    widgets.device_selector.current_component = mock.MagicMock(return_value=motor)
    widgets.position_spin_box.setValue(420)
    # Relative positioning mode
    await display.regions.set_relative_position(True)
    assert widgets.position_spin_box.value() == 10
    assert widgets.position_spin_box.maximum() == 32000 - 410
    assert widgets.position_spin_box.minimum() == -32000 - 410
    # Absolute positioning mode
    await display.regions.set_relative_position(False)
    assert widgets.position_spin_box.value() == 420
    assert widgets.position_spin_box.maximum() == 32000
    assert widgets.position_spin_box.minimum() == -32000


async def test_update_devices(display, sim_registry):
    await display.regions.set_region_count(1)
    device_selector = display.regions.row_widgets(1).device_selector
    device_selector.update_devices = mock.AsyncMock()
    await display.update_devices(sim_registry)
    assert device_selector.update_devices.called


async def test_add_row_devices(display, sim_registry):
    """Do the devices get updated when adding rows."""
    await display.update_devices(sim_registry)
    await display.regions.set_region_count(2)
    selector_widget = display.regions.row_widgets(2).device_selector
    assert selector_widget.combo_box_model.rowCount() > 0


def test_queue_plan(display, qtbot):
    # Make sure the plan can be submitted
    # Specific plan args should test `display.plan_args()`
    with qtbot.waitSignal(display.queue_item_submitted, timeout=2):
        display.queue_plan()
