import logging
from pathlib import Path
from typing import Sequence

import numpy as np
import pyqtgraph
import xarray as xr
from matplotlib.colors import TABLEAU_COLORS
from pyqtgraph import ImageView, PlotItem
from qtpy import QtWidgets, uic
from qtpy.QtCore import Slot
from scipy.interpolate import griddata

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
        vbox.setBackgroundColor("k")
        # Connect internal signals/slots

    def set_image_dimensions(self, metadata: Sequence):
        if len(metadata) != 1:
            log.warning(f"Cannot plot grids for {len(metadata)} scans.")
            self.shape = ()
            self.extent = ()
            return
        md = list(metadata.values())[0]
        try:
            self.shape = md["start"]["shape"]
            self.extent = md["start"]["extents"]
        except KeyError as exc:
            self.shape = ()
            self.extent = ()
            log.warning("Could not determine grid structure.")

    def regrid(self, points: np.ndarray, values: np.ndarray):
        """Calculate a new image with a shape based on metadata."""
        # Prepare new regular grid to interpolate to
        (ymin, ymax), (xmin, xmax) = self.extent
        ystep, xstep = (npts * 1j for npts in self.shape)
        yy, xx = np.mgrid[ymin:ymax:ystep, xmin:xmax:xstep]
        xi = np.c_[yy.flatten(), xx.flatten()]
        # Interpolate
        new_values = griddata(points, values, xi, method="cubic")
        return new_values

    @Slot()
    @Slot(dict)
    def plot(self, dataset: xr.DataArray):
        """Take loaded run data and plot it.

        Parameters
        ==========
        dataframe
          The gridded data array to plot. Data should be a 2D array.
        """
        self.clear_plot()
        # Plot this run's data
        if not (2 <= dataset.ndim <= 3):
            log.warning(f"Cannot plot image with {dataset.ndim} dimensions.")
        self.ui.plot_widget.setImage(dataset.values, autoRange=False)
        # Set axis labels
        img_item = self.ui.plot_widget.getImageItem()
        try:
            ylabel, xlabel = self.independent_hints
        except ValueError:
            log.warning(
                f"Could not determine grid labels from hints: {self.independent_hints}"
            )
        else:
            view = self.ui.plot_widget.view
            view.setLabels(left=ylabel, bottom=xlabel)
        # Set axes extent
        ycoords, xcoords = dataset.coords.values()
        xmin, xmax = np.min(xcoords.values), np.max(xcoords.values)
        ymin, ymax = np.min(ycoords.values), np.max(ycoords.values)
        x = xmin
        y = ymin
        w = xmax - xmin
        h = ymax - ymin
        img_item.setRect(x, y, w, h)

    def clear(self):
        """Reset the page to look blank."""
        self.clear_plot()

    def clear_plot(self):
        self.ui.plot_widget.getImageItem().clear()
        self.data_items = {}
