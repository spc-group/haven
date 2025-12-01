import asyncio
from unittest import mock

import pytest

from firefly.plans.count import CountDisplay


@pytest.fixture()
async def display(qtbot, sim_registry, dxp, ion_chamber):
    display = CountDisplay()
    qtbot.addWidget(display)
    await display.update_devices(sim_registry)
    display.run_button.setEnabled(True)
    try:
        yield display
    finally:
        await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_time_calculator(display, sim_registry, ion_chamber):
    # Set up detector list
    display.ui.detectors_list.acquire_times = mock.AsyncMock(return_value=[0.82])

    # Set up num of repeat scans
    display.ui.spinBox_repeat_scan_num.setValue(6)

    # Set up scan num of readings
    display.ui.num_spinbox.setValue(20)

    # Run the time calculator
    await display.update_total_time()

    # Check whether time is calculated correctly for a single scan
    assert display.ui.scan_duration_label.text() == "0 h 0 m 16 s"

    # Check whether time is calculated correctly including the repeated scan
    assert display.ui.total_duration_label.text() == "0 h 1 m 38 s"


def test_plan_args(display, qtbot, xspress):
    display.ui.run_button.setEnabled(True)
    display.ui.num_spinbox.setValue(5)
    display.ui.delay_spinbox.setValue(0.5)
    # Set up detector list
    display.ui.detectors_list.selected_detectors = mock.MagicMock(
        return_value=[xspress]
    )
    args, kwargs = display.plan_args()
    assert kwargs == dict(num=5, detectors=["vortex_me4"], delay=0.5, md={})


def test_plan_metadata(display, qtbot, xspress, ion_chamber):
    display.ui.run_button.setEnabled(True)
    display.ui.num_spinbox.setValue(5)
    # set up meta data
    display.metadata_widget.sample_line_edit.setText("LMO")
    display.metadata_widget.purpose_combo_box.setCurrentText("test")
    display.metadata_widget.notes_text_edit.setText("notes")
    display.metadata_widget.formula_line_edit.setText("LiMn0.5Ni0.5O")
    display.metadata_widget.standard_check_box.setChecked(True)
    display.ui.detectors_list.selected_detectors = mock.MagicMock(
        return_value=[xspress, ion_chamber]
    )
    args, kwargs = display.plan_args()
    assert kwargs == dict(
        num=5,
        detectors=["vortex_me4", "I00"],
        delay=0.0,
        md={
            "is_standard": True,
            "sample_name": "LMO",
            "purpose": "test",
            "notes": "notes",
            "sample_formula": "LiMn0.5Ni0.5O",
        },
    )


async def test_update_devices(display, sim_registry):
    display.detectors_list.update_devices = mock.AsyncMock()
    await display.update_devices(sim_registry)
    assert display.detectors_list.update_devices.called


def test_update_bss_metadata(display):
    md = {
        "esaf_title": "Xenonite XAFS",
        "esaf_id": "12345",
        "proposal_title": "New materials for interstellar space travel",
        "proposal_id": "5678",
    }
    display.update_bss_metadata(md)
    assert display.ui.metadata_widget.esaf_id_label.text() == "12345"


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
