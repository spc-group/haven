from firefly.robot import RobotDisplay

def test_region_number(qtbot):
    """Does changing the region number affect the UI?"""
    disp = RobotDisplay()
    qtbot.addWidget(disp)
    # Check that the display has the right number of rows to start with
    assert disp.ui.robot_spin_box.value() == 1
    assert disp.ui.sample_spin_box.value() == 10
    assert hasattr(disp, "regions")
    assert len(disp.regions) == 10


def test_robot_queued(ffapp, qtbot, sim_registry):
    display = RobotDisplay()
    display.ui.run_button.setEnabled(True)
    display.ui.num_motor_spin_box.setValue(3)
    
    expected_item = BPlan("robot_transfer_sample", "Austin", args)

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
