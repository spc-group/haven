import numpy as np
import pytest
import xarray as xr
from pyqtgraph import PlotWidget

from firefly.run_browser.lineplot_view import LineplotView


@pytest.fixture()
def view(qtbot):
    lp_view = LineplotView()
    qtbot.addWidget(lp_view)
    # Configure widgets
    return lp_view


# Set up fake data
dataset = xr.Dataset(
    {
        "7d1daf1d-60c7-4aa7-a668-d1cd97e5335f": xr.DataArray(
            data=np.linspace(101, 200, num=101),
            coords={"energy_energy": np.linspace(8333, 8533, num=101)},
        )
    }
)


def test_load_ui(view):
    """Make sure widgets were loaded from the UI file."""
    assert isinstance(view.ui.plot_widget, PlotWidget)


def test_symbol_options(view):
    combobox = view.ui.symbol_combobox
    assert combobox.count() == 19


def test_change_symbol(view):
    """For now just make sure it doesn't raise exceptions."""
    view.plot(dataset)
    view.change_symbol()


def test_plot(view):
    # Update the plots
    view.plot(dataset)
    # Check the data were plotted
    plot_item = view.ui.plot_widget.getPlotItem()
    assert len(plot_item.dataItems) == 1
