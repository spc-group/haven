from unittest import mock

import pytest
from bluesky_queueserver_api import BPlan
from ophyd_async.testing import set_mock_value
from qtpy import QtCore

from firefly.plans.line_scan import LineScanDisplay
from haven.devices.motor import Motor


@pytest.fixture()
async def motors(sim_registry, sync_motors):
    # Make a motor with a bad queueserver name
    motor1 = Motor(name="async motor-1", prefix="")
    assert " " in motor1.name
    assert "-" in motor1.name
    description = {
        motor1.name: {
            "dtype": "number",
            "shape": [],
            "dtype_numpy": "<f8",
            "source": "ca://25idc:simMotor:m2.RBV",
            "units": "degrees",
            "precision": 5,
            "limits": {
                "control": {"low": -10, "high": 10},
                "display": {"low": -10, "high": 10},
            },
        }
    }
    motor1.describe = mock.AsyncMock(return_value=description)
    motor2 = Motor(name="async_motor_2", prefix="")
    # Connect motors
    async_motors = [motor1, motor2]
    for motor in async_motors:
        await motor.connect(mock=True)
        sim_registry.register(motor)
    return async_motors + sync_motors


@pytest.fixture()
async def display(qtbot, sim_registry, sync_motors, motors, dxp, ion_chamber):
    display = LineScanDisplay()
    qtbot.addWidget(display)
    await display.update_devices(sim_registry)
    display.ui.run_button.setEnabled(True)
    return display


@pytest.mark.asyncio
async def test_time_calculator(display, sim_registry, ion_chamber, qtbot, qapp):
    # set up motor num
    await display.update_regions(2)

    # set up num of repeat scans
    display.ui.spinBox_repeat_scan_num.setValue(6)

    # set up scan num of points
    display.ui.scan_pts_spin_box.setValue(1000)

    # set up detectors
    display.ui.detectors_list.selected_detectors = mock.MagicMock(
        return_value=["vortex_me4", ion_chamber.name]
    )

    # set up default timing for the detector
    detectors = display.ui.detectors_list.selected_detectors()
    detectors = {name: sim_registry[name] for name in detectors}
    set_mock_value(ion_chamber.default_time_signal, 0.6255)
    detectors["vortex_me4"].default_time_signal.set(0.5).wait(2)

    # Trigger an update of the time calculator
    display.detectors_list.acquire_times = mock.AsyncMock(return_value=[1.0])
    await display.update_total_time()

    # Check whether time is calculated correctly for the scans
    assert display.ui.scan_duration_label.text() == "0 h 16 m 40 s"
    assert display.ui.total_duration_label.text() == "1 h 40 m 0 s"


async def test_regions_in_layout(display):
    assert display.regions_layout.rowCount() == 2  # header + default row


@pytest.mark.asyncio
async def test_step_size_calculation(display, qtbot):
    await display.update_regions(1)
    region = display.regions[0]

    # Test valid inputs
    region.start_line_edit.setValue(0)
    region.stop_line_edit.setValue(10)

    # Set num_points
    display.ui.scan_pts_spin_box.setValue(7)
    # Step size should be 1.6666 for 7 points from 0 to 10.
    assert region.step_line_edit.value() == 1.6667
    # Change the number of points and verify step size updates
    display.ui.scan_pts_spin_box.setValue(3)
    # Step size should be 5.0 for 3 points from 0 to 10."
    assert region.step_line_edit.value() == 5
    # Reset to another state and verify
    region.start_line_edit.setValue(0)
    region.stop_line_edit.setValue(10)
    display.ui.scan_pts_spin_box.setValue(6)
    assert region.step_line_edit.value() == 2


@pytest.mark.asyncio
async def test_line_scan_plan_queued(display, monkeypatch, qtbot):
    # set up motor num
    await display.update_regions(2)
    # set up a test motor 1
    display.regions[0].motor_box.combo_box.setCurrentText("async motor-1")
    display.regions[0].start_line_edit.setValue(1)
    display.regions[0].stop_line_edit.setValue(111)
    # set up a test motor 2
    display.regions[1].motor_box.combo_box.setCurrentText("sync_motor_2")
    display.regions[1].start_line_edit.setValue(2)
    display.regions[1].stop_line_edit.setValue(222)
    # set up scan num of points
    display.ui.scan_pts_spin_box.setValue(10)
    # time is calculated when the selection is changed
    display.ui.detectors_list.selected_detectors = mock.MagicMock(
        return_value=["vortex_me4", "I00"]
    )
    # set up meta data
    display.ui.lineEdit_sample.setText("sam")
    display.ui.comboBox_purpose.setCurrentText("test")
    display.ui.textEdit_notes.setText("notes")
    # Check the arguments that will get used by the plan
    args, kwargs = display.plan_args()
    assert args == (
        ["vortex_me4", "I00"],
        "async_motor_1",
        1.0,
        111.0,
        "sync_motor_2",
        2.0,
        222.0,
    )
    assert kwargs == {
        "num": 10,
        "md": {"sample_name": "sam", "purpose": "test", "notes": "notes"},
    }


async def test_full_motor_parameters(display, motors):
    motor = motors[0]
    display.ui.relative_scan_checkbox.setChecked(False)
    set_mock_value(motor.user_readback, 7.5)
    region = display.regions[0]
    await region.update_device_parameters(motor)
    start_box = region.start_line_edit
    assert start_box.minimum() == -10
    assert start_box.maximum() == 10
    assert start_box.decimals() == 5
    assert start_box.suffix() == " °"
    assert start_box.value() == 7.5
    stop_box = region.stop_line_edit
    assert stop_box.minimum() == -10
    assert stop_box.maximum() == 10
    assert stop_box.decimals() == 5
    assert stop_box.suffix() == " °"
    assert stop_box.value() == 7.5


async def test_relative_positioning(display, motors):
    motor = motors[0]
    region = display.regions[0]
    set_mock_value(motor.user_readback, 7.5)
    region.motor_box.current_component = mock.MagicMock(return_value=motor)
    region.start_line_edit.setValue(5.0)
    region.stop_line_edit.setValue(10.0)
    # Relative positioning mode
    await region.set_relative_position(True)
    assert region.start_line_edit.value() == -2.5
    assert region.start_line_edit.maximum() == 2.5
    assert region.start_line_edit.minimum() == -17.5
    assert region.stop_line_edit.value() == 2.5
    assert region.stop_line_edit.maximum() == 2.5
    assert region.stop_line_edit.minimum() == -17.5
    # Absolute positioning mode
    await region.set_relative_position(False)
    assert region.start_line_edit.value() == 5.0
    assert region.start_line_edit.maximum() == 10
    assert region.start_line_edit.minimum() == -10
    assert region.stop_line_edit.value() == 10.0
    assert region.stop_line_edit.maximum() == 10
    assert region.stop_line_edit.minimum() == -10
