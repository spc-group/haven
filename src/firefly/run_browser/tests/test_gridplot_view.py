import numpy as np
import pandas as pd
import pytest
from pyqtgraph import ImageView

from firefly.run_browser.gridplot_view import GridplotView


@pytest.fixture()
def view(qtbot):
    grid_view = GridplotView()
    qtbot.addWidget(grid_view)
    # Configure widgets
    grid_view.shape = (16, 32)
    grid_view.extent = ((-1000, 1000), (-500, 500))
    grid_view.data_keys = data_keys
    grid_view.ui.use_hints_checkbox.setChecked(False)
    grid_view.ui.regrid_checkbox.setCheckState(True)
    grid_view.ui.regrid_xsignal_combobox.addItem("fast_motor")
    grid_view.ui.regrid_xsignal_combobox.setCurrentText("fast_motor")
    grid_view.ui.regrid_ysignal_combobox.addItem("slow_motor")
    grid_view.ui.regrid_ysignal_combobox.setCurrentText("slow_motor")
    grid_view.ui.value_signal_combobox.addItem("I0-net_current")
    grid_view.ui.value_signal_combobox.addItem("It-net_current")
    grid_view.ui.value_signal_combobox.setCurrentText("It-net_current")
    grid_view.ui.r_signal_combobox.addItem("It-net_current")
    grid_view.ui.r_signal_combobox.addItem("I0-net_current")
    grid_view.ui.r_signal_combobox.setCurrentText("I0-net_current")
    grid_view.ui.r_signal_checkbox.setCheckState(True)
    grid_view.ui.logarithm_checkbox.setCheckState(True)
    grid_view.ui.invert_checkbox.setCheckState(True)
    grid_view.ui.gradient_checkbox.setCheckState(True)
    return grid_view


# Set up fake data
yy, xx = np.mgrid[0:16, 0:32]
dataframe = pd.DataFrame(
    {
        "slow_motor": yy.flatten(),
        "fast_motor": xx.flatten(),
        "I0-net_current": np.linspace(1, 100, num=16 * 32),
        "It-net_current": np.linspace(101, 200, num=16 * 32),
    }
)
dataframes = {"7d1daf1d-60c7-4aa7-a668-d1cd97e5335f": dataframe}


data_keys = {
    "slow_motor": {
        "dtype": "number",
        "dtype_numpy": "<f8",
        "object_name": "slow_motor",
        "shape": [],
        "units": "mm",
    },
    "fast_motor": {
        "dtype": "number",
        "dtype_numpy": "<f8",
        "object_name": "fast_motor",
        "shape": [],
        "units": "mm",
    },
    "ge_8element": {
        "dtype": "array",
        "dtype_numpy": "<u4",
        "external": "STREAM:",
        "object_name": "ge_8element",
        "shape": [8, 4096],
        "source": "ca://XSP_Ge_8elem:HDF1:FullFileName_RBV",
    },
    "ge_8element-element0-deadtime_factor": {
        "source": "ca://XSP_Ge_8elem:HDF1:FullFileName_RBV",
        "shape": [],
        "dtype": "number",
        "dtype_numpy": "<f8",
        "external": "STREAM:",
        "object_name": "ge_8element",
    },
    "I0-net_current": {
        "dtype": "number",
        "dtype_numpy": "<f8",
        "object_name": "I0",
        "shape": [],
        "source": "ca://25idVME:3820:scaler1.S0",
        "units": "A",
    },
    "It-net_current": {
        "dtype": "number",
        "dtype_numpy": "<f8",
        "object_name": "It",
        "shape": [],
        "source": "ca://25idVME:3820:scaler1.S0",
        "units": "A",
    },
}


def test_load_ui(view):
    """Make sure widgets were loaded from the UI file."""
    assert isinstance(view.ui.plot_widget, ImageView)


def test_signal_options(view):
    """
    We need to know:
    - data_keys
    - independent hints (scan axes)
    - dependent hints (device hints)

    Then each view can handle sorting out which signals it needs.

    Use '64e85e20-106c-48e6-b643-77e9647b0242' for testing in the
    haven-dev catalog.

    """
    comboboxes = [
        view.ui.regrid_xsignal_combobox,
        view.ui.regrid_ysignal_combobox,
        view.ui.value_signal_combobox,
        view.ui.r_signal_combobox,
    ]
    view.ui.use_hints_checkbox.setChecked(False)
    view.update_signal_widgets(data_keys, [], [])
    # Make sure we don't include array datasets
    for combobox in comboboxes:
        assert (
            combobox.findText("ge_8element") == -1
        ), f"ge_8element signal should not be in {combobox.objectName()}."
        assert (
            combobox.findText("ge_8element-element0-deadtime_factor") == -1
        ), f"ge_8element-element0-deadtime_factor signal should not be in {combobox.objectName()}."
        assert (
            combobox.findText("I0-net_current") > -1
        ), f"I0-net_current signal should be in {combobox.objectName()}."
        assert (
            combobox.findText("fast_motor") > -1
        ), f"fast_motor signal should be in {combobox.objectName()}."


def test_hinted_signal_options(view):
    """
    We need to know:
    - data_keys
    - independent hints (scan axes)
    - dependent hints (device hints)

    Then each view can handle sorting out which signals it needs.

    Use '64e85e20-106c-48e6-b643-77e9647b0242' for testing in the
    haven-dev catalog.

    """
    comboboxes = [
        view.ui.regrid_xsignal_combobox,
        view.ui.regrid_ysignal_combobox,
        view.ui.value_signal_combobox,
        view.ui.r_signal_combobox,
    ]
    view.ui.use_hints_checkbox.setChecked(True)
    view.update_signal_widgets(
        data_keys, ["fast_motor", "slow_motor"], ["I0-net_current"]
    )
    # Make sure we don't include array datasets
    for combobox in comboboxes:
        assert (
            combobox.findText("ge_8element") == -1
        ), f"ge_8element signal should not be in {combobox.objectName()}."
    # Check hinted X signals
    assert (
        view.ui.regrid_xsignal_combobox.findText("I0-net_current") == -1
    ), f"I0-net_current signal should not be in x-signal combobox."
    assert (
        view.ui.regrid_xsignal_combobox.findText("fast_motor") > -1
    ), f"fast_motor signal should be in x-signal combobox."
    assert (
        view.ui.regrid_ysignal_combobox.findText("fast_motor") > -1
    ), f"fast_motor signal should be in y-signal combobox."
    # Check hinted Y signals
    assert (
        view.ui.value_signal_combobox.findText("I0-net_current") > -1
    ), f"I0-net_current signal should not be in value signal combobox."
    assert (
        view.ui.value_signal_combobox.findText("fast_motor") == -1
    ), f"fast_motor signal should be in value signal combobox."


def test_plotting_data(view):
    # Check prepared data
    view.ui.regrid_checkbox.setCheckState(False)
    img = view.prepare_plotting_data(dataframe)
    It = dataframe["It-net_current"].values.reshape(16, 32)
    I0 = dataframe["I0-net_current"].values.reshape(16, 32)
    x = dataframe["fast_motor"].values.reshape(16, 32)
    y = dataframe["slow_motor"].values.reshape(16, 32)
    assert img.shape == (16, 32)
    ygrad, xgrad = np.gradient(np.log(I0 / It))
    expected_img = np.sqrt(xgrad**2 + ygrad**2)
    np.testing.assert_array_almost_equal(img, expected_img)


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
    view.plot(dataframes)
    # Check the data were plotted
    plot_item = view.ui.plot_widget.getImageItem()
    assert view.ui.plot_widget.image is not None


def test_swap_signals(view, qtbot):
    assert view.ui.value_signal_combobox.currentText() == "It-net_current"
    assert view.ui.r_signal_combobox.currentText() == "I0-net_current"
    view.swap_signals()
    assert view.ui.value_signal_combobox.currentText() == "I0-net_current"
    assert view.ui.r_signal_combobox.currentText() == "It-net_current"
