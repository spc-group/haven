import logging
from pathlib import Path
from typing import Mapping

import numpy as np
import pandas as pd
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

    def prepare_plotting_data(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        xsignal = self.ui.x_signal_combobox.currentText()
        ysignal = self.ui.y_signal_combobox.currentText()
        rsignal = self.ui.r_signal_combobox.currentText()
        # Get data from dataframe
        xdata = df[xsignal].values
        ydata = df[ysignal].values
        rdata = df[rsignal].values
        # Apply corrections
        if self.ui.r_signal_checkbox.checkState():
            ydata = ydata / rdata
        if self.ui.invert_checkbox.checkState():
            ydata = 1 / ydata
        if self.ui.logarithm_checkbox.checkState():
            ydata = np.log(ydata)
        if self.ui.gradient_checkbox.checkState():
            ydata = np.gradient(ydata, xdata)
        return (xdata, ydata)

    def axis_labels(self):
        return "", ""
        xlabel = self.ui.x_signal_combobox.currentText()
        ylabel = self.ui.y_signal_combobox.currentText()
        rlabel = self.ui.r_signal_combobox.currentText()
        use_reference = self.ui.r_signal_checkbox.checkState()
        inverted = self.ui.invert_checkbox.checkState()
        logarithm = self.ui.logarithm_checkbox.checkState()
        gradient = self.ui.gradient_checkbox.checkState()
        if use_reference and inverted:
            ylabel = f"{rlabel}/{ylabel}"
        elif use_reference:
            ylabel = f"{ylabel}/{rlabel}"
        elif inverted:
            ylabel = f"1/{ylabel}"
        if logarithm:
            ylabel = f"ln({ylabel})"
        if gradient:
            ylabel = f"grad({ylabel})"
        return xlabel, ylabel

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
    def plot(self, dataframes: Mapping | None = None):
        """Take loaded run data and plot it.

        Parameters
        ==========
        dataframes
          Dictionary with pandas series for each run with run UIDs for
          keys.

        """
        return
        if dataframes is not None:
            self.clear_plot()
            self.dataframes = dataframes
        plot_item = self.ui.plot_widget.getPlotItem()
        xlabel, ylabel = self.axis_labels()
        # Prepare datasets for plotting
        data = {}
        for uid, df in self.dataframes.items():
            try:
                xdata, ydata = self.prepare_plotting_data(df)
            except KeyError:
                continue
            data[uid] = (xdata, ydata)
        # Combine datasets if requested
        agg_name = self.ui.aggregator_combobox.currentText()
        if agg_name != "All":
            aggregate = self.aggregators[agg_name]
            xs, ys = zip(*data.values())
            data = {agg_name: (aggregate(xs, axis=0), aggregate(ys, axis=0))}
        # Plot each run's data
        for idx, (uid, (xdata, ydata)) in enumerate(data.items()):
            start_doc = self.metadata.get(uid, {}).get("start", {})
            label = self.label_from_metadata(start_doc) or uid
            if uid in self.data_items.keys():
                log.debug(f"Reusing plot item for {label}")
                # We've plotted this item before, so reuse it
                self.data_items[uid].setData(xdata, ydata)
            else:
                color = colors[idx % len(colors)]
                log.debug(f"Adding new plot item for {label}")
                self.data_items[uid] = plot_item.plot(
                    x=xdata,
                    y=ydata,
                    pen=color,
                    name=label,
                    symbol=self.current_symbol,
                    clear=False,
                )
        # Axis formatting
        plot_item.setLabels(left=ylabel, bottom=xlabel)
        if self.ui.autorange_checkbox.checkState():
            self.auto_range()

    def label_from_metadata(self, start_doc: Mapping) -> str:
        # Determine label from metadata
        uid = start_doc.get("uid", "")
        sample_name = start_doc.get("sample_name")
        scan_name = start_doc.get("scan_name")
        sample_formula = start_doc.get("sample_formula")
        if sample_name is not None and sample_formula is not None:
            sample_name = f"{sample_name} ({sample_formula})"
        elif sample_formula is not None:
            sample_name = sample_formula
        md_values = [val for val in [sample_name, scan_name] if val is not None]
        # Use the full UID unless we have something else to show
        if len(md_values) > 0:
            uid = uid.split("-")[0]
        # Build the label
        label = " — ".join([uid, *md_values])
        if start_doc.get("is_standard", False):
            label = f"{label} ★"
        return label

    def auto_range(self):
        self.plot_widget.autoRange(items=self.data_items.values())

    def clear_plot(self):
        self.ui.plot_widget.getPlotItem().clear()
        if self.cursor_line is not None:
            self.ui.plot_widget.removeItem(self.cursor_line)
            self.cursor_line = None
        self.data_items = {}

    def stash_metadata(self, metadata: Mapping):
        self.metadata = metadata
