import numpy as np
import pytest
import xarray as xr
from pyqtgraph import ImageView

from firefly.run_browser.frameset_view import FramesetView


@pytest.fixture()
def view(qtbot):
    fs_view = FramesetView()
    qtbot.addWidget(fs_view)
    return fs_view


def test_load_ui(view):
    """Make sure widgets were loaded from the UI file."""
    assert isinstance(view.ui.frame_view, ImageView)


def test_update_dimension_widgets(view):
    layout = view.ui.dimensions_layout
    view.update_dimension_widgets(shape=(21, 8, 4096))
    assert view.row_count(layout) == 4
    assert layout.itemAtPosition(1, 1).widget().text() == "21"
    assert layout.itemAtPosition(1, 2).widget().isChecked()
    assert layout.itemAtPosition(2, 1).widget().text() == "8"
    assert layout.itemAtPosition(2, 3).widget().isChecked()
    assert layout.itemAtPosition(3, 1).widget().text() == "4096"
    assert layout.itemAtPosition(3, 4).widget().isChecked()
    # New dimensions, does it update the rows?
    view.update_dimension_widgets(shape=(13, 21, 8, 4096))
    assert view.row_count(layout) == 5
    assert layout.itemAtPosition(1, 1).widget().text() == "13"
    assert layout.itemAtPosition(2, 1).widget().text() == "21"
    assert layout.itemAtPosition(3, 1).widget().text() == "8"
    assert layout.itemAtPosition(4, 1).widget().text() == "4096"


def test_radio_row_group(view):
    """Do other radio buttons get disabled when one is checked?"""
    layout = view.ui.dimensions_layout
    view.update_dimension_widgets(shape=(21, 8, 4096))
    z0_button = layout.itemAtPosition(1, 2).widget()
    y0_button = layout.itemAtPosition(1, 3).widget()
    x0_button = layout.itemAtPosition(1, 4).widget()
    z0_button.setChecked(True)
    assert not y0_button.isChecked()
    y0_button.setChecked(True)
    assert not z0_button.isChecked()


def test_radio_column_group(view):
    """Do other radio buttons get disabled when one is checked?"""
    layout = view.ui.dimensions_layout
    view.update_dimension_widgets(shape=(21, 8, 4096))
    z0_button = layout.itemAtPosition(1, 2).widget()
    z1_button = layout.itemAtPosition(2, 2).widget()
    z2_button = layout.itemAtPosition(3, 2).widget()
    z0_button.setChecked(True)
    assert not z1_button.isChecked()
    z1_button.setChecked(True)
    assert not z0_button.isChecked()


def test_disable_aggregate_comboboxes(view):
    """Do other combo boxes get disabled when a dimension is selected?"""
    layout = view.ui.dimensions_layout
    view.update_dimension_widgets(shape=(21, 8, 4096))
    z0_button = layout.itemAtPosition(1, 2).widget()
    combobox = layout.itemAtPosition(1, 5).widget()
    z0_button.setChecked(True)
    assert not combobox.isEnabled()


def test_reduce_dimensions_3d(view):
    data = np.mgrid[0:8, 0:51, 0:70, 0:102][0]
    # Make sure the dimension widgets are set up
    view.update_dimension_widgets(data)
    layout = view.ui.dimensions_layout
    z_pos, y_pos, x_pos = (2, 3, 4)
    layout.itemAtPosition(4, z_pos).widget().setChecked(True)
    layout.itemAtPosition(1, y_pos).widget().setChecked(True)
    layout.itemAtPosition(2, x_pos).widget().setChecked(True)
    # Apply dimensionality reduction
    new_data = view.reduce_dimensions(data)
    # Check results
    assert new_data.ndim == 3
    assert new_data.shape == (102, 8, 51)


def test_reduce_dimensions_2d(view):
    """1 of the dimensions gets reduced so we have a 2D image."""
    data = np.mgrid[0:8, 0:51, 0:70, 0:102][0]
    # Make sure the dimension widgets are set up
    view.update_dimension_widgets(data)
    layout = view.ui.dimensions_layout
    z_pos, y_pos, x_pos = (2, 3, 4)
    layout.itemAtPosition(4, z_pos).widget().setChecked(False)
    layout.itemAtPosition(4, 5).widget().setCurrentText("Mean")
    layout.itemAtPosition(1, y_pos).widget().setChecked(True)
    layout.itemAtPosition(2, x_pos).widget().setChecked(True)
    # Apply dimensionality reduction
    new_data = view.reduce_dimensions(data)
    # Check results
    assert new_data.ndim == 2
    assert new_data.shape == (8, 51)


def test_plot(view):
    ds = xr.DataArray(
        np.random.rand(16, 8, 4),
        coords={"frame": range(16), "row": range(8), "column": range(4)},
    )
    view.plot(ds)
    im_plot = view.ui.frame_view
    assert np.array_equal(im_plot.image, ds.values)


def test_apply_no_roi(view):
    """Do we get the array back if no ROI is set?"""
    arr = np.random.rand(8, 8, 8)
    view.ui.frame_view.ui.roiBtn.setChecked(False)
    new_arr = view.apply_roi(arr)
    assert new_arr is arr


def test_apply_roi(view):
    """Can we read the current ROI from the frameset tab?"""
    arr = np.random.rand(16, 8, 4)
    view.ui.frame_view.ui.roiBtn.setChecked(True)
    new_arr = view.apply_roi(arr)
    assert new_arr is not arr
    assert new_arr.shape[0] == 16
