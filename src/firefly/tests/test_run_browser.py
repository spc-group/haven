import logging
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest
from pyqtgraph import PlotItem, PlotWidget
from qtpy.QtCore import Qt
from tiled.adapters.mapping import MapAdapter
from tiled.adapters.xarray import DatasetAdapter
from tiled.client import Context, from_context
from tiled.server.app import build_app

from firefly.run_browser import RunBrowserDisplay
from firefly.run_client import DatabaseWorker

log = logging.getLogger(__name__)


def wait_for_runs_model(display, qtbot):
    with qtbot.waitSignal(display.runs_model_changed):
        pass


# Some mocked test data
run1 = pd.DataFrame(
    {
        "energy_energy": np.linspace(8300, 8400, num=100),
        "It_net_counts": np.abs(np.sin(np.linspace(0, 4 * np.pi, num=100))),
        "I0_net_counts": np.linspace(1, 2, num=100),
    }
)

hints = {
    "energy": {"fields": ["energy_energy", "energy_id_energy_readback"]},
}

bluesky_mapping = {
    "7d1daf1d-60c7-4aa7-a668-d1cd97e5335f": MapAdapter(
        {
            "primary": MapAdapter(
                {
                    "data": DatasetAdapter.from_dataset(run1.to_xarray()),
                },
                metadata={"descriptors": [{"hints": hints}]},
            ),
        },
        metadata={
            "plan_name": "xafs_scan",
            "start": {
                "plan_name": "xafs_scan",
                "uid": "7d1daf1d-60c7-4aa7-a668-d1cd97e5335f",
                "hints": {"dimensions": [[["energy_energy"], "primary"]]},
            },
        },
    ),
    "9d33bf66-9701-4ee3-90f4-3be730bc226c": MapAdapter(
        {
            "primary": MapAdapter(
                {
                    "data": DatasetAdapter.from_dataset(run1.to_xarray()),
                },
                metadata={"descriptors": [{"hints": hints}]},
            ),
        },
        metadata={
            "start": {
                "plan_name": "rel_scan",
                "uid": "9d33bf66-9701-4ee3-90f4-3be730bc226c",
                "hints": {"dimensions": [[["pitch2"], "primary"]]},
            }
        },
    ),
}


mapping = {
    "255id_testing": MapAdapter(bluesky_mapping),
}

tree = MapAdapter(mapping)


@pytest.fixture(scope="module")
def client():
    app = build_app(tree)
    with Context.from_app(app) as context:
        client = from_context(context)
        yield client["255id_testing"]


@pytest.fixture()
def display(ffapp, client, qtbot):
    display = RunBrowserDisplay(root_node=client)
    wait_for_runs_model(display, qtbot)
    try:
        yield display
    finally:
        display._thread.quit()
        display._thread.wait(msecs=5000)
        assert not display._thread.isRunning()


def test_client_fixture(client):
    """Does the client fixture load without stalling the test runner?"""


def test_run_viewer_action(ffapp, monkeypatch):
    monkeypatch.setattr(ffapp, "create_window", MagicMock())
    assert hasattr(ffapp, "show_run_browser_action")
    ffapp.show_run_browser_action.trigger()
    assert isinstance(ffapp.windows["run_browser"], MagicMock)


def test_load_runs(display):
    assert display.runs_model.rowCount() > 0
    assert display.ui.runs_total_label.text() == str(display.runs_model.rowCount())


def test_update_selected_runs(qtbot, display):
    # Change the proposal item
    selection_model = display.ui.run_tableview.selectionModel()
    item = display.runs_model.item(0, 1)
    assert item is not None
    rect = display.run_tableview.visualRect(item.index())
    with qtbot.waitSignal(display._db_worker.selected_runs_changed):
        qtbot.mouseClick(
            display.run_tableview.viewport(), Qt.LeftButton, pos=rect.center()
        )
    # Check that the runs were saved
    assert len(display._db_worker.selected_runs) > 0


def test_metadata(qtbot, display):
    # Change the proposal item
    selection_model = display.ui.run_tableview.selectionModel()
    item = display.runs_model.item(0, 1)
    assert item is not None
    rect = display.run_tableview.visualRect(item.index())
    with qtbot.waitSignal(display._db_worker.selected_runs_changed):
        qtbot.mouseClick(
            display.run_tableview.viewport(), Qt.LeftButton, pos=rect.center()
        )
    # Check that the metadata was set properly in the Metadata tab
    metadata_doc = display.ui.metadata_textedit.document()
    text = display.ui.metadata_textedit.document().toPlainText()
    assert "xafs_scan" in text


def test_1d_plot_signals(client, display):
    # Check that the 1D plot was created
    plot_widget = display.ui.plot_1d_view
    plot_item = display.plot_1d_item
    assert isinstance(plot_widget, PlotWidget)
    assert isinstance(plot_item, PlotItem)
    # Update the list of runs and see if the controsl get updated
    display._db_worker.selected_runs = client.values()
    display._db_worker.selected_runs_changed.emit([])
    # Check signals in checkboxes
    for combobox in [
        display.ui.multi_signal_x_combobox,
        display.ui.signal_y_combobox,
        display.ui.signal_r_combobox,
        display.ui.signal_x_combobox,
    ]:
        assert (
            combobox.findText("energy_energy") > -1
        ), f"energy_energy signal not in {combobox.objectName()}."


def test_1d_plot_signal_memory(client, display):
    """Do we remember the signals that were previously selected."""
    # Check that the 1D plot was created
    plot_widget = display.ui.plot_1d_view
    plot_item = display.plot_1d_item
    assert isinstance(plot_widget, PlotWidget)
    assert isinstance(plot_item, PlotItem)
    # Update the list of runs and see if the controls get updated
    display._db_worker.selected_runs = client.values()
    display.update_1d_signals()
    # Check signals in comboboxes
    cb = display.ui.signal_y_combobox
    assert cb.currentText() == "energy_energy"
    cb.setCurrentIndex(1)
    assert cb.currentText() == "energy_id_energy_readback"
    # Update the combobox signals and make sure the text didn't change
    display.update_1d_signals()
    assert cb.currentText() == "energy_id_energy_readback"


def test_1d_hinted_signals(client, display):
    display.ui.plot_1d_hints_checkbox.setChecked(True)
    # Check that the 1D plot was created
    plot_widget = display.ui.plot_1d_view
    plot_item = display.plot_1d_item
    assert isinstance(plot_widget, PlotWidget)
    assert isinstance(plot_item, PlotItem)
    # Update the list of runs and see if the controsl get updated
    display._db_worker.selected_runs = client.values()
    display.update_1d_signals()
    # Check signals in checkboxes
    combobox = display.ui.signal_x_combobox
    assert (
        combobox.findText("energy_energy") > -1
    ), f"hinted signal not in {combobox.objectName()}."
    assert (
        combobox.findText("It_net_counts") == -1
    ), f"unhinted signal found in {combobox.objectName()}."


@pytest.mark.skip(reason="Need to figure out why tiled fails with this test.")
def test_update_1d_plot(client, display, qtbot):
    run = client.values()[0]
    run_data = run["primary"]["data"].read()
    expected_xdata = run_data.energy_energy
    expected_ydata = np.log(run_data.I0_net_counts / run_data.It_net_counts)
    expected_ydata = np.gradient(expected_ydata, expected_xdata)
    with qtbot.waitSignal(display.plot_1d_changed):
        display._db_worker.selected_runs_changed.emit([])
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
    display._db_worker.selected_runs = [run]
    display.update_1d_plot()
    # Check that the data were added
    data_item = display.plot_1d_item.listDataItems()[0]
    xdata, ydata = data_item.getData()
    np.testing.assert_almost_equal(xdata, expected_xdata)
    np.testing.assert_almost_equal(ydata, expected_ydata)


def test_update_multi_plot(client, display, qtbot):
    run = client.values()[0]
    run_data = run["primary"]["data"].read()
    expected_xdata = run_data.energy_energy
    expected_ydata = np.log(run_data.I0_net_counts / run_data.It_net_counts)
    expected_ydata = np.gradient(expected_ydata, expected_xdata)
    with qtbot.waitSignal(display.plot_1d_changed):
        display._db_worker.selected_runs_changed.emit([])
    # Configure signals
    display.ui.multi_signal_x_combobox.addItem("energy_energy")
    display.ui.multi_signal_x_combobox.setCurrentText("energy_energy")
    display.multi_y_signals = ["energy_energy"]
    display._db_worker.selected_runs = [run]
    # Update the plots
    display.update_multi_plot()
    # Check that the data were added
    # data_item = display._multiplot_items[0].listDataItems()[0]
    # xdata, ydata = data_item.getData()
    # np.testing.assert_almost_equal(xdata, expected_xdata)
    # np.testing.assert_almost_equal(ydata, expected_ydata)


def test_filter_controls(client, display, qtbot):
    # Does editing text change the filters?
    display.ui.filter_user_combobox.setCurrentText("")
    with qtbot.waitSignal(display.filters_changed):
        qtbot.keyClicks(display.ui.filter_user_combobox, "wolfman")
    # Set some values for the rest of the controls
    display.ui.filter_proposal_combobox.setCurrentText("12345")
    display.ui.filter_esaf_combobox.setCurrentText("678901")
    display.ui.filter_current_proposal_checkbox.setChecked(True)
    display.ui.filter_current_esaf_checkbox.setChecked(True)
    display.ui.filter_plan_combobox.addItem("cake")
    display.ui.filter_plan_combobox.setCurrentText("cake")
    display.ui.filter_full_text_lineedit.setText("Aperature Science")
    display.ui.filter_edge_combobox.setCurrentText("U-K")
    display.ui.filter_sample_combobox.setCurrentText("Pb.*")
    with qtbot.waitSignal(display.filters_changed) as blocker:
        display.update_filters()
    # Check if the filters were update correctly
    filters = blocker.args[0]
    assert filters == {
        "user": "wolfman",
        "proposal": "12345",
        "esaf": "678901",
        "use_current_proposal": True,
        "use_current_esaf": True,
        "exit_status": "success",
        "plan": "cake",
        "full_text": "Aperature Science",
        "edge": "U-K",
        "sample": "Pb.*",
    }


def test_filter_runs(client, qtbot):
    worker = DatabaseWorker(root_node=client)
    worker._filters["plan"] = "xafs_scan"
    with qtbot.waitSignal(worker.all_runs_changed) as blocker:
        worker.load_all_runs()
    # Check that the runs were filtered
    runs = blocker.args[0]
    assert len(runs) == 1


def test_distinct_fields(client, qtbot, display):
    worker = DatabaseWorker(root_node=client)
    with qtbot.waitSignal(worker.distinct_fields_changed) as blocker:
        worker.load_distinct_fields()
    # Check that the dictionary has the right structure
    distinct_fields = blocker.args[0]
    for key in ["sample_name"]:
        assert key in distinct_fields.keys()


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
