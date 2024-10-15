from unittest import mock

import pytest
from bluesky_queueserver_api import BPlan

from firefly.plans.move_motor_window import MoveMotorDisplay


@pytest.fixture()
async def display(qtbot, sim_registry, sync_motors, async_motors):
    display = MoveMotorDisplay()
    qtbot.addWidget(display)
    await display.update_devices(sim_registry)
    return display


@pytest.mark.asyncio
async def test_move_motor_plan_queued(display, qtbot, monkeypatch):
    monkeypatch.setattr(display, "submit_queue_item", mock.MagicMock())
    display.ui.run_button.setEnabled(True)
    # uncheck relative
    display.ui.relative_scan_checkbox.setChecked(False)
    await display.update_regions(2)
    # set up a test motor 1
    display.regions[0].motor_box.combo_box.setCurrentText("async_motor_1")
    display.regions[0].position_line_edit.setText("111")
    # set up a test motor 2
    display.regions[1].motor_box.combo_box.setCurrentText("sync_motor_2")
    display.regions[1].position_line_edit.setText("222")
    expected_item = BPlan(
        "mv",
        "async_motor_1",
        111.0,
        "sync_motor_2",
        222.0,
    )
    # Run the code under test
    display.queue_plan()
    # Check that the right plan was submitted
    assert display.submit_queue_item.called
    submitted_item = display.submit_queue_item.call_args[0][0]
    assert submitted_item.to_dict() == expected_item.to_dict()
