import logging
import datetime as dt
from typing import Sequence
import yaml
from httpx import HTTPStatusError
from contextlib import contextmanager

import numpy as np
from qtpy.QtGui import QStandardItemModel, QStandardItem
from qtpy.QtCore import Signal, Slot, QThread
from pyqtgraph import PlotItem

from firefly import display, FireflyApplication
from firefly.run_client import DatabaseWorker
from haven import tiled_client, load_config, exceptions

log = logging.getLogger(__name__)


class RunBrowserDisplay(display.FireflyDisplay):
    runs_model: QStandardItemModel
    _run_col_names: Sequence = ["UID", "Plan", "Sample", "Datetime", "Proposal", "ESAF", "Edge"]

    # Signals
    runs_selected = Signal(list)
    runs_model_changed = Signal(QStandardItemModel)
    plot_1d_changed = Signal(object)

    def __init__(self, root_node=None, args=None, macros=None, **kwargs):
        # self.prepare_run_client(root_node=root_node)
        super().__init__(args=args, macros=macros, **kwargs)
        self.start_run_client(root_node=root_node)

    def start_run_client(self, root_node):
        """Set up the database client in a separate thread."""
        # Create the thread and worker
        thread = QThread(parent=self)
        self._thread = thread
        worker = DatabaseWorker(root_node=root_node)
        self._db_worker = worker
        worker.moveToThread(thread)
        # Connect signals/slots
        thread.started.connect(worker.load_all_runs)
        worker.all_runs_changed.connect(self.set_runs_model_items)
        worker.selected_runs_changed.connect(self.update_metadata)
        worker.selected_runs_changed.connect(self.update_1d_signals)
        worker.selected_runs_changed.connect(self.update_1d_plot)
        self.runs_selected.connect(worker.load_selected_runs)
        # Start the thread
        thread.start()

    def customize_ui(self):
        self.load_models()
        # Setup controls for select which run to show
        self.ui.run_tableview.selectionModel().selectionChanged.connect(
            self.update_selected_runs
        )
        self.ui.signal_y_combobox.currentTextChanged.connect(self.update_1d_plot)
        self.ui.signal_x_combobox.currentTextChanged.connect(self.update_1d_plot)
        self.ui.signal_r_combobox.currentTextChanged.connect(self.update_1d_plot)
        self.ui.signal_r_checkbox.stateChanged.connect(self.update_1d_plot)
        self.ui.logarithm_checkbox.stateChanged.connect(self.update_1d_plot)
        self.ui.invert_checkbox.stateChanged.connect(self.update_1d_plot)
        self.ui.gradient_checkbox.stateChanged.connect(self.update_1d_plot)
        self.ui.plot_1d_hints_checkbox.stateChanged.connect(self.update_1d_signals)
        # Set up 1D plotting widgets
        self.plot_1d_item = self.ui.plot_1d_view.getPlotItem()
        self.plot_1d_item.addLegend()

    def get_signals(self, run, hinted_only=False):
        if hinted_only:
            xsignals = run.metadata['start']['hints']['dimensions'][0][0]
            ysignals = []
            hints = run['primary'].metadata['descriptors'][0]['hints']
            for device, dev_hints in hints.items():
                ysignals.extend(dev_hints['fields'])
        else:
            xsignals = ysignals = run['primary']['data'].keys()
        return xsignals, ysignals

    def set_runs_model_items(self, runs):
        self.runs_model.clear()
        self.runs_model.setHorizontalHeaderLabels(self._run_col_names)
        for run in runs:
            items = [QStandardItem(val) for val in run.values()]
            self.ui.runs_model.appendRow(items)
        self.runs_model_changed.emit(self.ui.runs_model)
    
    def update_1d_signals(self, *args):
        # Store old values for restoring later
        comboboxes = [self.ui.signal_x_combobox, self.ui.signal_y_combobox, self.ui.signal_r_combobox]
        old_values = [cb.currentText() for cb in comboboxes]
        # Determine valid list of columns to choose from
        xcols = set()
        ycols = set()
        runs = self._db_worker.selected_runs
        use_hints = self.ui.plot_1d_hints_checkbox.isChecked()
        for run in runs:
            try:
                _xcols, _ycols = self.get_signals(run, hinted_only=use_hints)
            except KeyError:
                continue
            else:
                xcols.update(_xcols)
                ycols.update(_ycols)
        # Update the UI with the list of controls
        cb = self.ui.signal_x_combobox
        cb.clear()
        cb.addItems(sorted(list(xcols)))
        for cb in [self.ui.signal_y_combobox,
                   self.ui.signal_r_combobox,]:
            cb.clear()
            cb.addItems(sorted(list(ycols)))
        # Restore previous values
        for val, cb in zip(old_values, comboboxes):
            cb.setCurrentText(val)

    def update_small_multiples(self, *args):
        ...

    def calculate_ydata(self, x_data, y_data, r_data, x_signal, y_signal, r_signal,
                        use_reference=False, use_log=False, use_invert=False,
                        use_grad=False):
        """Take raw y and reference data and calculate a new y_data signal."""
        # Apply transformations
        y = y_data
        y_string = f"[{y_signal}]"
        try:
            if use_reference:
                y = y / r_data
                y_string = f"{y_string}/[{r_signal}]"
            if use_log:
                y = np.log(y)
                y_string = f"ln({y_string})"
            if use_invert:
                y *= -1
                y_string = f"-{y_string}"
            if use_grad:
                y = np.gradient(y, x_data)
                y_string = f"d({y_string})/d[{r_signal}]"
        except TypeError:
            msg = f"Could not calculate transformation."
            log.warning(msg)
            raise exceptions.InvalidTransformation(msg)
        return y, y_string


    def load_run_data(self, run, x_signal, y_signal, r_signal, use_reference=True):
        try:
            data = run['primary']['data'].read()
            y_data = data[y_signal]
            x_data = data[x_signal]
            if use_reference:
                r_data = data[r_signal]
            else:
                r_data = 1
        except KeyError as e:
            # No data, so nothing to plot
            msg = f"Cannot find key {e} in {run}."
            log.warning(msg)
            raise exceptions.SignalNotFound(msg)
        return x_data, y_data, r_data


    def update_1d_plot(self, *args):
        print("Clearing")
        self.plot_1d_item.clear()
        # Figure out which signals to plot
        y_signal = self.ui.signal_y_combobox.currentText()
        x_signal = self.ui.signal_x_combobox.currentText()
        use_reference = self.ui.signal_r_checkbox.isChecked()
        if use_reference:
            r_signal = self.ui.signal_r_combobox.currentText()
        else:
            r_signal = None
        use_log = self.ui.logarithm_checkbox.isChecked()
        use_invert = self.ui.invert_checkbox.isChecked()
        use_grad = self.ui.gradient_checkbox.isChecked()
        # Do the plotting for each run
        y_string = ""
        for idx, run in enumerate(self._db_worker.selected_runs):
            print(run, y_signal)
            # Load datasets from the database
            try:
                x_data, y_data, r_data = self.load_run_data(run, x_signal,
                                                            y_signal,
                                                            r_signal,
                                                            use_reference=use_reference)
            except exceptions.SignalNotFound as e:
                self.ui.plot_1d_message_label.setText(str(e))
                continue
            # Screen out non-numeric data types
            try:
                np.isfinite(x_data)
                np.isfinite(y_data)
                np.isfinite(r_data)
            except TypeError as e:
                msg = str(e)
                log.warning(msg)
                self.ui.plot_1d_message_label.setText(msg)
                continue
            # Calculate plotting data
            try:
                y_data, y_string = self.calculate_ydata( x_data, y_data, r_data,
                                                         x_signal, y_signal, r_signal,
                                                         use_reference=use_reference, use_log=use_log,
                                                         use_invert=use_invert, use_grad=use_grad)
            except exceptions.InvalidTransformation as e:
                self.ui.plot_1d_message_label.setText(str(e))
                continue
            # Plot this run's data
            self.plot_1d_item.plot(x=x_data, y=y_data, pen=idx, name=run.metadata['start']['uid'], clear=False)
        # Axis formatting
        self.plot_1d_item.setLabels(left=y_string, bottom=x_signal)
        self.plot_1d_changed.emit(self.plot_1d_item)
        
    def update_metadata(self, *args):
        """Render metadata for the runs into the metadata widget."""
        # Combine the metadata in a human-readable output
        text = ""
        runs = self._db_worker.selected_runs
        for run in runs:
            md_dict = dict(**run.metadata)
            text += yaml.dump(md_dict)
            text += f"\n\n{'=' * 20}\n\n"
        # Update the widget with the rendered metadata
        self.ui.metadata_textedit.document().setPlainText(text)

    def update_selected_runs(self, *args):
        """Get the current runs from the database and stash them."""
        # Get UID's from the selection
        col_idx = self._run_col_names.index("UID")
        indexes = self.ui.run_tableview.selectedIndexes()
        uids = [i.siblingAtColumn(col_idx).data() for i in indexes]
        self.runs_selected.emit(uids)

    def load_models(self):
        # Set up the model
        self.runs_model = QStandardItemModel()
        # Add the model to the UI element
        self.ui.run_tableview.setModel(self.runs_model)

    def ui_filename(self):
        return "run_browser.ui"
