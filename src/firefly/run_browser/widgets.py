import logging
from itertools import count
from typing import Mapping, Optional, Sequence

import numpy as np
from matplotlib.colors import TABLEAU_COLORS
from pandas.api.types import is_numeric_dtype
from pyqtgraph import GraphicsLayoutWidget, ImageView, PlotItem, PlotWidget
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QFileDialog, QWidget

log = logging.getLogger(__name__)
colors = list(TABLEAU_COLORS.values())


class FiltersWidget(QWidget):
    returnPressed = Signal()

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        # Check for return keys pressed
        if event.key() in [Qt.Key_Enter, Qt.Key_Return]:
            self.returnPressed.emit()


class ExportDialog(QFileDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFileMode(QFileDialog.FileMode.AnyFile)
        self.setAcceptMode(QFileDialog.AcceptSave)

    def ask(self, mimetypes: Optional[Sequence[str]] = None):
        """Get the name of the file to save for exporting."""
        self.setMimeTypeFilters(mimetypes)
        # Show the file dialog
        if self.exec_() == QFileDialog.Accepted:
            return self.selectedFiles()
        else:
            return None


class Browser1DPlotItem(PlotItem):
    hover_coords_changed = Signal(str)

    def hoverEvent(self, event):
        super().hoverEvent(event)
        if event.isExit():
            self.hover_coords_changed.emit("NaN")
            return
        # Get data coordinates from event
        pos = event.scenePos()
        data_pos = self.vb.mapSceneToView(pos)
        pos_str = f"({data_pos.x():.3f}, {data_pos.y():.3f})"
        self.hover_coords_changed.emit(pos_str)


class Browser1DPlotWidget(PlotWidget):
    auto_range_needed: bool
    data_items: dict

    def __init__(self, parent=None, background="default", plotItem=None, **kargs):
        plot_item = Browser1DPlotItem(**kargs)
        super().__init__(parent=parent, background=background, plotItem=plot_item)
        self.clear_runs()

    def clear_runs(self):
        self.getPlotItem().clear()
        self.cursor_line = None
        self.auto_range_needed = True
        self.data_items = {}

    def plot_runs(self, runs: Mapping, ylabel="", xlabel=""):
        """Take loaded run data and plot it.

        Parameters
        ==========
        runs
          Dictionary with pandas series for each curve. The keys
          should be the curve labels, the series' indexes are the x
          values and the series' values are the y data.

        """
        plot_item = self.getPlotItem()
        # Plot this run's data
        for idx, (label, series) in enumerate(runs.items()):
            color = colors[idx % len(colors)]
            if label in self.data_items.keys():
                # We've plotted this item before, so reuse it
                data_item = self.data_items[label]
                data_item.setData(series.index, series.values)
            else:
                self.data_items[label] = plot_item.plot(
                    x=series.index,
                    y=series.values,
                    pen=color,
                    name=label,
                    clear=False,
                )
            # Cursor to drag around on the data
            if self.cursor_line is None:
                self.cursor_line = plot_item.addLine(
                    x=np.median(series.index), movable=True, label="{value:.3f}"
                )
        # Axis formatting
        plot_item.setLabels(left=ylabel, bottom=xlabel)


class Browser2DPlotWidget(ImageView):
    """A plot widget for 2D maps."""

    def __init__(self, *args, view=None, **kwargs):
        if view is None:
            view = PlotItem()
        super().__init__(*args, view=view, **kwargs)

    def plot_runs(
        self, runs: Mapping, xlabel: str = "", ylabel: str = "", extents=None
    ):
        """Take loaded 2D or 3D mapping data and plot it.

        Parameters
        ==========
        runs
          Dictionary with pandas series for each curve. The keys
          should be the curve labels, the series' indexes are the x
          values and the series' values are the y data.
        xlabel
          The label for the horizontal axis.
        ylabel
          The label for the vertical axis.
        extents
          Spatial extents for the map as ((-y, +y), (-x, +x)).

        """
        images = np.asarray(list(runs.values()))
        # Combine the different runs into one image
        # To-do: make this respond to the combobox selection
        image = np.mean(images, axis=0)
        # To-do: Apply transformations

        # # Plot the image
        if 2 <= image.ndim <= 3:
            self.setImage(image.T, autoRange=False)
        else:
            log.info(f"Could not plot image of dataset with shape {image.shape}.")
            return
        # Determine the axes labels
        self.view.setLabel(axis="bottom", text=xlabel)
        self.view.setLabel(axis="left", text=ylabel)
        # Set axes extent
        yextent, xextent = extents
        x = xextent[0]
        y = yextent[0]
        w = xextent[1] - xextent[0]
        h = yextent[1] - yextent[0]
        self.getImageItem().setRect(x, y, w, h)
