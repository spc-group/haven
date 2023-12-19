from unittest import mock

from bluesky_queueserver_api import BPlan
from qtpy import QtCore

from firefly.plans.line_scan import LineScanDisplay

from ophyd.sim import make_fake_device
import pytest
from haven.instrument import motor


# fake motor copied from test_motor_menu.py, not sure this is right
@pytest.fixture
def fake_motors(sim_registry):
    motor_names = ["motorA_m2"]
    motors = []
    for name in motor_names:
        this_motor = make_fake_device(motor.HavenMotor)(name=name, labels={"motors"})
        sim_registry.register(this_motor)
        motors.append(this_motor)
    return motors


def test_line_scan_plan_queued(ffapp, qtbot, sim_registry):
    display = LineScanDisplay()
    display.ui.run_button.setEnabled(True)
    display.ui.scan_start_lineEdit.setText("10")
    display.ui.scan_stop_lineEdit.setText("20")
    display.ui.scan_pts_spin_box.setValue(5)
    display.ui.detectors_list.selected_detectors = mock.MagicMock(
        return_value=["vortex_me4", "I0"]
    )

    # Adding fake motor options to motor combobox
    motor_options = ["MotorA_m1", "MotorA_m2", "MotorA_m3"]
    display.ui.motorA_comboBox.addItems(motor_options)
    # Choose motorA_m1
    index = display.ui.combo.findText("MotorA_m1")
    if index >= 0:
        display.ui.combo.setCurrentIndex(index)

    expected_item = BPlan("scan", ["vortex_me4", "I0"], fake_motors, 10, 20, num=5)

    def check_item(item):
        from pprint import pprint

        pprint(item.to_dict())
        pprint(expected_item.to_dict())
        return item.to_dict() == expected_item.to_dict()

    # Click the run button and see if the plan is queued
    with qtbot.waitSignal(
        ffapp.queue_item_added, timeout=1000, check_params_cb=check_item
    ):
        qtbot.mouseClick(display.ui.run_button, QtCore.Qt.LeftButton)
