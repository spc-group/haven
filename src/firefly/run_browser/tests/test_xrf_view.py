import numpy as np
import pytest
from qtpy.QtWidgets import QComboBox

from firefly.run_browser.xrf_view import XRFView


@pytest.fixture()
def view(qtbot):
    xrf_view = XRFView()
    qtbot.addWidget(xrf_view)
    return xrf_view


def test_load_ui(view):
    """Make sure widgets were loaded from the UI file."""
    assert isinstance(view.ui.dataset_combobox, QComboBox)


def test_dataset_combobox_options(view):
    """
    We need to know:
    - external signals
    - internal signals
    - hints

    Then each view can handle sorting out which signals it needs.

    Use '64e85e20-106c-48e6-b643-77e9647b0242' for testing in the
    haven-dev catalog.

    """

    data_keys = {
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
    ihints = ["sim_motor_2"]
    dhints = ["I0-net_current"]
    combobox = view.ui.dataset_combobox
    view.update_signal_widgets(data_keys, ihints, dhints)
    assert (
        combobox.findText("ge_8element") > -1
    ), f"ge_8element signal not in {combobox.objectName()}."
    assert (
        combobox.findText("I0-net_current") == -1
    ), f"I0-net_current signal should not be in {combobox.objectName()}."


def test_update_dimension_widgets(view):
    data = np.mgrid[0:21, 0:8, 0:4096][0]
    view.update_dimension_widgets(data)
    layout = view.ui.dimensions_layout
    assert view.row_count(layout) == 4
    assert layout.itemAtPosition(1, 1).widget().text() == "21"
    assert layout.itemAtPosition(2, 1).widget().text() == "8"
    assert layout.itemAtPosition(3, 1).widget().text() == "4096"


def test_reduce_dimensions_3d(view):
    data = np.mgrid[0:14, 0:21, 0:8, 0:4096][0]
    # Make sure the dimension widgets are set up
    view.update_dimension_widgets(data)
    layout = view.ui.dimensions_layout
    z_pos, y_pos, x_pos = (2, 3, 4)
    layout.itemAtPosition(3, z_pos).widget().setChecked(True)
    layout.itemAtPosition(4, y_pos).widget().setChecked(True)
    layout.itemAtPosition(1, x_pos).widget().setChecked(True)
    # Apply dimensionality reduction
    new_data = view.reduce_dimensions(data)
    # Check results
    assert new_data.ndim == 3
    assert new_data.shape == (8, 4096, 14)


def test_reduce_dimensions_2d(view):
    data = np.mgrid[0:14, 0:21, 0:8, 0:4096][0]
    # Make sure the dimension widgets are set up
    view.update_dimension_widgets(data)
    layout = view.ui.dimensions_layout
    z_pos, y_pos, x_pos = (2, 3, 4)
    layout.itemAtPosition(3, z_pos).widget().setChecked(True)
    layout.itemAtPosition(4, y_pos).widget().setChecked(True)
    layout.itemAtPosition(1, x_pos).widget().setChecked(True)
    view.ui.z_combobox.setCurrentText("Mean")
    view.ui.z_checkbox.setChecked(False)
    # Apply dimensionality reduction
    new_data = view.reduce_dimensions(data)
    # Check results
    assert new_data.ndim == 2
    assert new_data.shape == (4096, 14)
