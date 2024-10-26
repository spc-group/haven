import pytest
from bluesky_queueserver_api import BPlan
from ophyd import Component as Cpt
from ophyd import Signal
from ophyd.sim import SynAxis
from qtpy import QtCore

from firefly.robot import RobotDisplay


class FakeHavenMotor(SynAxis):
    user_offset = Cpt(Signal, value=0, kind="config")


@pytest.fixture
def sim_motor_registry(sim_registry):
    # Create the motors
    sim_registry.register(FakeHavenMotor(name="motor1"))
    sim_registry.register(FakeHavenMotor(name="motor2"))
    yield sim_registry


@pytest.fixture
async def display(qtbot, sim_motor_registry, robot):
    display = RobotDisplay(macros={"DEVICE": robot.name})
    qtbot.addWidget(display)
    await display.update_devices(sim_motor_registry)
    return display


def test_region_number(display):
    # Check that the display has the right number of rows to start with
    assert display.ui.sample_combo_box.count() == 10
    assert hasattr(display, "regions")
    assert len(display.regions) == 0


@pytest.mark.asyncio
async def test_robot_queued(qtbot, sim_motor_registry, display):
    await display.update_devices(sim_motor_registry)
    display.ui.run_button.setEnabled(True)
    display.ui.num_motor_spin_box.setValue(1)
    await display.update_regions(1)

    # set up a test motor
    display.regions[0].motor_box.combo_box.setCurrentText("motor1")
    display.regions[0].start_line_edit.setText("100")

    expected_item = BPlan("robot_transfer_sample", "robotA", 8, "motor1", 100)

    def check_item(item):
        return item.to_dict() == expected_item.to_dict()

    # Click the run button and see if the plan is queued
    with qtbot.waitSignal(
        display.queue_item_submitted, timeout=1000, check_params_cb=check_item
    ):
        qtbot.mouseClick(display.ui.run_button, QtCore.Qt.LeftButton)
