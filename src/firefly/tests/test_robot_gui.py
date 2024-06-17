import pytest

from bluesky_queueserver_api import BPlan
from ophyd import Signal
from ophyd import Component as Cpt
from ophyd.sim import SynAxis
from qtpy import QtCore

from firefly.robot import RobotDisplay


def test_region_number(qtbot, robot):
    disp = RobotDisplay(macros={"DEVICE": robot.name})
    qtbot.addWidget(disp)
    # Check that the display has the right number of rows to start with
    assert disp.ui.sample_combo_box.count() == 10
    assert hasattr(disp, "regions")
    assert len(disp.regions) == 1


class FakeHavenMotor(SynAxis):
    user_offset = Cpt(Signal, value=0, kind="config")


@pytest.fixture
def sim_motor_registry(sim_registry):
    # Create the motors
    motor1 = FakeHavenMotor(name="motor1")
    motor2 = FakeHavenMotor(name="motor2")
    yield sim_registry


def test_robot_queued(ffapp, qtbot, sim_registry, robot, sim_motor_registry):
    display = RobotDisplay(macros={"DEVICE": robot.name})
    display.ui.run_button.setEnabled(True)
    display.ui.num_motor_spin_box.setValue(1)
    display.update_regions()

    # set up a test motor
    display.regions[0].motor_box.combo_box.setCurrentText("motor1")
    display.regions[0].start_line_edit.setText("100")

    expected_item = BPlan("robot_transfer_sample", "robotA", 8, "motor1", 100)

    def check_item(item):
        return item.to_dict() == expected_item.to_dict()

    # Click the run button and see if the plan is queued
    with qtbot.waitSignal(
        ffapp.queue_item_added, timeout=1000, check_params_cb=check_item
    ):
        qtbot.mouseClick(display.ui.run_button, QtCore.Qt.LeftButton)
