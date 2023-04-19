import time
from unittest.mock import MagicMock
from collections import namedtuple

from qtpy.QtCore import Qt
from pyqtgraph import PlotItem, PlotWidget
import numpy as np

from haven import tiled_client
from firefly.main_window import PlanMainWindow
from firefly.run_browser import RunBrowserDisplay


def test_run_viewer_action(ffapp, qtbot, monkeypatch, sim_tiled):
    monkeypatch.setattr(ffapp, 'create_window', MagicMock())
    assert hasattr(ffapp, "show_run_browser_action")
    ffapp.show_run_browser_action.trigger()
    assert isinstance(ffapp.windows["run_browser"], MagicMock)


def test_load_runs(qtbot, ffapp, sim_tiled):
    display = RunBrowserDisplay(client=sim_tiled["255id_testing"])
    assert display.runs_model.rowCount() > 0


def test_update_selected_runs(qtbot, ffapp, sim_tiled):
    display = RunBrowserDisplay(client=sim_tiled['255id_testing'])
    # Change the proposal item
    selection_model = display.ui.run_tableview.selectionModel()
    item = display.runs_model.item(0, 1)
    assert item is not None
    rect = display.run_tableview.visualRect(item.index())
    with qtbot.waitSignal(display.runs_selected):
        qtbot.mouseClick(
            display.run_tableview.viewport(), Qt.LeftButton, pos=rect.center()
        )
    # Check that the runs were saved
    assert len(display._selected_runs) > 0


def test_metadata(qtbot, ffapp, sim_tiled):
    display = RunBrowserDisplay(client=sim_tiled['255id_testing'])
    # Change the proposal item
    selection_model = display.ui.run_tableview.selectionModel()
    item = display.runs_model.item(0, 1)
    assert item is not None
    rect = display.run_tableview.visualRect(item.index())
    with qtbot.waitSignal(display.runs_selected):
        qtbot.mouseClick(
            display.run_tableview.viewport(), Qt.LeftButton, pos=rect.center()
        )
    # Check that the metadata was set properly in the Metadata tab
    metadata_doc = display.ui.metadata_textedit.document()
    text = display.ui.metadata_textedit.document().toPlainText()
    assert "xafs_scan" in text


def test_1d_plot_signals(qtbot, ffapp, sim_tiled):
    client = sim_tiled["255id_testing"]
    display = RunBrowserDisplay(client=client)
    # Check that the 1D plot was created
    plot_widget = display.ui.plot_1d_view
    plot_item = display.plot_1d_item
    assert isinstance(plot_widget, PlotWidget)
    assert isinstance(plot_item, PlotItem)
    # Update the list of runs and see if the controsl get updated
    display._selected_runs = client.values()
    display.update_1d_signals()
    # Check signals in checkboxes
    for combobox in [display.ui.signal_y_combobox,
                     display.ui.signal_r_combobox,
                     display.ui.signal_x_combobox]:
        assert combobox.findText("energy_energy") > -1, f"energy_energy signal not in {combobox.objectName()}."


def test_1d_plot_signal_memory(qtbot, ffapp, sim_tiled):
    """Do we remember the signals that were previously selected."""
    client = sim_tiled["255id_testing"]
    display = RunBrowserDisplay(client=client)
    # Check that the 1D plot was created
    plot_widget = display.ui.plot_1d_view
    plot_item = display.plot_1d_item
    assert isinstance(plot_widget, PlotWidget)
    assert isinstance(plot_item, PlotItem)
    # Update the list of runs and see if the controsl get updated
    display._selected_runs = client.values()
    display.update_1d_signals()
    # Check signals in comboboxes
    cb = display.ui.signal_y_combobox
    assert cb.currentText() == "energy_energy"
    cb.setCurrentIndex(1)
    assert cb.currentText() == "energy_id_energy_readback"
    # # Update the combobox signals and make sure the text didn't change
    display.update_1d_signals()
    assert cb.currentText() == "energy_id_energy_readback"
    

def test_1d_hinted_signals(qtbot, ffapp, sim_tiled):
    client = sim_tiled["255id_testing"]
    display = RunBrowserDisplay(client=client)
    display.ui.plot_1d_hints_checkbox.setChecked(True)
    # Check that the 1D plot was created
    plot_widget = display.ui.plot_1d_view
    plot_item = display.plot_1d_item
    assert isinstance(plot_widget, PlotWidget)
    assert isinstance(plot_item, PlotItem)
    # Update the list of runs and see if the controsl get updated
    display._selected_runs = client.values()
    display.update_1d_signals()
    # Check signals in checkboxes
    combobox = display.ui.signal_x_combobox
    assert combobox.findText("energy_energy") > -1, f"hinted signal not in {combobox.objectName()}."
    assert combobox.findText("It_net_counts") == -1, f"unhinted signal found in {combobox.objectName()}."
        

def test_update_1d_plot(qtbot, ffapp, sim_tiled):
    client = sim_tiled["255id_testing"]
    display = RunBrowserDisplay(client=client)
    run = client.values()[0]
    run_data = run['primary']['data'].read()
    display._selected_runs = [run]
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
    display.update_1d_plot()
    # Check that the data were added
    data_item = display.plot_1d_item.listDataItems()[0]
    xdata, ydata = data_item.getData()
    expected_xdata = run_data.energy_energy
    expected_ydata = np.log(run_data.I0_net_counts / run_data.It_net_counts)
    expected_ydata = np.gradient(expected_ydata, expected_xdata)
    np.testing.assert_almost_equal(xdata, expected_xdata)
    np.testing.assert_almost_equal(ydata, expected_ydata)
