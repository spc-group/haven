import asyncio
import datetime as dt
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import AsyncMock

import pandas as pd
import pytest
import time_machine
from ophyd.sim import instantiate_fake_device
from qtpy.QtWidgets import QFileDialog

from firefly.run_browser.display import RunBrowserDisplay
from haven.devices.beamline_manager import EpicsBssDevice


@contextmanager
def block_signals(*widgets):
    """Disable Qt signals so tests can be set up."""
    for widget in widgets:
        widget.blockSignals(True)
    try:
        yield
    finally:
        for widget in widgets:
            widget.blockSignals(False)


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
    try:
        yield display
    finally:
        # Make sure all the db tasks have a chance to finish cleanly
        [task.cancel() for task in display._running_db_tasks.values()]
        # tasks = asyncio.gather(*display._running_db_tasks.values())
        # print("Awaiting tasks")
        # from pprint import pprint
        # pprint(list(display._running_db_tasks.values()))
        # await asyncio.wait_for(tasks, timeout=5)


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


async def test_load_runs(display):
    await display.load_runs()
    assert display.runs_model.rowCount() > 0
    assert display.ui.runs_total_label.text() == str(display.runs_model.rowCount())


async def test_selected_uids(display):
    await display.load_runs()
    # No rows at first
    assert display.selected_uids() == set()
    # Check a row
    row, col = (0, 0)
    display.ui.runs_model.item(0, 0).setCheckState(True)
    # Now there are some selected rows
    assert len(display.selected_uids()) == 1


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


async def test_update_internal_dataframes(display, qtbot, mocker):
    display.selected_uids = mocker.MagicMock(
        return_value={"85573831-f4b4-4f64-b613-a6007bf03a8d"}
    )
    with block_signals(display.ui.stream_combobox, display.ui.x_signal_combobox):
        display.ui.stream_combobox.addItem("primary")
        display.ui.x_signal_combobox.addItem("mono-energy")
    display.ui.multiplot_tab.plot = mocker.MagicMock()
    await display.update_internal_dataframes()
    # Check that the plotting routines were called correctly
    assert display.ui.multiplot_tab.plot.called
    args, kwargs = display.ui.multiplot_tab.plot.call_args
    dfs = args[0]
    assert len(dfs) == 1
    df = dfs["85573831-f4b4-4f64-b613-a6007bf03a8d"]
    assert isinstance(df, pd.DataFrame)


async def test_update_datasets(display, qtbot, mocker):
    display.selected_uids = mocker.MagicMock(return_value={"xarray_run"})
    with block_signals(
        display.ui.stream_combobox,
        display.ui.x_signal_combobox,
        display.ui.y_signal_combobox,
        display.ui.r_signal_combobox,
    ):
        display.ui.stream_combobox.addItem("primary")
        display.ui.x_signal_combobox.addItem("mono-energy")
        display.ui.y_signal_combobox.addItem("It-net_count")
        display.ui.r_signal_combobox.addItem("I0-net_count")
    # Check that the clients got called
    display.ui.lineplot_tab.plot = mocker.MagicMock()
    display.ui.gridplot_tab.plot = mocker.MagicMock()
    display.ui.frameset_tab.plot = mocker.MagicMock()
    display.ui.spectra_tab.plot = mocker.MagicMock()
    await display.update_datasets()
    assert display.ui.lineplot_tab.plot.called
    args, kwargs = display.ui.lineplot_tab.plot.call_args
    datasets = args[0]
    assert len(datasets) == 1
    ds = datasets["xarray_run"]
    assert "mono-energy" in ds
    assert "It-net_count" in ds
    assert "I0-net_count" in ds
    # Check that the other view plot methods were called
    assert display.ui.gridplot_tab.plot.called
    assert display.ui.frameset_tab.plot.called
    assert display.ui.spectra_tab.plot.called


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


@pytest.mark.asyncio
async def test_signal_options(display, mocker):
    """
    We need to know:
    - data_keys
    - independent hints (scan axes)
    - dependent hints (device hints)

    Used '64e85e20-106c-48e6-b643-77e9647b0242' for testing in the
    haven-dev catalog.

    """
    display.selected_uids = mocker.MagicMock(
        return_value={"85573831-f4b4-4f64-b613-a6007bf03a8d"}
    )
    with block_signals(display.ui.stream_combobox, display.ui.use_hints_checkbox):
        await display.update_streams()
        display.ui.stream_combobox.setCurrentText("primary")
        display.ui.use_hints_checkbox.setChecked(False)
    # Check that we got the right signals in the right order
    await display.update_signal_widgets()
    expected_signals = [
        "energy_energy",
        "ge_8element",
        "ge_8element-deadtime_factor",
        "I0-net_count",
        "seq_num",
    ]
    combobox = display.ui.x_signal_combobox
    signals = [combobox.itemText(idx) for idx in range(combobox.count())]
    assert signals == expected_signals
    combobox = display.ui.y_signal_combobox
    signals = [combobox.itemText(idx) for idx in range(combobox.count())]
    assert signals == expected_signals
    combobox = display.ui.r_signal_combobox
    signals = [combobox.itemText(idx) for idx in range(combobox.count())]
    assert signals == expected_signals


@pytest.mark.asyncio
async def test_hinted_signal_options(display, mocker):
    """
    We need to know:
    - data_keys
    - independent hints (scan axes)
    - dependent hints (device hints)

    Used '64e85e20-106c-48e6-b643-77e9647b0242' for testing in the
    haven-dev catalog.

    """
    display.selected_uids = mocker.MagicMock(
        return_value={"85573831-f4b4-4f64-b613-a6007bf03a8d"}
    )
    with block_signals(display.ui.stream_combobox, display.ui.use_hints_checkbox):
        display.ui.stream_combobox.addItem("primary")
        display.ui.use_hints_checkbox.setChecked(True)
    await display.update_signal_widgets()
    # Check hinted X signals
    combobox = display.ui.x_signal_combobox
    signals = [combobox.itemText(idx) for idx in range(combobox.count())]
    assert signals == ["aerotech_horiz", "aerotech_vert"]
    # Check hinted Y signals
    expected_signals = [
        "aerotech_horiz",
        "aerotech_vert",
        "CdnI0_net_counts",
        "CdnIPreKb_net_counts",
        "CdnIt_net_counts",
        "I0_net_counts",
        "Ipre_KB_net_counts",
        "Ipreslit_net_counts",
        "It_net_counts",
    ]
    combobox = display.ui.y_signal_combobox
    signals = [combobox.itemText(idx) for idx in range(combobox.count())]
    assert signals == expected_signals
    # Check hinted reference signals
    combobox = display.ui.r_signal_combobox
    signals = [combobox.itemText(idx) for idx in range(combobox.count())]
    assert signals == expected_signals


@pytest.mark.xfail
def test_prepare_plotting_data():
    assert False


@pytest.mark.xfail
def test_label_from_metadata():
    assert False


@pytest.mark.xfail
def test_swap_signals(view, qtbot):
    assert view.ui.y_signal_combobox.currentText() == "It-net_current"
    assert view.ui.r_signal_combobox.currentText() == "I0-net_current"
    view.swap_signals()
    assert view.ui.y_signal_combobox.currentText() == "I0-net_current"
    assert view.ui.r_signal_combobox.currentText() == "It-net_current"


@pytest.mark.xfail
def test_update_plot_mean(view):
    view.independent_hints = ["energy_energy"]
    view.dependent_hints = ["I0-net_current"]
    # view.data_keys = data_keys
    view.ui.aggregator_combobox.setCurrentText("StDev")
    # Update the plots
    # view.plot(dataframes)
    # Check the data were plotted
    plot_item = view.ui.plot_widget.getPlotItem()
    assert len(plot_item.dataItems) == 1


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
