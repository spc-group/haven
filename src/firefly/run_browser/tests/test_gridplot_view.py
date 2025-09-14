import numpy as np
import pytest
import xarray as xr
from pyqtgraph import ImageView

from firefly.run_browser.gridplot_view import GridplotView


@pytest.fixture()
def view(qtbot):
    grid_view = GridplotView()
    qtbot.addWidget(grid_view)
    return grid_view


# Set up fake data
dataset = xr.DataArray(
    data=np.linspace(101, 200, num=16 * 32).reshape(16, 32),
    coords={
        "slow_motor": np.arange(16),
        "fast_motor": np.arange(32),
    },
    name="It-net_current",
)


def test_load_ui(view):
    """Make sure widgets were loaded from the UI file."""
    assert isinstance(view.ui.plot_widget, ImageView)


def test_regrid_data(view):
    # Prepare some simulated measurement data
    xx, yy = np.mgrid[-3.2:3.2:0.25, -3.2:3.2:0.2]
    xy = np.sqrt(xx**2 + yy**2)
    data = np.cos(xy)
    xmax = np.sqrt(2 * np.pi)
    view.shape = (61, 61)
    view.extent = ((-xmax, xmax), (-xmax, xmax))
    points = np.c_[yy.flatten(), xx.flatten()]
    new_data = view.regrid(points=points, values=data.flatten())
    assert new_data.shape == (61 * 61,)
    # Simulate what the interpolated data should be
    xstep = 2 * xmax / 60
    xx, yy = np.mgrid[-xmax:xmax:xstep, -xmax:xmax:xstep]
    new_xy = np.sqrt(xx**2 + yy**2)
    test_data = np.cos(new_xy).flatten()
    np.testing.assert_almost_equal(new_data, test_data, decimal=2)


def test_update_plot(view):
    view.ui.regrid_checkbox.setCheckState(False)
    # Update the plots
    view.plot(dataset)
    # Check the data were plotted
    plot_item = view.ui.plot_widget.getImageItem()
    assert view.ui.plot_widget.image is not None
