import pytest
from bluesky_queueserver_api import BPlan
from ophyd.sim import make_fake_device
from qtpy import QtCore

from firefly.plans.move_motor_window import MoveMotorDisplay
from haven.instrument import motor


@pytest.fixture
def fake_motors(sim_registry):
    motor_names = ["motorA_m1", "motorA_m2"]
    motors = []
    for name in motor_names:
        this_motor = make_fake_device(motor.HavenMotor)(name=name, labels={"motors"})
        motors.append(this_motor)
    return motors


@pytest.fixture()
async def display(qtbot, sim_registry, fake_motors):
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
    display.regions[0].motor_box.combo_box.setCurrentText("motorA_m1")
    display.regions[0].position_line_edit.setText("111")

    # set up a test motor 2
    display.regions[1].motor_box.combo_box.setCurrentText("motorA_m2")
    display.regions[1].position_line_edit.setText("222")

    expected_item = BPlan(
        "mv",
        "motorA_m1",
        111.0,
        "motorA_m2",
        222.0,
    )

    def check_item(item):
        print(item.to_dict())
        return item.to_dict() == expected_item.to_dict()

    # Click the run button and see if the plan is queued
    with qtbot.waitSignal(
        display.queue_item_submitted, timeout=1000, check_params_cb=check_item
    ):
        qtbot.mouseClick(display.ui.run_button, QtCore.Qt.LeftButton)
