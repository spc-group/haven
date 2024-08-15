from unittest import mock

import pytest
from bluesky_queueserver_api import BPlan
from ophyd.sim import make_fake_device
from qtpy import QtCore

from firefly.plans.line_scan import LineScanDisplay
from haven.instrument import motor


@pytest.fixture()
async def display(qtbot, sim_registry, sync_motors, async_motors, dxp, I0):
    display = LineScanDisplay()
    qtbot.addWidget(display)
    await display.update_devices(sim_registry)
    display.ui.run_button.setEnabled(True)
    return display


@pytest.mark.asyncio
async def test_time_calculator(display, sim_registry):
    # set up motor num
    await display.update_regions(2)

    # set up num of repeat scans
    display.ui.spinBox_repeat_scan_num.setValue(6)

    # set up scan num of points
    display.ui.scan_pts_spin_box.setValue(1000)

    # set up detectors
    display.ui.detectors_list.selected_detectors = mock.MagicMock(
        return_value=["vortex_me4", "I0"]
    )

    # set up default timing for the detector
    detectors = display.ui.detectors_list.selected_detectors()
    detectors = {name: sim_registry[name] for name in detectors}
    detectors["I0"].default_time_signal.set(0.6255).wait(2)
    detectors["vortex_me4"].default_time_signal.set(0.5).wait(2)

    # Create empty QItemSelection objects
    selected = QtCore.QItemSelection()
    deselected = QtCore.QItemSelection()

    # emit the signal so that the time calculator is triggered
    display.ui.detectors_list.selectionModel().selectionChanged.emit(
        selected, deselected
    )

    # Check whether time is calculated correctly for a single scan
    assert display.ui.label_hour_scan.text() == "0"
    assert display.ui.label_min_scan.text() == "10"
    assert display.ui.label_sec_scan.text() == "25.5"

    # Check whether time is calculated correctly including the repeated scan
    assert display.ui.label_hour_total.text() == "1"
    assert display.ui.label_min_total.text() == "2"
    assert display.ui.label_sec_total.text() == "33.0"


@pytest.mark.asyncio
async def test_line_scan_plan_queued(qtbot, display):
    # set up motor num
    await display.update_regions(2)

    # set up a test motor 1
    display.regions[0].motor_box.combo_box.setCurrentText("async_motor_1")
    display.regions[0].start_line_edit.setText("1")
    display.regions[0].stop_line_edit.setText("111")

    # set up a test motor 2
    display.regions[1].motor_box.combo_box.setCurrentText("sync_motor_2")
    display.regions[1].start_line_edit.setText("2")
    display.regions[1].stop_line_edit.setText("222")

    # set up scan num of points
    display.ui.scan_pts_spin_box.setValue(10)

    # time is calculated when the selection is changed
    display.ui.detectors_list.selected_detectors = mock.MagicMock(
        return_value=["vortex_me4", "I0"]
    )

    # set up meta data
    display.ui.lineEdit_sample.setText("sam")
    display.ui.lineEdit_purpose.setText("test")
    display.ui.textEdit_notes.setText("notes")

    expected_item = BPlan(
        "scan",
        ["vortex_me4", "I0"],
        "async_motor_1",
        1.0,
        111.0,
        "sync_motor_2",
        2.0,
        222.0,
        num=10,
        md={"sample": "sam", "purpose": "test", "notes": "notes"},
    )

    def check_item(item):
        from pprint import pprint
        pprint(item.to_dict())
        pprint(expected_item.to_dict())
        return item.to_dict() == expected_item.to_dict()

    # Click the run button and see if the plan is queued
    with qtbot.waitSignal(
        display.queue_item_submitted, timeout=1000, check_params_cb=check_item
    ):
        qtbot.mouseClick(display.ui.run_button, QtCore.Qt.LeftButton)
