import asyncio
from unittest import mock

import pytest
from bluesky_queueserver_api import BPlan
from ophyd_async.testing import set_mock_value
from qtpy import QtCore

from firefly.plans.grid_scan import GridScanDisplay


@pytest.fixture()
async def display(qtbot, sim_registry, sync_motors, async_motors, dxp, ion_chamber):
    display = GridScanDisplay()
    motor1 = async_motors[0]
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
    qtbot.addWidget(display)
    await display.update_devices(sim_registry)
    display.ui.run_button.setEnabled(True)
    try:
        yield display
    finally:
        await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_time_calculator(display, sim_registry, ion_chamber):
    # set up motor num
    await display.update_regions(2)

    # set up num of repeat scans
    display.ui.spinBox_repeat_scan_num.setValue(6)

    # set up scan num of points
    display.regions[0].scan_pts_spin_box.setValue(4)
    display.regions[1].scan_pts_spin_box.setValue(5)

    # set up detectors
    display.ui.detectors_list.acquire_times = mock.AsyncMock(return_value=[0.82])

    # Run the time calculator
    await display.update_total_time()

    # Check whether time is calculated correctly for a single scan
    assert display.ui.scan_duration_label.text() == "0 h 0 m 16 s"

    # Check whether time is calculated correctly including the repeated scan
    assert display.ui.total_duration_label.text() == "0 h 1 m 38 s"


async def test_regions_in_layout(display):
    assert display.regions_layout.rowCount() == 3  # header + 2 default rows


@pytest.mark.asyncio
async def test_step_size_calculation(display):
    # Set up the display with 2 regions
    await display.update_regions(2)

    # Step size should be 0.90909 for 11 points from 0 to 10.
    region_0 = display.regions[0]
    region_0.start_line_edit.setValue(0)
    region_0.stop_line_edit.setValue(10)
    region_0.scan_pts_spin_box.setValue(12)
    assert region_0.step_line_edit.text() == "0.90909"

    # Step size should be 5 for 3 points from 5 to 15.
    region_1 = display.regions[1]
    region_1.start_line_edit.setValue(5)
    region_1.stop_line_edit.setValue(15)
    region_1.scan_pts_spin_box.setValue(3)
    assert region_1.step_line_edit.text() == "5"

    # Step size should 10 for 3 points from 10 to 30.
    region_0.start_line_edit.setValue(10)
    region_0.stop_line_edit.setValue(30)
    region_0.scan_pts_spin_box.setValue(3)
    assert region_0.step_line_edit.text() == "10"


@pytest.mark.asyncio
async def test_grid_scan_plan_queued(display, ion_chamber, qtbot):
    await display.update_regions(2)

    # set up a test motor 1
    display.regions[0].motor_box.combo_box.setCurrentText("sync_motor_2")
    display.regions[0].start_line_edit.setValue(1)
    display.regions[0].stop_line_edit.setValue(111)
    display.regions[0].scan_pts_spin_box.setValue(5)

    # select snake for the first motor
    display.regions[0].snake_checkbox.setChecked(True)

    # set up a test motor 2
    display.regions[1].motor_box.combo_box.setCurrentText("async_motor_1")
    display.regions[1].start_line_edit.setValue(2)
    display.regions[1].stop_line_edit.setValue(222)
    display.regions[1].scan_pts_spin_box.setValue(10)

    # set up detector list
    display.ui.detectors_list.selected_detectors = mock.MagicMock(
        return_value=["vortex_me4", ion_chamber.name]
    )
    # set up meta data
    display.ui.lineEdit_sample.setText("sam")
    display.ui.comboBox_purpose.setCurrentText("test")
    display.ui.textEdit_notes.setText("notes")

    expected_item = BPlan(
        "rel_grid_scan",
        ["vortex_me4", "I00"],
        "async_motor_1",
        2.0,
        222.0,
        10,
        "sync_motor_2",
        1.0,
        111.0,
        5,
        snake_axes=["sync_motor_2"],
        md={"sample_name": "sam", "purpose": "test", "notes": "notes"},
    )

    def check_item(item):
        print(item.to_dict())
        print(expected_item.to_dict())
        return item.to_dict() == expected_item.to_dict()

    # Click the run button and see if the plan is queued
    with qtbot.waitSignal(
        display.queue_item_submitted, timeout=1000, check_params_cb=check_item
    ):
        qtbot.mouseClick(display.ui.run_button, QtCore.Qt.LeftButton)


async def test_full_motor_parameters(display, async_motors):
    motor = async_motors[0]
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


async def test_relative_positioning(display, async_motors):
    motor = async_motors[0]
    region = display.regions[0]
    set_mock_value(motor.user_readback, 7.5)
    region.motor_box.current_component = mock.MagicMock(return_value=motor)
    region.start_line_edit.setValue(5)
    region.stop_line_edit.setValue(10)
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
