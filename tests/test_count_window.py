from unittest import mock

from qtpy import QtCore
from bluesky_queueserver_api import BPlan

from firefly.plans.count import CountDisplay

def test_count_plan_queued(ffapp, qtbot, sim_registry):
    display = CountDisplay()
    display.ui.run_button.setEnabled(True)
    display.ui.num_spinbox.setValue(5)
    display.ui.delay_spinbox.setValue(0.5)
    expected_item = BPlan("count", num=5, detectors=[], delay=0.5)

    def check_item(item):
        from pprint import pprint
        pprint(item.to_dict())
        pprint(expected_item.to_dict())
        return item.to_dict() == expected_item.to_dict()

    # Click the run button and see if the plan is queued
    with qtbot.waitSignal(ffapp.queue_item_added, timeout=1000, check_params_cb=check_item):
        qtbot.mouseClick(display.ui.run_button, QtCore.Qt.LeftButton)
        
