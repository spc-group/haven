import asyncio
from unittest.mock import MagicMock

import numpy as np
import pytest
from pyqtgraph import ImageItem, ImageView, PlotItem, PlotWidget
from qtpy.QtWidgets import QFileDialog

from firefly.run_browser import RunBrowserDisplay
from firefly.run_client import DatabaseWorker


@pytest.fixture()
async def display(qtbot, catalog, mocker):
    mocker.patch(
        "firefly.run_browser.ExportDialog.exec_", return_value=QFileDialog.Accepted
    )
    mocker.patch(
        "firefly.run_browser.ExportDialog.selectedFiles",
        return_value=["/net/s255data/export/test_file.nx"],
    )
    mocker.patch("firefly.run_client.DatabaseWorker.export_runs")
    display = RunBrowserDisplay(root_node=catalog)
    qtbot.addWidget(display)
    display.clear_filters()
    # Wait for the initial database load to process
    await display._running_db_tasks["init_load_runs"]
    await display._running_db_tasks["update_combobox_items"]
    return display


@pytest.mark.asyncio
async def test_db_task(display):
    async def test_coro():
        return 15

    result = await display.db_task(test_coro())
    assert result == 15


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_update_selected_runs(display):
    # Change the proposal item
    item = display.runs_model.item(0, 1)
    assert item is not None
    display.ui.run_tableview.selectRow(0)
    # Update the runs
    await display.update_selected_runs()
    # Check that the runs were saved
    assert len(display.db.selected_runs) > 0


@pytest.mark.asyncio
async def test_metadata(display):
    # Change the proposal item
    display.ui.run_tableview.selectRow(0)
    await display.update_selected_runs()
    # Check that the metadata was set properly in the Metadata tab
    text = display.ui.metadata_textedit.document().toPlainText()
    assert "xafs_scan" in text


@pytest.mark.asyncio
async def test_1d_plot_signals(catalog, display):
    # Check that the 1D plot was created
    plot_widget = display.ui.plot_1d_view
    plot_item = display.plot_1d_item
    assert isinstance(plot_widget, PlotWidget)
    assert isinstance(plot_item, PlotItem)
    # Update the list of runs and see if the controls get updated
    display.ui.run_tableview.selectColumn(0)
    await display.update_selected_runs()
    # Check signals in checkboxes
    for combobox in [
        display.ui.signal_y_combobox,
        display.ui.signal_r_combobox,
        display.ui.signal_x_combobox,
    ]:
        assert (
            combobox.findText("energy_energy") > -1
        ), f"energy_energy signal not in {combobox.objectName()}."


# Warns: Task was destroyed but it is pending!
@pytest.mark.asyncio
async def test_1d_plot_signal_memory(catalog, display):
    """Do we remember the signals that were previously selected."""
    # Check that the 1D plot was created
    plot_widget = display.ui.plot_1d_view
    plot_item = display.plot_1d_item
    assert isinstance(plot_widget, PlotWidget)
    assert isinstance(plot_item, PlotItem)
    # Update the list of runs and see if the controls get updated
    display.ui.run_tableview.selectRow(1)
    await display.update_selected_runs()
    # Check signals in comboboxes
    cb = display.ui.signal_y_combobox
    assert cb.currentText() == "energy_energy"
    cb.setCurrentIndex(1)
    assert cb.currentText() == "energy_id_energy_readback"
    # Update the combobox signals and make sure the text didn't change
    await display.update_1d_signals()
    assert cb.currentText() == "energy_id_energy_readback"


# Warns: Task was destroyed but it is pending!
@pytest.mark.asyncio
async def test_1d_hinted_signals(catalog, display):
    display.ui.plot_1d_hints_checkbox.setChecked(True)
    # Check that the 1D plot was created
    plot_widget = display.ui.plot_1d_view
    plot_item = display.plot_1d_item
    assert isinstance(plot_widget, PlotWidget)
    assert isinstance(plot_item, PlotItem)
    # Update the list of runs and see if the controls get updated
    display.db.selected_runs = [run async for run in catalog.values()]
    await display.update_1d_signals()
    return
    # Check signals in checkboxes
    combobox = display.ui.signal_x_combobox
    assert (
        combobox.findText("energy_energy") > -1
    ), f"hinted signal not in {combobox.objectName()}."
    assert (
        combobox.findText("It_net_counts") == -1
    ), f"unhinted signal found in {combobox.objectName()}."


@pytest.mark.asyncio
async def test_update_1d_plot(catalog, display):
    # Set up some fake data
    run = [run async for run in catalog.values()][0]
    display.db.selected_runs = [run]
    await display.update_1d_signals()
    run_data = await run.to_dataframe()
    expected_xdata = run_data.energy_energy
    expected_ydata = np.log(run_data.I0_net_counts / run_data.It_net_counts)
    expected_ydata = np.gradient(expected_ydata, expected_xdata)
    # Set the controls to describe the data we want to test
    x_combobox = display.ui.signal_x_combobox
    x_combobox.addItem("energy_energy")
    x_combobox.setCurrentText("energy_energy")
    y_combobox = display.ui.signal_y_combobox
    y_combobox.addItem("It_net_counts")
    y_combobox.setCurrentText("It_net_counts")
    r_combobox = display.ui.signal_r_combobox
    r_combobox.addItem("I0_net_counts")
    r_combobox.setCurrentText("I0_net_counts")
    display.ui.signal_r_checkbox.setChecked(True)
    display.ui.logarithm_checkbox.setChecked(True)
    display.ui.invert_checkbox.setChecked(True)
    display.ui.gradient_checkbox.setChecked(True)
    # Update the plots
    await display.update_1d_plot()
    # Check that the data were added
    data_item = display.plot_1d_item.listDataItems()[0]
    xdata, ydata = data_item.getData()
    np.testing.assert_almost_equal(xdata, expected_xdata)
    np.testing.assert_almost_equal(ydata, expected_ydata)


# Warns: Task was destroyed but it is pending!
@pytest.mark.asyncio
async def test_2d_plot_signals(catalog, display):
    # Check that the 1D plot was created
    plot_widget = display.ui.plot_2d_view
    plot_item = display.plot_2d_item
    assert isinstance(plot_widget, ImageView)
    assert isinstance(plot_item, ImageItem)
    # Update the list of runs and see if the controls get updated
    display.db.selected_runs = [await catalog["85573831-f4b4-4f64-b613-a6007bf03a8d"]]
    await display.update_2d_signals()
    # Check signals in checkboxes
    combobox = display.ui.signal_value_combobox
    assert combobox.findText("It_net_counts") > -1


@pytest.mark.asyncio
async def test_update_2d_plot(catalog, display):
    display.plot_2d_item.setRect = MagicMock()
    # Load test data
    run = await catalog["85573831-f4b4-4f64-b613-a6007bf03a8d"]
    display.db.selected_runs = [run]
    await display.update_1d_signals()
    # Set the controls to describe the data we want to test
    val_combobox = display.ui.signal_value_combobox
    val_combobox.addItem("It_net_counts")
    val_combobox.setCurrentText("It_net_counts")
    display.ui.logarithm_checkbox_2d.setChecked(True)
    display.ui.invert_checkbox_2d.setChecked(True)
    display.ui.gradient_checkbox_2d.setChecked(True)
    # Update the plots
    await display.update_2d_plot()
    # Determine what the image data should look like
    expected_data = await run["It_net_counts"]
    expected_data = expected_data.reshape((5, 21)).T
    # Check that the data were added
    image = display.plot_2d_item.image
    np.testing.assert_almost_equal(image, expected_data)
    # Check that the axes were formatted correctly
    axes = display.plot_2d_view.view.axes
    xaxis = axes["bottom"]["item"]
    yaxis = axes["left"]["item"]
    assert xaxis.labelText == "aerotech_horiz"
    assert yaxis.labelText == "aerotech_vert"
    display.plot_2d_item.setRect.assert_called_with(-100, -80, 200, 160)


@pytest.mark.asyncio
async def test_update_multi_plot(catalog, display):
    run = await catalog["7d1daf1d-60c7-4aa7-a668-d1cd97e5335f"]
    expected_xdata = await run["energy_energy"]
    expected_ydata = np.log(await run["I0_net_counts"] / await run["It_net_counts"])
    expected_ydata = np.gradient(expected_ydata, expected_xdata)
    # Configure signals
    display.ui.multi_signal_x_combobox.addItem("energy_energy")
    display.ui.multi_signal_x_combobox.setCurrentText("energy_energy")
    display.multi_y_signals = ["energy_energy"]
    display.db.selected_runs = [run]
    # Update the plots
    await display.update_multi_plot()
    # Check that the data were added
    # data_item = display._multiplot_items[0].listDataItems()[0]
    # xdata, ydata = data_item.getData()
    # np.testing.assert_almost_equal(xdata, expected_xdata)
    # np.testing.assert_almost_equal(ydata, expected_ydata)


@pytest.mark.asyncio
async def test_filter_runs(catalog):
    worker = DatabaseWorker(catalog=catalog)
    runs = await worker.load_all_runs(filters={"plan": "xafs_scan"})
    # Check that the runs were filtered
    assert len(runs) == 1


@pytest.mark.asyncio
async def test_distinct_fields(catalog, display):
    worker = DatabaseWorker(catalog=catalog)
    distinct_fields = await worker.load_distinct_fields()
    # Check that the dictionary has the right structure
    for key in ["sample_name"]:
        assert key in distinct_fields.keys()


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


@pytest.mark.asyncio
async def test_update_combobox_items(display):
    """Check that the comboboxes get the distinct filter fields."""
    assert display.ui.filter_plan_combobox.count() > 0


@pytest.mark.asyncio
async def test_export_button_enabled(catalog, display):
    assert not display.export_button.isEnabled()
    # Update the list with 1 run and see if the control gets enabled
    display.selected_runs = [run async for run in catalog.values()]
    display.selected_runs = display.selected_runs[:1]
    display.update_export_button()
    assert display.export_button.isEnabled()
    # Update the list with multiple runs and see if the control gets disabled
    display.selected_runs = [run async for run in catalog.values()]
    display.update_export_button()
    assert not display.export_button.isEnabled()


@pytest.mark.asyncio
async def test_export_button_clicked(catalog, display, mocker, qtbot):
    # Set up a run to be tested against
    run = MagicMock()
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
