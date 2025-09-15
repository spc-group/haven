import logging
from collections import namedtuple
from pathlib import Path

import numpy as np
import pandas as pd
import pyqtgraph as pg
import qtawesome as qta
import xarray as xr
from numpy.typing import NDArray
from qtpy import QtCore, QtWidgets, uic

axes = namedtuple("axes", ("z", "y", "x"))

log = logging.getLogger(__name__)


class FramesetImageView(pg.ImageView):
    def __init__(self, *args, view=None, **kwargs):
        if view is None:
            view = pg.PlotItem()
        super().__init__(*args, view=view, **kwargs)
        self.timeLine.setPen((255, 255, 0, 200), width=5)
        self.timeLine.setHoverPen("r", width=5)
        self.setColorMap(pg.colormap.get("viridis"))


class FramesetView(QtWidgets.QWidget):
    ui_file = Path(__file__).parent / "frameset_view.ui"
    spectra: np.ndarray | None = None
    aggregators = {
        "Mean": np.mean,
        "Median": np.median,
        "StDev": np.std,
    }
    datasets: dict[str, np.ndarray] | None = None
    data_frames: dict[str, pd.DataFrame] | None = None

    dataset_selected = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = uic.loadUi(self.ui_file, self)
        # Set up control widgets
        self.ui.lock_aspect_button.toggled.connect(
            self.frame_view.getView().setAspectLocked
        )
        self.ui.lock_aspect_button.toggled.connect(self.toggle_lock_icon)
        self.toggle_lock_icon(True)

    def toggle_lock_icon(self, state: bool):
        """Toggle the lock icon on the lock aspect button."""
        if state:
            icon = qta.icon("fa6s.lock")
        else:
            icon = qta.icon("fa6s.unlock")
        self.ui.lock_aspect_button.setIcon(icon)

    def row_count(self, layout: QtWidgets.QGridLayout) -> int:
        """How many rows in *layout* actually contain widgets."""
        rows = 0
        for i in range(layout.count()):
            row, _, span, _ = layout.getItemPosition(i)
            rows = max(rows, row + span)
        return rows

    @QtCore.Slot()
    def plot(self, array: xr.DataArray):
        """Plot a dataset as a stack of frames."""
        # Start with a clear plot
        self.clear()
        # Determine how to plot the time series values
        tvals = list(array.coords.values())[0]
        # Plot the images
        self.ui.frame_view.setImage(array.values, xvals=tvals.values)

    def apply_roi(self, arr: NDArray) -> NDArray:
        im_view = self.ui.frame_view
        if not im_view.ui.roiBtn.isChecked():
            return arr
        roi = im_view.roi
        new_arr = roi.getArrayRegion(data=arr, img=im_view.imageItem, axes=(1, 2))
        return new_arr

    def clear(self):
        im_plot = self.ui.frame_view
        im_plot.clear()
