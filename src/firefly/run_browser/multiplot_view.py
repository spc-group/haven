import logging
from itertools import count
from pathlib import Path
from typing import Mapping, Sequence

from pandas.api.types import is_numeric_dtype
from qtpy import QtWidgets, uic
from qtpy.QtCore import Slot

log = logging.getLogger(__name__)


class MultiplotView(QtWidgets.QWidget):
    _multiplot_items: Mapping
    ui_file = Path(__file__).parent / "multiplot_view.ui"

    def __init__(self, parent=None):
        self.data_keys = {}
        self.independent_hints = []
        self.dependent_hints = []
        self._multiplot_items = {}
        self.dataframes = {}
        super().__init__(parent)
        self.ui = uic.loadUi(self.ui_file, self)
        self.ui.use_hints_checkbox.stateChanged.connect(self.update_signal_widgets)
        self.ui.use_hints_checkbox.stateChanged.connect(self.plot_multiples)
        self.ui.x_signal_combobox.currentTextChanged.connect(self.plot_multiples)

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
                if props["dtype"] == "number"
            }
        valid_hints = set(self.data_keys.keys())
        if independent_hints is not None:
            self.independent_hints = set(independent_hints) & valid_hints
        if dependent_hints is not None:
            self.dependent_hints = set(dependent_hints) & valid_hints
        # Decide whether we want to use hints
        use_hints = self.ui.use_hints_checkbox.isChecked()
        if use_hints:
            new_cols = self.independent_hints
        else:
            new_cols = self.data_keys.keys()
        # Update the UI
        combobox = self.ui.x_signal_combobox
        old_cols = [combobox.itemText(idx) for idx in range(combobox.count())]
        if old_cols != new_cols:
            old_value = combobox.currentText()
            combobox.clear()
            combobox.addItems(new_cols)
            if old_value in new_cols:
                combobox.setCurrentText(old_value)

    @Slot(dict)
    @Slot()
    def plot_multiples(self, dataframes: Mapping | None = None) -> None:
        """Take loaded run data and plot small multiples.

        If *dataframes* is None, the last known set of data frames
        will be used.

        Parameters
        ==========
        dataframes
          Dictionary with pandas series for each curve. The keys
          should be the curve labels, the series' indexes are the x
          values and the series' values are the y data.

        """
        # Stash the data in case we want to replot later
        if dataframes is not None:
            self.dataframes = dataframes
        # Decide on which signals to use
        xsignal = self.ui.x_signal_combobox.currentText()
        if xsignal == "":
            return
        ysignals = list(self.data_keys.keys())
        # ysignals = []
        # for df in self.dataframes.values():
        #     ysignals.extend(df.columns)
        # Remove duplicates and x-signal from the list of y signals
        ysignals = sorted(list(dict.fromkeys(ysignals)))
        ysignals = [sig for sig in ysignals if sig != xsignal]
        use_hints = self.ui.use_hints_checkbox.isChecked()
        if use_hints:
            ysignals = [sig for sig in ysignals if sig in self.dependent_hints]
        # Plot the runs
        plot_widget = self.ui.plot_widget
        plot_widget.clear()
        self._multiplot_items = {}
        for label, data in self.dataframes.items():
            # Figure out which signals to plot
            if xsignal in data.columns:
                xdata = data[xsignal].values
            else:
                # Could not find x signal, so use the index instead
                log.warning(
                    f"Cannot plot x='{xsignal}' for {list(data.keys())}. Falling back to index."
                )
                xdata = data.index
            # Plot each y signal on a separate plot
            for ysignal, plot_item in zip(ysignals, self.multiplot_items()):
                plot_item.setTitle(ysignal)
                if ysignal not in data.columns:
                    log.warning(f"No signal {ysignal} in data.")
                    continue
                ydata = data[ysignal].values
                if is_numeric_dtype(ydata):
                    plot_item.plot(xdata, ydata)
                log.debug(f"Plotted {ysignal} vs. {xsignal} for {label}")

    def multiplot_items(self, n_cols: int = 3):
        view = self.ui.plot_widget
        item0 = None
        for idx in count():
            row = int(idx / n_cols)
            col = idx % n_cols
            # Make a new plot item if one doesn't exist
            if (row, col) not in self._multiplot_items:
                self._multiplot_items[(row, col)] = view.addPlot(row=row, col=col)
            new_item = self._multiplot_items[(row, col)]
            # Link the X-axes together
            if item0 is None:
                item0 = new_item
            else:
                new_item.setXLink(item0)
            # Resize the viewing area to fit the contents
            width = view.width()
            plot_width = width / n_cols
            # view.resize(int(width), int(plot_width * row))
            view.setFixedHeight(1200)
            yield new_item
