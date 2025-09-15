import numpy as np
import pytest
import xarray as xr
from pyqtgraph import GraphicsLayoutWidget

from firefly.run_browser.multiplot_view import MultiplotView


@pytest.fixture()
def view(qtbot):
    mp_view = MultiplotView()
    qtbot.addWidget(mp_view)
    return mp_view


data_keys = {
    "sim_motor_2": {
        "dtype": "number",
    },
    "ge_8element": {
        "dtype": "array",
        "dtype_numpy": "<u4",
        "external": "STREAM:",
        "object_name": "ge_8element",
        "shape": [8, 4096],
        "source": "ca://XSP_Ge_8elem:HDF1:FullFileName_RBV",
    },
    "I0-net_current": {
        "dtype": "number",
        "dtype_numpy": "<f8",
        "object_name": "I0",
        "shape": [],
        "source": "ca://25idVME:3820:scaler1.S0",
        "units": "A",
    },
}


def test_load_ui(view):
    """Make sure widgets were loaded from the UI file."""
    assert isinstance(view.ui.plot_widget, GraphicsLayoutWidget)


def test_update_plot(view):
    coords = {"energy_energy": np.linspace(8330, 8500, num=101)}
    dataset = xr.Dataset(
        {
            "I0": xr.DataArray(np.sin(np.linspace(0, 6.28, num=101)), coords=coords),
        },
    )
    # Update the plots
    view.plot([dataset])
    # Check that the data were added
    assert len(view._multiplot_items) == 1
    data_item = view._multiplot_items[(0, 0)].listDataItems()[0]
    xdata, ydata = data_item.getData()
    np.testing.assert_almost_equal(xdata, coords["energy_energy"])
    np.testing.assert_almost_equal(ydata, dataset["I0"].values)
