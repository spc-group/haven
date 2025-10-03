from unittest import mock

import pytest
from ophyd_async.testing import set_mock_value

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
    await display.regions.set_region_count(2)

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
    assert display.num_regions_spin_box.value() == 1


@pytest.mark.asyncio
async def test_step_size_calculation(display, qtbot):
    await display.regions.set_region_count(1)
    region = display.regions[0]
    widgets = display.regions.row_widgets(1)

    # Test valid inputs
    widgets.start_spin_box.setValue(0)
    widgets.stop_spin_box.setValue(10)

    # Set num_points
    display.ui.scan_pts_spin_box.setValue(7)
    # Step size should be 1.6666 for 7 points from 0 to 10.
    assert widgets.step_label.text() == "1.67"
    # Change the number of points and verify step size updates
    display.ui.scan_pts_spin_box.setValue(3)
    # Step size should be 5.0 for 3 points from 0 to 10."
    assert widgets.step_label.text() == "5.0"
    # Reset to another state and verify
    widgets.start_spin_box.setValue(0)
    widgets.stop_spin_box.setValue(10)
    display.ui.scan_pts_spin_box.setValue(6)
    assert widgets.step_label.text() == "2.0"


@pytest.mark.asyncio
async def test_plan_args(display, qtbot, xspress, ion_chamber):
    # set up motor num
    await display.regions.set_region_count(2)
    # set up a test motor 1
    widgets = display.regions.row_widgets(1)
    widgets.device_selector.combo_box.setCurrentText("async motor-1")
    widgets.start_spin_box.setValue(1)
    widgets.stop_spin_box.setValue(111)
    # set up a test motor 2
    widgets = display.regions.row_widgets(2)
    widgets.device_selector.combo_box.setCurrentText("sync_motor_2")
    widgets.start_spin_box.setValue(2)
    widgets.stop_spin_box.setValue(222)
    # set up scan num of points
    display.ui.scan_pts_spin_box.setValue(10)
    # time is calculated when the selection is changed
    display.ui.detectors_list.selected_detectors = mock.MagicMock(
        return_value=[xspress, ion_chamber]
    )
    # set up meta data
    display.ui.metadata_widget.sample_line_edit.setText("sam")
    display.ui.metadata_widget.purpose_combo_box.setCurrentText("test")
    display.ui.metadata_widget.notes_text_edit.setText("notes")
    # Check the arguments that will get used by the plan
    args, kwargs = display.plan_args()
    assert args == (
        ["vortex_me4", "I00"],
        "async motor-1",
        1.0,
        111.0,
        "sync_motor_2",
        2.0,
        222.0,
    )
    assert kwargs == {
        "num": 10,
        "md": {
            "sample_name": "sam",
            "purpose": "test",
            "notes": "notes",
        },
    }


async def test_full_motor_parameters(display, motors):
    await display.regions.set_region_count(2)
    motor = motors[0]
    # display.relative_scan_checkbox.setChecked(False)
    await display.regions.set_relative_position(False)
    set_mock_value(motor.user_readback, 7.5)
    region = display.regions[0]
    await display.regions.update_device_parameters(motor, row=1)
    widgets = display.regions.row_widgets(1)
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


async def test_relative_positioning(display, motors):
    await display.regions.set_region_count(2)
    motor = motors[0]
    widgets = display.regions.row_widgets(1)
    set_mock_value(motor.user_readback, 7.5)
    widgets.device_selector.current_component = mock.MagicMock(return_value=motor)
    widgets.start_spin_box.setValue(5.0)
    widgets.stop_spin_box.setValue(10.0)
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


async def test_update_devices(display, sim_registry):
    await display.regions.set_region_count(1)
    device_selector = display.regions.row_widgets(1).device_selector
    device_selector.update_devices = mock.AsyncMock()
    display.detectors_list.update_devices = mock.AsyncMock()
    await display.update_devices(sim_registry)
    assert device_selector.update_devices.called
    assert display.detectors_list.update_devices.called


def test_queue_plan(display, qtbot):
    # Make sure the plan can be submitted
    # Specific plan args should test `display.plan_args()`
    with qtbot.waitSignal(display.queue_item_submitted, timeout=2):
        display.queue_plan()


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman, Juan Juan Huang
# :email:     wolfman@anl.gov, juanjuan.huang@anl.gov
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
