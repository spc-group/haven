import pytest
from bluesky_queueserver_api import BPlan
from qtpy.QtWidgets import QPushButton

from firefly.display import SampleMetadata
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
    display.metadata_widget.scan_line_edit.setText("dance-off")
    display.metadata_widget.notes_text_edit.setText(
        "Wound up on this ship and snagged a block."
    )
    # Set metadata from the beamline scheduling system
    sample_metadata = SampleMetadata(
        is_standard=True,
        chemical_formula="Xe260",
        sample_name="Xenonite",
        dm_experiment="cabana-2026-C3",
    )
    display.update_sample_metadata(sample_metadata)
    md = display.plan_metadata()
    assert md == {
        "is_standard": True,
        "purpose": "dancing",
        "dm_exp": "cabana-2026-C3",
        "notes": "Wound up on this ship and snagged a block.",
        "scan_name": "dance-off",
        "sample_formula": "Xe260",
        "sample_name": "Xenonite",
    }


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2023, UChicago Argonne, LLC
#
# Distributed under the terms of the 3-Clause BSD License
#
# The full license is in the file LICENSE, distributed with this software.
#
# DISCLAIMER
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# -----------------------------------------------------------------------------
