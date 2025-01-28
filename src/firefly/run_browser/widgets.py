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
