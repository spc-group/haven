from pprint import pprint
from unittest import mock

import pytest
from bluesky_queueserver_api import BPlan
from ophyd.sim import make_fake_device
from qtpy import QtCore

from firefly.plans.line_scan import LineScanDisplay
from haven.instrument import motor


@pytest.fixture
def fake_motors(sim_registry):
    motor_names = ["motorA_m1", "motorA_m2"]
    motors = []
    for name in motor_names:
        this_motor = make_fake_device(motor.HavenMotor)(name=name, labels={"motors"})
        sim_registry.register(this_motor)
        motors.append(this_motor)
    return motors


def test_line_scan_plan_queued(ffapp, qtbot, sim_registry, fake_motors):
    display = LineScanDisplay()
    display.ui.run_button.setEnabled(True)
    display.ui.num_motor_spin_box.setValue(2)
    display.update_regions()

    # set up a test motor 1
    display.regions[0].motor_box.combo_box.setCurrentText("motorA_m1")
    display.regions[0].start_line_edit.setText("1")
    display.regions[0].stop_line_edit.setText("111")

    # set up a test motor 2
    display.regions[1].motor_box.combo_box.setCurrentText("motorA_m2")
    display.regions[1].start_line_edit.setText("2")
    display.regions[1].stop_line_edit.setText("222")

    # set up scan num of points
    display.ui.scan_pts_spin_box.setValue(10)

    # set up detector list
    display.ui.detectors_list.selected_detectors = mock.MagicMock(
        return_value=["vortex_me4", "I0"]
    )

    # set up meta data
    display.ui.lineEdit_sample.setText("sam")
    display.ui.lineEdit_purpose.setText("test")

    expected_item = BPlan(
        "scan",
        ["vortex_me4", "I0"],
        "motorA_m1",
        1,
        111,
        "motorA_m2",
        2,
        222,
        num=10,
        md={"sample": "sam", "purpose": "test"},
    )

    def check_item(item):
        pprint(item.to_dict())
        pprint(expected_item.to_dict())
        return item.to_dict() == expected_item.to_dict()

    # Click the run button and see if the plan is queued
    with qtbot.waitSignal(
        ffapp.queue_item_added, timeout=1000, check_params_cb=check_item
    ):
        qtbot.mouseClick(display.ui.run_button, QtCore.Qt.LeftButton)
