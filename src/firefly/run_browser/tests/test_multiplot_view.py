import numpy as np
import pandas as pd
import pytest
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


def test_xsignal_options(view):
    """
    We need to know:
    - data_keys
    - independent hints (scan axes)
    - dependent hints (device hints)

    Then each view can handle sorting out which signals it needs.

    Use '64e85e20-106c-48e6-b643-77e9647b0242' for testing in the
    haven-dev catalog.

    """
    combobox = view.ui.x_signal_combobox
    view.ui.use_hints_checkbox.setChecked(False)
    view.update_signal_widgets(data_keys, [], [])
    # Make sure we don't include array datasets
    assert (
        combobox.findText("ge_8element") == -1
    ), f"ge_8element signal should not be in {combobox.objectName()}."
    assert (
        combobox.findText("I0-net_current") > -1
    ), f"I0-net_current signal should be in {combobox.objectName()}."
    assert (
        combobox.findText("sim_motor_2") > -1
    ), f"sim_motor_2 signal should be in {combobox.objectName()}."


def test_hinted_xsignal_options(view):
    """
    We need to know:
    - data_keys
    - independent hints (scan axes)
    - dependent hints (device hints)

    Then each view can handle sorting out which signals it needs.

    Use '64e85e20-106c-48e6-b643-77e9647b0242' for testing in the
    haven-dev catalog.

    """
    combobox = view.ui.x_signal_combobox
    ihints = ["sim_motor_2"]
    dhints = ["I0-net_current"]
    view.ui.use_hints_checkbox.setChecked(False)
    view.update_signal_widgets(data_keys, ihints, dhints)
    view.ui.use_hints_checkbox.setChecked(True)
    view.update_signal_widgets()
    # Make sure we don't include array datasets
    assert (
        combobox.findText("ge_8element") == -1
    ), f"ge_8element signal should not be in {combobox.objectName()}."
    assert (
        combobox.findText("sim_motor_2") >= -1
    ), f"sim_motor_2 signal should be in {combobox.objectName()}."
    assert (
        combobox.findText("I0-net_current") == -1
    ), f"I0-net_current signal should not be in {combobox.objectName()}."


def test_update_plot(view):
    view.use_hints_checkbox.setChecked(True)
    view.independent_hints = ["energy_energy"]
    view.dependent_hints = ["energy_energy", "I0"]
    view.data_keys = {
        "energy_energy": {},
        "I0": {},
    }
    df = pd.DataFrame(
        {
            "energy_energy": np.linspace(8330, 8500, num=101),
            "I0": np.sin(np.linspace(0, 6.28, num=101)),
        }
    )
    dataframes = {"7d1daf1d-60c7-4aa7-a668-d1cd97e5335f": df}
    # Configure signals
    view.ui.x_signal_combobox.addItem("energy_energy")
    view.ui.x_signal_combobox.setCurrentText("energy_energy")
    view.multi_y_signals = ["energy_energy"]
    # Update the plots
    view.plot_multiples(dataframes)
    # Check that the data were added
    assert len(view._multiplot_items) == 1
    data_item = view._multiplot_items[(0, 0)].listDataItems()[0]
    xdata, ydata = data_item.getData()
    np.testing.assert_almost_equal(xdata, df["energy_energy"])
    np.testing.assert_almost_equal(ydata, df["I0"])
