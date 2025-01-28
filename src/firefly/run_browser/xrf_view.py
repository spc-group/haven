from collections import namedtuple
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
from qtpy import QtCore, QtWidgets, uic

axes = namedtuple("axes", ("z", "y", "x"))


class XRFView(QtWidgets.QWidget):
    ui_file = Path(__file__).parent / "xrf_view.ui"
    spectra: np.ndarray | None = None
    aggregators = {
        "Mean": np.mean,
        "Median": np.median,
        "StDev": np.std,
    }

    dataset_changed = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = uic.loadUi(self.ui_file, self)
        self.ui.dataset_combobox.currentTextChanged.connect(self.dataset_changed)
        # Clear rows from the dimension layout
        for row in range(1, self.row_count(self.ui.dimensions_layout)):
            self.remove_dimension_widgets(row)
        # Set up some button groups for the radio buttons
        self.x_group = QtWidgets.QButtonGroup()
        self.y_group = QtWidgets.QButtonGroup()
        self.z_group = QtWidgets.QButtonGroup()
        # Other UI updates
        self.z_combobox.addItems(["None"] + list(self.aggregators.keys()))

    def row_count(self, layout: QtWidgets.QGridLayout) -> int:
        """How many rows in *layout* actually contain widgets."""
        rows = 0
        for i in range(layout.count()):
            row, _, span, _ = layout.getItemPosition(i)
            rows = max(rows, row + span)
        return rows

    def remove_dimension_widgets(self, row_idx: int):
        layout = self.ui.dimensions_layout
        for col in range(layout.columnCount()):
            widget = layout.itemAtPosition(row_idx, col)
            print(row_idx, col, widget.widget())
            layout.removeItem(widget)

    def add_dimension_widgets(self, row_idx: int, shape: int):
        layout = self.ui.dimensions_layout

        dim_label = QtWidgets.QLabel()
        dim_label.setText(str(row_idx - 1))
        layout.addWidget(dim_label, row_idx, 0)
        shape_label = QtWidgets.QLabel()
        shape_label.setText(str(shape))
        layout.addWidget(shape_label, row_idx, 1)
        # Dimension radio buttons
        z_radio = QtWidgets.QRadioButton()
        self.z_group.addButton(z_radio)
        layout.addWidget(z_radio, row_idx, 2)
        y_radio = QtWidgets.QRadioButton()
        self.y_group.addButton(y_radio)
        layout.addWidget(y_radio, row_idx, 3)
        x_radio = QtWidgets.QRadioButton()
        self.x_group.addButton(x_radio)
        layout.addWidget(x_radio, row_idx, 4)
        # Combobox for aggregation
        combobox = QtWidgets.QComboBox()
        layout.addWidget(combobox, row_idx, 5)
        combobox.addItems(self.aggregators.keys())

    def update_signal_widgets(
        self, data_keys: Mapping, independent_hints: Sequence, dependent_hints: Sequence
    ):
        """Update the UI based on new data keys and hints."""
        self.independent_hints = independent_hints
        self.dependent_hints = dependent_hints
        self.data_keys = {
            key: props for key, props in data_keys.items() if props["dtype"] == "array"
        }
        combobox = self.ui.dataset_combobox
        combobox.clear()
        combobox.addItems(self.data_keys.keys())

    def plot_spectra(self, spectra: np.ndarray | None = None):
        """Plot a set of spectra as lines.

        If *spectra* is not given, the last spectra seen are used.

        """
        if spectra is None:
            spectra = self.spectra
        else:
            self.spectra = spectra
        spectra = self.reduce_dimensions(spectra)
        # Plot the spectra
        plot = self.ui.xrf_spectra_view.getPlotItem()
        plot.clear()
        for spectrum in spectra:
            plot.plot(spectrum)

    def update_dimension_widgets(self, spectra: np.ndarray | None = None):
        """Update the widgets for setting dimensions to match the
        *spectra* array.

        """
        row_count = self.row_count(self.ui.dimensions_layout) - 1
        dim_count = spectra.ndim
        for row in range(dim_count, row_count):
            self.remove_dimension_widgets(row + 1)
        for row in range(row_count, dim_count):
            self.add_dimension_widgets(row + 1, shape=spectra.shape[row])

    def reduce_dimensions(self, spectra: np.ndarray) -> np.ndarray:
        """Reduce the input *spectra* to a shape for plotting
        depending on the dimensions widgets.

        """
        layout = self.ui.dimensions_layout
        ndim = spectra.ndim
        # Go in reverse to we can apply aggregators without messing up earlier indices
        for dim in reversed(range(spectra.ndim)):
            row = dim + 1
            is_plotted = any(
                [
                    layout.itemAtPosition(row, col).widget().isChecked()
                    for col in range(2, 5)
                ]
            )
            if not is_plotted:
                agg_name = layout.itemAtPosition(row, 5).widget().currentText()
                aggregator = self.aggregators[agg_name]
                spectra = aggregator(spectra, axis=dim)
        # Order axes according to (z, x, y) widgets
        frm, to = [], []
        src_dim = 0
        for dim in range(ndim):
            row = dim + 1
            btns = [layout.itemAtPosition(row, col).widget() for col in range(2, 5)]
            is_checked = [btn.isChecked() for btn in btns]
            try:
                plot_idx = is_checked.index(True)
            except ValueError:
                continue
            to.append(plot_idx)
            frm.append(src_dim)
            src_dim += 1
        spectra = np.moveaxis(spectra, frm, to)
        # Reduce the z-axis if plotting in 2D
        if not self.ui.z_checkbox.checkState():
            aggregator = self.aggregators[self.ui.z_combobox.currentText()]
            spectra = aggregator(spectra, axis=0)
        return spectra
