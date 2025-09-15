import logging
from pathlib import Path
from typing import Mapping

import numpy as np
import qtawesome as qta
from matplotlib.colors import TABLEAU_COLORS
from pyqtgraph import PlotItem, PlotWidget
from qtpy import QtWidgets, uic
from qtpy.QtCore import Signal, Slot

log = logging.getLogger(__name__)
colors = list(TABLEAU_COLORS.values())


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
    def __init__(self, parent=None, background="default", plotItem=None, **kargs):
        plot_item = Browser1DPlotItem(**kargs)
        super().__init__(parent=parent, background=background, plotItem=plot_item)


class LineplotView(QtWidgets.QWidget):
    cursor_line = None

    ui_file = Path(__file__).parent / "lineplot_view.ui"

    aggregators = {
        "Mean": np.mean,
        "Median": np.median,
        "StDev": np.std,
    }
    symbols = {
        # See pyqtgraph.ScatterPlotItem.setSymbol() for symbols
        "●": "o",
        "■": "s",
        "▼": "t",
        "▲": "t1",
        "▶": "t2",
        "◀": "t3",
        "◆": "d",
        "+": "+",
        "⬟": "p",
        "⬢": "h",
        "★": "star",
        "|": "|",
        "—": "_",
        "×": "x",
        "⬆": "arrow_up",
        "➡": "arrow_right",
        "⬇": "arrow_down",
        "⬅": "arrow_left",
        "⌖": "crosshair",
    }

    def __init__(self, parent=None):
        self.data_keys = {}
        self.independent_hints = []
        self.dependent_hints = []
        self.dataframes = {}
        self.metadata = {}
        super().__init__(parent)
        self.ui = uic.loadUi(self.ui_file, self)
        self.cursor_button.setIcon(qta.icon("fa5s.crosshairs"))
        self.autorange_button.setIcon(qta.icon("mdi.image-filter-center-focus"))
        self.ui.symbol_combobox.addItems(self.symbols.keys())
        # Connect internal signals/slots
        self.ui.autorange_button.clicked.connect(self.auto_range)
        self.ui.cursor_button.clicked.connect(self.center_cursor)
        self.ui.symbol_checkbox.stateChanged.connect(self.change_symbol)
        self.ui.symbol_combobox.currentTextChanged.connect(self.change_symbol)
        # Set up plotting widgets
        plot_item = self.ui.plot_widget.getPlotItem()
        plot_item.addLegend()
        plot_item.hover_coords_changed.connect(self.ui.hover_coords_label.setText)
        self.clear_plot()

    @property
    def current_symbol(self) -> str | None:
        if self.ui.symbol_checkbox.isChecked():
            symbol = self.ui.symbol_combobox.currentText()
            return self.symbols[symbol]
        else:
            return None

    @Slot()
    def change_symbol(self):
        symbol = self.current_symbol
        for item in self.data_items.values():
            item.setSymbol(symbol)

    @Slot()
    def center_cursor(self):
        plot = self.ui.plot_widget
        x_range, y_range = plot.viewRange()
        xval = np.mean(x_range)
        # Cursor to drag around on the data
        if self.cursor_line is None:
            self.cursor_line = plot.addLine(
                x=np.median(xval), movable=True, label="{value:.3f}"
            )
        else:
            self.cursor_line.setValue(xval)

    @Slot()
    @Slot(dict)
    def plot(self, datasets: Mapping | None = None):
        """Take loaded run data and plot it.

        Parameters
        ==========
        datasets
          Map with xarray DataArray for each run with run UIDs for
          keys.

        """
        self.clear_plot()
        plot_item = self.ui.plot_widget.getPlotItem()
        xlabel, ylabel = "", ""
        # Plot each run's data
        for idx, (label, ydata) in enumerate(datasets.items()):
            xdata = list(ydata.coords.values())[0]
            color = colors[idx % len(colors)]
            log.debug(f"Adding new plot item for {label}")
            self.data_items[label] = plot_item.plot(
                x=xdata,
                y=ydata,
                pen=color,
                name=label,
                symbol=self.current_symbol,
                clear=False,
            )
            xlabel, ylabel = xdata.name or xlabel, ydata.name or ylabel
        # Axis formatting
        plot_item.setLabels(left=ylabel, bottom=xlabel)
        if self.ui.autorange_checkbox.checkState():
            self.auto_range()

    def auto_range(self):
        self.plot_widget.autoRange(items=self.data_items.values())

    def clear(self):
        self.clear_plot()

    def clear_plot(self):
        self.ui.plot_widget.getPlotItem().clear()
        if self.cursor_line is not None:
            self.ui.plot_widget.removeItem(self.cursor_line)
            self.cursor_line = None
        self.data_items = {}
