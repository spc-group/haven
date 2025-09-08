import asyncio
import datetime as dt
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import time_machine
from ophyd.sim import instantiate_fake_device
from qtpy.QtWidgets import QFileDialog

from firefly.run_browser.display import RunBrowserDisplay
from haven.devices.beamline_manager import EpicsBssDevice


@pytest.fixture()
def bss(sim_registry):
    bss_ = instantiate_fake_device(EpicsBssDevice, prefix="apsbss:", name="bss")
    return bss_


@pytest.fixture()
async def display(qtbot, mocker, tiled_client):
    mocker.patch(
        "firefly.run_browser.widgets.ExportDialog.exec_",
        return_value=QFileDialog.Accepted,
    )
    mocker.patch(
        "firefly.run_browser.widgets.ExportDialog.selectedFiles",
        return_value=["/net/s255data/export/test_file.nx"],
    )
    mocker.patch("firefly.run_browser.client.DatabaseWorker.export_runs")
    mocker.patch(
        "firefly.run_browser.display.list_profiles",
        return_value={
            "cortex": Path("/tmp/cortex"),
            "fedorov": Path("/tmp/fedorov"),
        },
    )
    mocker.patch(
        "firefly.run_browser.display.get_default_profile_name", return_value="cortex"
    )
    display = RunBrowserDisplay()
    qtbot.addWidget(display)
    display.clear_filters()
    # Wait for the initial database load to process
    display.db.catalog = tiled_client
    await display.load_runs()
    return display


async def test_db_task(display):
    async def test_coro():
        return 15

    result = await display.db_task(test_coro())
    assert result == 15


async def test_db_task_interruption(display):
    async def test_coro(sleep_time):
        await asyncio.sleep(sleep_time)
        return sleep_time

    # Create an existing task that will be cancelled
    task_1 = display.db_task(test_coro(1.0), name="testing")
    # Now execute another task
    result = await display.db_task(test_coro(0.01), name="testing")
    assert result == 0.01
    # Check that the first one was cancelled
    with pytest.raises(asyncio.exceptions.CancelledError):
        await task_1
    assert task_1.done()
    assert task_1.cancelled()


def test_load_runs(display):
    assert display.runs_model.rowCount() > 0
    assert display.ui.runs_total_label.text() == str(display.runs_model.rowCount())


async def test_metadata(display, qtbot, mocker):
    display.selected_uids = mocker.MagicMock(
        return_value={"85573831-f4b4-4f64-b613-a6007bf03a8d"}
    )
    with qtbot.wait_signal(display.metadata_changed):
        new_md = await display.update_metadata()
    assert "85573831-f4b4-4f64-b613-a6007bf03a8d" in new_md


def test_busy_hints_run_widgets(display):
    """Check that the display widgets get disabled during DB hits."""
    with display.busy_hints(run_widgets=True, run_table=False):
        # Are widgets disabled in the context block?
        assert not display.ui.detail_tabwidget.isEnabled()
    # Are widgets re-enabled outside the context block?
    assert display.ui.detail_tabwidget.isEnabled()


def test_busy_hints_run_table(display):
    """Check that the all_runs table view gets disabled during DB hits."""
    with display.busy_hints(run_table=True, run_widgets=False):
        # Are widgets disabled in the context block?
        assert not display.ui.run_tableview.isEnabled()
    # Are widgets re-enabled outside the context block?
    assert display.ui.run_tableview.isEnabled()


def test_busy_hints_filters(display):
    """Check that the all_runs table view gets disabled during DB hits."""
    with display.busy_hints(run_table=False, run_widgets=False, filter_widgets=True):
        # Are widgets disabled in the context block?
        assert not display.ui.filters_widget.isEnabled()
    # Are widgets re-enabled outside the context block?
    assert display.ui.filters_widget.isEnabled()


def test_busy_hints_status(display, mocker):
    """Check that any busy_hints displays the message "Loading…"."""
    spy = mocker.spy(display, "show_message")
    with display.busy_hints(run_table=True, run_widgets=False):
        # Are widgets disabled in the context block?
        assert not display.ui.run_tableview.isEnabled()
        assert spy.call_count == 1
    # Are widgets re-enabled outside the context block?
    assert spy.call_count == 2
    assert display.ui.run_tableview.isEnabled()


def test_busy_hints_multiple(display):
    """Check that multiple busy hints can co-exist."""
    # Next the busy_hints context to mimic multiple async calls
    with display.busy_hints(run_widgets=True):
        # Are widgets disabled in the outer block?
        assert not display.ui.detail_tabwidget.isEnabled()
        with display.busy_hints(run_widgets=True):
            # Are widgets disabled in the inner block?
            assert not display.ui.detail_tabwidget.isEnabled()
        # Are widgets still disabled in the outer block?
        assert not display.ui.detail_tabwidget.isEnabled()
    # Are widgets re-enabled outside the context block?
    assert display.ui.detail_tabwidget.isEnabled()


async def test_auto_bss_filters(display):
    # First set the BSS metadata when the "current" box is checked
    display.filter_current_proposal_checkbox.setChecked(True)
    display.filter_current_esaf_checkbox.setChecked(True)
    display.update_bss_metadata(
        {
            "proposal_id": "12345",
            "esaf_id": "56789",
        }
    )
    assert display.filter_proposal_combobox.currentText() == "12345"
    assert display.filter_esaf_combobox.currentText() == "56789"
    # Now cache some BSS metadata with the "current" box unchecked
    display.filter_current_proposal_checkbox.setChecked(False)
    display.filter_current_esaf_checkbox.setChecked(False)
    display.update_bss_metadata(
        {
            "proposal_id": "54321",
            "esaf_id": "98765",
        }
    )
    assert display.filter_proposal_combobox.currentText() == "12345"  # Not updated yet
    assert display.filter_esaf_combobox.currentText() == "56789"  # Not updated yet
    # Now re-enable the "current" checkboxes and see if the widgets update
    display.filter_current_proposal_checkbox.setChecked(True)
    display.filter_current_esaf_checkbox.setChecked(True)
    assert display.filter_proposal_combobox.currentText() == "54321"
    assert display.filter_esaf_combobox.currentText() == "98765"


async def test_update_combobox_items(display):
    """Check that the comboboxes get the distinct filter fields."""
    await display.update_combobox_items()
    # Some of these have filters are disabled because they are slow
    # with sqlite They may be re-enabled when switching to postgres
    assert display.ui.filter_plan_combobox.count() > 0
    assert display.ui.filter_sample_combobox.count() > 0
    assert display.ui.filter_formula_combobox.count() > 0
    assert display.ui.filter_scan_combobox.count() > 0
    assert display.ui.filter_edge_combobox.count() > 0
    assert display.ui.filter_exit_status_combobox.count() > 0
    assert display.ui.filter_proposal_combobox.count() > 0
    assert display.ui.filter_esaf_combobox.count() > 0
    assert display.ui.filter_beamline_combobox.count() > 0


async def test_export_button_enabled(display):
    assert not display.export_button.isEnabled()
    # Update the list with 1 run and see if the control gets enabled
    display.selected_runs = [{}]
    display.update_export_button()
    assert display.export_button.isEnabled()
    # Update the list with multiple runs and see if the control gets disabled
    display.selected_runs = [{}, {}]
    display.update_export_button()
    assert not display.export_button.isEnabled()


async def test_export_button_clicked(display, mocker, qtbot):
    # Set up a run to be tested against
    run = AsyncMock()
    run.formats.return_value = [
        "application/json",
        "application/x-hdf5",
        "application/x-nexus",
    ]
    display.selected_runs = [run]
    display.update_export_button()
    # Clicking the button should open a file dialog
    await display.export_runs()
    assert display.export_dialog.exec_.called
    assert display.export_dialog.selectedFiles.called
    # Check that file filter names are set correctly
    # (assumes application/json is available on every machine)
    assert "JSON document (*.json)" in display.export_dialog.nameFilters()
    # Check that the file was saved
    assert display.db.export_runs.called
    files = display.export_dialog.selectedFiles.return_value
    assert display.db.export_runs.call_args.args == (files,)
    assert display.db.export_runs.call_args.kwargs["formats"] == ["application/json"]


fake_time = dt.datetime(2022, 8, 19, 19, 10, 51).astimezone()


@time_machine.travel(fake_time, tick=False)
def test_default_filters(display):
    display.reset_default_filters()
    assert display.ui.filter_exit_status_combobox.currentText() == "success"
    assert display.ui.filter_current_esaf_checkbox.checkState()
    assert display.ui.filter_current_proposal_checkbox.checkState()
    # Test datetime filters
    assert display.ui.filter_after_checkbox.checkState()
    last_week = dt.datetime(2022, 8, 12, 19, 10, 51)
    after_filter_time = display.ui.filter_after_datetimeedit.dateTime()
    after_filter_time = dt.datetime.fromtimestamp(after_filter_time.toTime_t())
    assert after_filter_time == last_week
    next_week = dt.datetime(2022, 8, 26, 19, 10, 51)
    before_filter_time = display.ui.filter_before_datetimeedit.dateTime()
    before_filter_time = dt.datetime.fromtimestamp(before_filter_time.toTime_t())
    assert before_filter_time == next_week
    # Test beamline filters
    assert (
        display.ui.filter_beamline_combobox.currentText()
        == "SPC Beamline (sector unknown)"
    )


def test_time_filters(display):
    """Check that the before and after datetime filters are activated."""
    display.ui.filter_after_checkbox.setChecked(False)
    display.ui.filter_before_checkbox.setChecked(False)
    filters = display.filters()
    assert "after" not in filters
    assert "before" not in filters
    display.ui.filter_after_checkbox.setChecked(True)
    display.ui.filter_before_checkbox.setChecked(True)
    filters = display.filters()
    assert "after" in filters
    assert "before" in filters


async def test_update_data_frames(display, qtbot, mocker):
    display.selected_uids = mocker.MagicMock(
        return_value={
            "85573831-f4b4-4f64-b613-a6007bf03a8d",
            "7d1daf1d-60c7-4aa7-a668-d1cd97e5335f",
        }
    )
    display.ui.stream_combobox.addItem("primary")
    display.ui.stream_combobox.setCurrentText("primary")
    with qtbot.waitSignal(display.data_frames_changed):
        await display.update_data_frames()


async def test_profile_choices(display):
    combobox = display.ui.profile_combobox
    items = [combobox.itemText(idx) for idx in range(combobox.count())]
    assert items == ["cortex", "fedorov"]


async def test_stream_choices(display, mocker):
    display.selected_uids = mocker.MagicMock(
        return_value={"85573831-f4b4-4f64-b613-a6007bf03a8d"}
    )
    await display.update_streams()
    combobox = display.ui.stream_combobox
    items = [combobox.itemText(idx) for idx in range(combobox.count())]
    assert items == ["primary", "baseline"]


async def test_retrieve_dataset(display, qtbot):
    # See '788b1d91-efa1-4b26-9a0a-3454aa7e1a93' for a sample dataset
    with qtbot.wait_signal(display.datasets_changed):
        await display.fetch_datasets("ge_8element", "testing")


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
