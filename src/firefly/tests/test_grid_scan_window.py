import asyncio
from unittest import mock

import pytest
from ophyd_async.testing import set_mock_value

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
    # Set up motor num
    await display.regions.set_region_count(2)
    # Set up num of repeat scans
    display.ui.spinBox_repeat_scan_num.setValue(6)
    # Set up scan num of points
    display.regions_layout.itemAtPosition(1, 4).widget().setValue(4)
    display.regions_layout.itemAtPosition(2, 4).widget().setValue(5)
    # set up detectors
    display.ui.detectors_list.acquire_times = mock.AsyncMock(return_value=[0.82])
    # Run the time calculator
    await display.update_total_time()
    # Check whether time is calculated correctly for a single scan
    assert display.ui.scan_duration_label.text() == "0\u202fh 0\u202fm 16\u202fs"
    # Check whether time is calculated correctly including the repeated scan
    assert display.ui.total_duration_label.text() == "0\u202fh 1\u202fm 38\u202fs"


async def test_regions_in_layout(display):
    assert display.num_regions_spin_box.value() == 2


@pytest.mark.asyncio
async def test_step_size_calculation(display, qtbot):
    # Set up the display with 2 regions
    await display.regions.set_region_count(2)

    # Step size should be 0.90909 for 11 points from 0 to 10.
    row = 1
    display.regions.layout.itemAtPosition(row, 2).widget().setValue(0)
    display.regions.layout.itemAtPosition(row, 3).widget().setValue(10)
    display.regions.layout.itemAtPosition(row, 4).widget().setValue(12)
    # region_0.start_spin_box.setValue(0)
    # region_0.stop_spin_box.setValue(10)
    # region_0.scan_pts_spin_box.setValue(12)
    step_label = display.regions.layout.itemAtPosition(row, 5).widget()
    assert step_label.text() == "0.91"
    # Step size should be 5 for 3 points from 5 to 15.
    region_1 = display.regions[1]
    region_1.start_spin_box.setValue(5)
    region_1.stop_spin_box.setValue(15)
    region_1.scan_pts_spin_box.setValue(3)
    assert region_1.step_label.text() == "5.0"

    # Step size should 10 for 3 points from 10 to 30.
    region_0.start_spin_box.setValue(10)
    region_0.stop_spin_box.setValue(30)
    region_0.scan_pts_spin_box.setValue(3)
    assert region_0.step_label.text() == "10.0"


@pytest.mark.asyncio
async def test_grid_scan_plan_args(display, xspress, ion_chamber, qtbot):
    await display.regions.set_region_count(2)
    widgets = display.regions.row_widgets(row=1)
    # set up a test motor 1
    widgets.device_selector.combo_box.setCurrentText("sync_motor_2")
    widgets.start_spin_box.setValue(1)
    widgets.stop_spin_box.setValue(111)
    widgets.num_points_spin_box.setValue(5)
    # select snake for the first motor
    widgets.snake_checkbox.setChecked(True)
    # set up a test motor 2
    widgets = display.regions.row_widgets(row=2)
    widgets.device_selector.combo_box.setCurrentText("async_motor_1")
    widgets.start_spin_box.setValue(2)
    widgets.stop_spin_box.setValue(222)
    widgets.num_points_spin_box.setValue(10)
    # set up detector list
    display.ui.detectors_list.selected_detectors = mock.MagicMock(
        return_value=[xspress, ion_chamber]
    )
    # set up meta data
    display.metadata_widget.sample_line_edit.setText("sam")
    display.metadata_widget.purpose_combo_box.setCurrentText("test")
    display.metadata_widget.notes_text_edit.setText("notes")
    # Check arguments that will get used by the plan
    args, kwargs = display.plan_args()
    assert args == (
        ["vortex_me4", "I00"],
        "sync_motor_2",
        1.0,
        111.0,
        5,
        "async_motor_1",
        2.0,
        222.0,
        10,
    )
    assert kwargs == dict(
        snake_axes=["sync_motor_2"],
        md={
            "sample_name": "sam",
            "purpose": "test",
            "notes": "notes",
            "is_standard": False,
        },
    )


async def test_full_motor_parameters(display, async_motors):
    await display.regions.set_region_count(2)
    motor = async_motors[0]
    display.ui.relative_scan_checkbox.setChecked(False)
    set_mock_value(motor.user_readback, 7.5)
    region = display.regions[0]
    await display.regions.update_device_parameters(motor, row=1)
    widgets = display.regions.row_widgets(row=1)
    start_box = widgets.start_spin_box
    assert start_box.minimum() == -10
    assert start_box.maximum() == 10
    assert start_box.decimals() == 5
    assert start_box.suffix() == "\u202f°"
    assert start_box.value() == 7.5
    stop_box = widgets.stop_spin_box
    assert stop_box.minimum() == -10
    assert stop_box.maximum() == 10
    assert stop_box.decimals() == 5
    assert stop_box.suffix() == "\u202f°"
    assert stop_box.value() == 7.5


async def test_relative_positioning(display, async_motors):
    await display.regions.set_region_count(2)
    motor = async_motors[0]
    region = display.regions[0]
    widgets = display.regions.row_widgets(1)
    set_mock_value(motor.user_readback, 7.5)
    widgets.device_selector.current_component = mock.MagicMock(return_value=motor)
    widgets.start_spin_box.setValue(5)
    widgets.stop_spin_box.setValue(10)
    # Relative positioning mode
    await display.regions.set_relative_position(True)
    assert widgets.start_spin_box.value() == -2.5
    assert widgets.start_spin_box.maximum() == 2.5
    assert widgets.start_spin_box.minimum() == -17.5
    assert widgets.stop_spin_box.value() == 2.5
    assert widgets.stop_spin_box.maximum() == 2.5
    assert widgets.stop_spin_box.minimum() == -17.5
    # Absolute positioning mode
    await display.regions.set_relative_position(False)
    assert widgets.start_spin_box.value() == 5.0
    assert widgets.start_spin_box.maximum() == 10
    assert widgets.start_spin_box.minimum() == -10
    assert widgets.stop_spin_box.value() == 10.0
    assert widgets.stop_spin_box.maximum() == 10
    assert widgets.stop_spin_box.minimum() == -10
