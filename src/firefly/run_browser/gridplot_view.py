import logging
from itertools import count
from pathlib import Path
from typing import Mapping, Sequence

from scipy.interpolate import griddata
import numpy as np
import pandas as pd
import yaml
from matplotlib.colors import TABLEAU_COLORS
from pandas.api.types import is_numeric_dtype
from pyqtgraph import GraphicsLayoutWidget, ImageView, PlotItem, PlotWidget
import pyqtgraph
import qtawesome as qta
from qtpy import QtCore, QtWidgets, uic
from qtpy.QtCore import Qt, Signal, Slot
from qtpy.QtWidgets import QFileDialog, QWidget

log = logging.getLogger(__name__)
colors = list(TABLEAU_COLORS.values())


pyqtgraph.setConfigOption("imageAxisOrder", "row-major")


class GridImageView(ImageView):
    def __init__(self, *args, view=None, **kwargs):
        if view is None:
            view = PlotItem()
        super().__init__(*args, view=view, **kwargs)


class GridplotView(QtWidgets.QWidget):
    """Handles the plotting of tabular data that was taken on a grid."""
    ui_file = Path(__file__).parent / "gridplot_view.ui"
    shape = ()
    extent = ()

    def __init__(self, parent=None):
        self.data_keys = {}
        self.independent_hints = []
        self.dependent_hints = []
        self.dataframes = {}
        self.metadata = {}
        super().__init__(parent)
        self.ui = uic.loadUi(self.ui_file, self)
        # Prepare plotting style
        vbox = self.ui.plot_widget.ui.roiPlot.getPlotItem().getViewBox()
        vbox.setBackgroundColor('k')
        # Connect internal signals/slots
        self.ui.use_hints_checkbox.stateChanged.connect(self.update_signal_widgets)
        self.ui.regrid_checkbox.stateChanged.connect(self.update_signal_widgets)
        self.ui.regrid_xsignal_combobox.currentTextChanged.connect(self.plot)
        self.ui.regrid_ysignal_combobox.currentTextChanged.connect(self.plot)
        self.ui.value_signal_combobox.currentTextChanged.connect(self.plot)
        self.ui.r_signal_combobox.currentTextChanged.connect(self.plot)
        self.ui.r_signal_checkbox.stateChanged.connect(self.plot)
        self.ui.logarithm_checkbox.stateChanged.connect(self.plot)
        self.ui.invert_checkbox.stateChanged.connect(self.plot)
        self.ui.gradient_checkbox.stateChanged.connect(self.plot)

    def set_image_dimensions(self, metadata: Sequence):
        if len(metadata) != 1:
            log.warning(f"Cannot plot grids for {len(metadata)}-D scan.")
            self.shape = ()
            self.extent = ()
            return
        md = list(metadata.values())[0]
        try:
            self.shape = md['start']['shape']
            self.extent = md['start']['extents']
        except KeyError as exc:
            self.shape = ()
            self.extent = ()
            log.exception(exc)

    @Slot(dict, set, set)
    @Slot()
    def update_signal_widgets(
        self,
        data_keys: Mapping | None = None,
        independent_hints: Sequence | None = None,
        dependent_hints: Sequence | None = None,
    ):
        """Update the UI based on new data keys and hints.

        If any of *data_keys*, *independent_hints* or
        *dependent_hints* are used, then the last seen values will be
        used.

        """
        # Stash inputs for if we need to update later
        if data_keys is not None:
            self.data_keys = {
                key: props
                for key, props in data_keys.items()
                if "external" not in props
            }
        valid_hints = set(self.data_keys.keys())
        if independent_hints is not None:
            self.independent_hints = set(independent_hints) & valid_hints
        if dependent_hints is not None:
            self.dependent_hints = set(dependent_hints) & valid_hints
        # Decide whether we want to use hints
        use_hints = self.ui.use_hints_checkbox.isChecked()
        if use_hints:
            new_xcols = self.independent_hints
            new_ycols = self.dependent_hints
        else:
            new_xcols = list(self.data_keys.keys())
            new_ycols = list(self.data_keys.keys())
        # Update the UI
        comboboxes = [
            self.ui.regrid_xsignal_combobox,
            self.ui.regrid_ysignal_combobox,
            self.ui.value_signal_combobox,
            self.ui.r_signal_combobox,
        ]
        for combobox, new_cols in zip(comboboxes, [new_xcols, new_xcols, new_ycols, new_ycols]):
            old_cols = [combobox.itemText(idx) for idx in range(combobox.count())]
            if old_cols != new_cols:
                old_value = combobox.currentText()
                combobox.clear()
                combobox.addItems(new_cols)
                if old_value in new_cols:
                    combobox.setCurrentText(old_value)

    def prepare_plotting_data(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        """Prepare independent and dependent datasets from this
        dataframe and UI state.

        Based on the state of various UI widgets, the image data may
        be reference-corrected or inverted and be converted to its
        natural-log or gradeient. Additionally, the images may be
        re-gridded: interpolated to match the readback values of a
        independent, scanned axis (e.g. motor position).

        Parameters
        ==========
        df
          The dataframe from which to pull data.

        Returns
        =======
        img
          The 2D or 3D image data to plot in (slice, row, col) order.

        """
        xsignal = self.ui.regrid_xsignal_combobox.currentText()
        ysignal = self.ui.regrid_ysignal_combobox.currentText()
        vsignal = self.ui.value_signal_combobox.currentText()
        rsignal = self.ui.r_signal_combobox.currentText()
        # Get data from dataframe
        values = df[vsignal]
        # Make the grid linear based on measured motor positions
        if self.ui.regrid_checkbox.checkState():
            xdata = df[xsignal]
            ydata = df[ysignal]
            values = self.regrid(points=np.c_[ydata, xdata], values=values)
        # Apply scaler filters
        if self.ui.r_signal_checkbox.checkState():
            values = values / df[rsignal]
        if self.ui.invert_checkbox.checkState():
            values = 1 / values
        if self.ui.logarithm_checkbox.checkState():
            values = np.log(values)
        # Reshape to an image
        img = np.reshape(values, self.shape)
        # Apply gradient filter
        if self.ui.gradient_checkbox.checkState():
            img = np.gradient(img)
            img = np.linalg.norm(img, axis=0)
        return img

    def regrid(self, points: np.ndarray, values: np.ndarray):
        """Calculate a new image with a shape based on metadata.

        """
        # Prepare new regular grid to interpolate to
        (ymin, ymax), (xmin, xmax) = self.extent
        ystep, xstep = (npts * 1j for npts in self.shape)
        yy, xx = np.mgrid[ymin:ymax:ystep,xmin:xmax:xstep]
        xi = np.c_[yy.flatten(), xx.flatten()]
        # Interpolate
        new_values = griddata(points, values, xi, method="cubic")
        return new_values

    @Slot()
    @Slot(dict)
    def plot(self, dataframes: Mapping | None = None):
        """Take loaded run data and plot it.

        Parameters
        ==========
        dataframes
          Dictionary with pandas series for each run with run UIDs for
          keys.

        """
        self.clear_plot()
        if dataframes is not None:
            self.dataframes = dataframes
        # Prepare data to plot
        if len(self.dataframes) != 1:
            log.info(f"Cannot plot {len(self.dataframes)} maps.")
            return
        df = list(self.dataframes.values())[0]
        try:
            img = self.prepare_plotting_data(df)
        except KeyError as exc:
            log.warning(f"Could not plot map of signal {exc}.")
            return
        # Plot this run's data
        img = np.reshape(img, self.shape)
        self.ui.plot_widget.setImage(img, autoRange=False)
        # Set axis labels
        img_item = self.ui.plot_widget.getImageItem()
        try:
            ylabel, xlabel = self.independent_hints
        except ValueError:
            log.warning(f"Could not determine grid labels from hints: {self.independent_hints}")
        else:
            view = self.ui.plot_widget.view
            view.setLabels(left=ylabel, bottom=xlabel)
        # Set axes extent
        (ymin, ymax), (xmin, xmax) = self.extent
        x = xmin
        y = ymin
        w = xmax - xmin
        h = ymax - ymin
        img_item.setRect(x, y, w, h)

    def clear_plot(self):
        self.ui.plot_widget.getImageItem().clear()
        self.data_items = {}


# class Browser2DPlotWidget(ImageView):
#     """A plot widget for 2D maps."""

#     def __init__(self, *args, view=None, **kwargs):
#         if view is None:
#             view = PlotItem()
#         super().__init__(*args, view=view, **kwargs)

#     def plot_runs(
#         self, runs: Mapping, xlabel: str = "", ylabel: str = "", extents=None
#     ):
#         """Take loaded 2D or 3D mapping data and plot it.

#         Parameters
#         ==========
#         runs
#           Dictionary with pandas series for each curve. The keys
#           should be the curve labels, the series' indexes are the x
#           values and the series' values are the y data.
#         xlabel
#           The label for the horizontal axis.
#         ylabel
#           The label for the vertical axis.
#         extents
#           Spatial extents for the map as ((-y, +y), (-x, +x)).

#         """
#         images = np.asarray(list(runs.values()))
#         # Combine the different runs into one image
#         # To-do: make this respond to the combobox selection
#         image = np.mean(images, axis=0)
#         # To-do: Apply transformations

#         # # Plot the image
#         if 2 <= image.ndim <= 3:
#             self.setImage(image.T, autoRange=False)
#         else:
#             log.info(f"Could not plot image of dataset with shape {image.shape}.")
#             return
#         # Determine the axes labels
#         self.view.setLabel(axis="bottom", text=xlabel)
#         self.view.setLabel(axis="left", text=ylabel)
#         # Set axes extent
#         yextent, xextent = extents
#         x = xextent[0]
#         y = yextent[0]
#         w = xextent[1] - xextent[0]
#         h = yextent[1] - yextent[0]
#         self.getImageItem().setRect(x, y, w, h)
