import pytest
from bluesky_queueserver_api import BPlan
from qtpy.QtWidgets import QPushButton

from firefly.plans.display import PlanDisplay
from firefly.plans.metadata import MetadataWidget


class DummyScanDisplay(PlanDisplay):
    plan_type = "dummy"

    def customize_ui(self):
        self.metadata_widget = MetadataWidget(parent=self)
        self.run_button = QPushButton(parent=self)

    def plan_args(self):
        return ("async_motor_1", 111.0, "sync_motor_2", 222.0), {}

    def ui_filename(self):
        return None


@pytest.fixture()
async def display(qtbot, sim_registry, sync_motors, async_motors):
    display = DummyScanDisplay()
    qtbot.addWidget(display)
    await display.update_devices(sim_registry)
    return display


@pytest.mark.asyncio
async def test_plan_queued(display, qtbot):
    """Test on a specific plan window since then we don't have to make one ourselves."""
    display.run_button.setEnabled(True)
    expected_item = BPlan(
        "dummy",
        "async_motor_1",
        111.0,
        "sync_motor_2",
        222.0,
    )
    plan_item = display.queue_plan()
    assert plan_item.to_dict() == expected_item.to_dict()


def test_plan_metadata(display):
    # Set metadata in the metadata widget
    display.metadata_widget.purpose_combo_box.setCurrentText("dancing")
    display.metadata_widget.standard_check_box.setChecked(True)
    # Set metadata from the beamline scheduling system
    display.update_bss_metadata(
        {
            "proposal_id": "123456",
        }
    )
    md = display.plan_metadata()
    assert md == {
        "is_standard": True,
        "purpose": "dancing",
        "proposal_id": "123456",
    }
