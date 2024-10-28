import asyncio
import logging
from collections import Counter
from contextlib import contextmanager
from functools import wraps
from typing import Mapping, Optional, Sequence

import qtawesome as qta
import yaml
from qasync import asyncSlot
from qtpy.QtCore import Qt
from qtpy.QtGui import QStandardItem, QStandardItemModel

from firefly import display
from firefly.run_browser.client import DatabaseWorker
from firefly.run_browser.widgets import ExportDialog

log = logging.getLogger(__name__)


def cancellable(fn):
    @wraps(fn)
    async def inner(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except asyncio.exceptions.CancelledError:
            log.warning(f"Cancelled task {fn}")

    return inner


class RunBrowserDisplay(display.FireflyDisplay):
    runs_model: QStandardItemModel
    _run_col_names: Sequence = [
        "Plan",
        "Sample",
        "Edge",
        "E0",
        "Exit Status",
        "Datetime",
        "UID",
        "Proposal",
        "ESAF",
        "ESAF Users",
    ]
    _multiplot_items = {}

    selected_runs: list
    _running_db_tasks: Mapping

    export_dialog: Optional[ExportDialog] = None

    # Counter for keeping track of UI hints for long DB hits
    _busy_hinters: Counter

    def __init__(self, root_node=None, args=None, macros=None, **kwargs):
        super().__init__(args=args, macros=macros, **kwargs)
        self.selected_runs = []
        self._running_db_tasks = {}
        self._busy_hinters = Counter()
        self.db = DatabaseWorker(catalog=root_node)
        # Load the list of all runs for the selection widget
        self.db_task(self.load_runs(), name="init_load_runs")
        # Load the list of filters' field values into the comboboxes
        self.db_task(self.update_combobox_items(), name="update_combobox_items")

    def db_task(self, coro, name="default task"):
        """Executes a co-routine as a database task. Existing database
        tasks get cancelled.

        """
        # Check for existing tasks
        has_previous_task = name in self._running_db_tasks.keys()
        task_is_running = has_previous_task and not self._running_db_tasks[name].done()
        if task_is_running:
            self._running_db_tasks[name].cancel("New database task started.")
        # Wait on this task to be done
        new_task = asyncio.ensure_future(coro)
        self._running_db_tasks[name] = new_task
        return new_task

    @asyncSlot()
    async def reload_runs(self):
        """A simple wrapper to make load_runs a slot."""
        await self.load_runs()

    @cancellable
    async def load_runs(self):
        """Get the list of available runs based on filters."""
        with self.busy_hints(run_widgets=True, run_table=True, filter_widgets=False):
            runs = await self.db_task(
                self.db.load_all_runs(self.filters()),
                name="load all runs",
            )
            # Update the table view data model
            self.runs_model.clear()
            self.runs_model.setHorizontalHeaderLabels(self._run_col_names)
            for run in runs:
                items = [QStandardItem(val) for val in run.values()]
                self.ui.runs_model.appendRow(items)
            # Adjust the layout of the data table
            sort_col = self._run_col_names.index("Datetime")
            self.ui.run_tableview.sortByColumn(sort_col, Qt.DescendingOrder)
            self.ui.run_tableview.resizeColumnsToContents()
            # Let slots know that the model data have changed
            self.runs_total_label.setText(str(self.ui.runs_model.rowCount()))

    def clear_filters(self):
        self.ui.filter_proposal_combobox.setCurrentText("")
        self.ui.filter_esaf_combobox.setCurrentText("")
        self.ui.filter_sample_combobox.setCurrentText("")
        self.ui.filter_exit_status_combobox.setCurrentText("")
        self.ui.filter_current_proposal_checkbox.setChecked(False)
        self.ui.filter_current_esaf_checkbox.setChecked(False)
        self.ui.filter_plan_combobox.setCurrentText("")
        self.ui.filter_full_text_lineedit.setText("")
        self.ui.filter_edge_combobox.setCurrentText("")
        self.ui.filter_user_combobox.setCurrentText("")

    async def update_combobox_items(self):
        """"""
        with self.busy_hints(run_table=False, run_widgets=False, filter_widgets=True):
            fields = await self.db.load_distinct_fields()
            for field_name, cb in [
                ("proposal_users", self.ui.filter_proposal_combobox),
                ("proposal_id", self.ui.filter_user_combobox),
                ("esaf_id", self.ui.filter_esaf_combobox),
                ("sample_name", self.ui.filter_sample_combobox),
                ("plan_name", self.ui.filter_plan_combobox),
                ("edge", self.ui.filter_edge_combobox),
            ]:
                if field_name in fields.keys():
                    old_text = cb.currentText()
                    cb.clear()
                    cb.addItems(fields[field_name])
                    cb.setCurrentText(old_text)

    @asyncSlot()
    @cancellable
    async def sleep_slot(self):
        await self.db_task(self.print_sleep())

    async def print_sleep(self):
        with self.busy_hints(run_widgets=True, run_table=True, filter_widgets=True):
            label = self.ui.sleep_label
            label.setText(f"3...")
            await asyncio.sleep(1)
            old_text = label.text()
            label.setText(f"{old_text}2...")
            await asyncio.sleep(1)
            old_text = label.text()
            label.setText(f"{old_text}1...")
            await asyncio.sleep(1)
            old_text = label.text()
            label.setText(f"{old_text}done!")

    def customize_ui(self):
        self.load_models()
        # Setup controls for select which run to show

        self.ui.run_tableview.selectionModel().selectionChanged.connect(
            self.update_selected_runs
        )
        self.ui.refresh_runs_button.setIcon(qta.icon("fa5s.sync"))
        self.ui.refresh_runs_button.clicked.connect(self.reload_runs)
        # Sleep controls for testing async timing
        self.ui.sleep_button.clicked.connect(self.sleep_slot)
        # Respond to changes in displaying the 1d plot
        for signal in [
            self.ui.signal_y_combobox.currentTextChanged,
            self.ui.signal_x_combobox.currentTextChanged,
            self.ui.signal_r_combobox.currentTextChanged,
            self.ui.signal_r_checkbox.stateChanged,
            self.ui.logarithm_checkbox.stateChanged,
            self.ui.invert_checkbox.stateChanged,
            self.ui.gradient_checkbox.stateChanged,
        ]:
            signal.connect(self.plot_1d_view.clear_runs)
            signal.connect(self.update_1d_plot)
        self.ui.plot_1d_hints_checkbox.stateChanged.connect(self.update_1d_signals)
        self.ui.autorange_1d_button.clicked.connect(self.auto_range)
        # Respond to changes in displaying the 2d plot
        self.ui.plot_multi_hints_checkbox.stateChanged.connect(
            self.update_multi_signals
        )
        self.ui.plot_multi_hints_checkbox.stateChanged.connect(self.update_multi_plot)
        # Respond to changes in displaying the 2d plot
        self.ui.signal_value_combobox.currentTextChanged.connect(self.update_2d_plot)
        self.ui.logarithm_checkbox_2d.stateChanged.connect(self.update_2d_plot)
        self.ui.invert_checkbox_2d.stateChanged.connect(self.update_2d_plot)
        self.ui.gradient_checkbox_2d.stateChanged.connect(self.update_2d_plot)
        self.ui.plot_2d_hints_checkbox.stateChanged.connect(self.update_2d_signals)
        # Respond to filter controls getting updated
        self.ui.filters_widget.returnPressed.connect(self.refresh_runs_button.click)
        # Respond to controls for the current run
        self.ui.export_button.clicked.connect(self.export_runs)
        self.ui.reload_plots_button.clicked.connect(self.update_plots)
        # Set up 1D plotting widgets
        self.plot_1d_item = self.ui.plot_1d_view.getPlotItem()
        self.plot_2d_item = self.ui.plot_2d_view.getImageItem()
        self.plot_1d_item.addLegend()
        self.plot_1d_item.hover_coords_changed.connect(
            self.ui.hover_coords_label.setText
        )
        # Create a new export dialog for saving files
        self.export_dialog = ExportDialog(parent=self)

    def auto_range(self):
        self.plot_1d_view.autoRange()

    def update_busy_hints(self):
        """Enable/disable UI elements based on the active hinters."""
        # Widgets for showing plots for runs
        if self._busy_hinters["run_widgets"] > 0:
            self.ui.detail_tabwidget.setEnabled(False)
        else:
            # Re-enable the run widgets
            self.ui.detail_tabwidget.setEnabled(True)
        # Widgets for selecting which runs to show
        if self._busy_hinters["run_table"] > 0:
            self.ui.run_tableview.setEnabled(False)
        else:
            # Re-enable the run widgets
            self.ui.run_tableview.setEnabled(True)
        # Widgets for filtering runs
        if self._busy_hinters["filters_widget"] > 0:
            self.ui.filters_widget.setEnabled(False)
        else:
            self.ui.filters_widget.setEnabled(True)
        # Update status message in message bars
        if len(list(self._busy_hinters.elements())) > 0:
            self.show_message("Loading…")
        else:
            self.show_message("Done.", 5000)

    @contextmanager
    def busy_hints(self, run_widgets=True, run_table=True, filter_widgets=True):
        """A context manager that displays UI hints when slow operations happen.

        Arguments can be used to control which widgets are modified.

        Usage:

        .. code-block:: python

            with self.busy_hints():
                self.db_task(self.slow_operation)

        Parameters
        ==========
        run_widgets
          Disable the widgets for viewing individual runs.
        run_table
          Disable the table for selecting runs to view.
        filter_widgets
          Disable the filter comboboxes, etc.

        """
        # Update the counters for keeping track of concurrent contexts
        hinters = {
            "run_widgets": run_widgets,
            "run_table": run_table,
            "filters_widget": filter_widgets,
        }
        hinters = [name for name, include in hinters.items() if include]
        self._busy_hinters.update(hinters)
        # Update the UI (e.g. disable widgets)
        self.update_busy_hints()
        # Run the innner context code
        try:
            yield
        finally:
            # Re-enable widgets if appropriate
            self._busy_hinters.subtract(hinters)
            self.update_busy_hints()

    @asyncSlot()
    @cancellable
    async def update_multi_signals(self, *args):
        """Retrieve a new list of signals for multi plot and update UI."""
        combobox = self.ui.multi_signal_x_combobox
        # Store old value for restoring later
        old_value = combobox.currentText()
        # Determine valid list of columns to choose from
        use_hints = self.ui.plot_multi_hints_checkbox.isChecked()
        signals_task = self.db_task(
            self.db.signal_names(hinted_only=use_hints), "multi signals"
        )
        xcols, ycols = await signals_task
        # Update the comboboxes with new signals
        combobox.clear()
        combobox.addItems(xcols)
        # Restore previous value
        combobox.setCurrentText(old_value)

    @asyncSlot()
    @cancellable
    async def update_1d_signals(self, *args):
        # Store old values for restoring later
        comboboxes = [
            self.ui.signal_x_combobox,
            self.ui.signal_y_combobox,
            self.ui.signal_r_combobox,
        ]
        old_values = [cb.currentText() for cb in comboboxes]
        # Determine valid list of columns to choose from
        use_hints = self.ui.plot_1d_hints_checkbox.isChecked()
        signals_task = self.db_task(
            self.db.signal_names(hinted_only=use_hints), "1D signals"
        )
        xcols, ycols = await signals_task
        self.multi_y_signals = ycols
        # Update the comboboxes with new signals
        self.ui.signal_x_combobox.clear()
        self.ui.signal_x_combobox.addItems(xcols)
        for cb in [
            self.ui.signal_y_combobox,
            self.ui.signal_r_combobox,
        ]:
            cb.clear()
            cb.addItems(ycols)
        # Restore previous values
        for val, cb in zip(old_values, comboboxes):
            cb.setCurrentText(val)

    @asyncSlot()
    @cancellable
    async def update_2d_signals(self, *args):
        # Store current selection for restoring later
        val_cb = self.ui.signal_value_combobox
        old_value = val_cb.currentText()
        # Determine valid list of dependent signals to choose from
        use_hints = self.ui.plot_2d_hints_checkbox.isChecked()
        xcols, vcols = await self.db_task(
            self.db.signal_names(hinted_only=use_hints), "2D signals"
        )
        # Update the UI with the list of controls
        val_cb.clear()
        val_cb.addItems(vcols)
        # Restore previous selection
        val_cb.setCurrentText(old_value)

    @asyncSlot()
    @cancellable
    async def update_multi_plot(self, *args):
        x_signal = self.ui.multi_signal_x_combobox.currentText()
        if x_signal == "":
            return
        use_hints = self.ui.plot_multi_hints_checkbox.isChecked()
        runs = await self.db_task(
            self.db.all_signals(hinted_only=use_hints), "multi-plot"
        )
        self.ui.plot_multi_view.plot_runs(runs, xsignal=x_signal)

    def update_export_button(self):
        # We can only export one scan at a time from here
        should_enable = self.selected_runs is not None and len(self.selected_runs) == 1
        self.ui.export_button.setEnabled(should_enable)

    @asyncSlot()
    async def export_runs(self):
        """Export the selected runs to user-specified filenames.

        Shows the user a file dialog with accepted types based on the
        accepted tiled export formats.

        """
        dialog = self.export_dialog
        # Determine default mimetypes
        mimetypes = self.selected_runs[0].formats()
        filenames = dialog.ask(mimetypes=mimetypes)
        mimetype = dialog.selectedMimeTypeFilter()
        formats = [mimetype] * len(filenames)
        await self.db_task(self.db.export_runs(filenames, formats=formats), "export")

    @asyncSlot(str)
    @cancellable
    async def update_running_scan(self, uid: str):
        print(f"Updating running scan: {uid=}")
        await self.update_1d_plot(uids=[uid])

    @asyncSlot()
    @cancellable
    async def update_1d_plot(self, *args, uids: Sequence[str] = None):
        """Updates the data used in the plots.

        If *uids* is given, only runs with UIDs listed in *uids* will
        be updated.

        """
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
        # Load data
        task = self.db_task(
            self.db.signals(
                x_signal,
                y_signal,
                r_signal,
                use_log=use_log,
                use_invert=use_invert,
                use_grad=use_grad,
                uids=uids,
            ),
            "1D plot",
        )
        runs = await task
        if len(runs) == 0:
            return
        # Decide on axes labels
        xlabel = x_signal
        if r_signal is not None:
            if use_invert:
                ylabel = f"{r_signal}/{y_signal}"
            else:
                ylabel = f"{y_signal}/{r_signal}"
        else:
            if use_invert:
                ylabel = f"1/{y_signal}"
            else:
                ylabel = y_signal
        if use_log:
            ylabel = f"ln({ylabel})"
        if use_grad:
            ylabel = f"∇ {ylabel}"
        # Do the plotting
        print("RUNNING", self.ui.plot_1d_view.plot_runs)
        self.ui.plot_1d_view.plot_runs(runs, xlabel=xlabel, ylabel=ylabel)
        if self.ui.autorange_1d_checkbox.isChecked():
            self.ui.plot_1d_view.autoRange()

    @asyncSlot()
    @cancellable
    async def update_2d_plot(self):
        """Change the 2D map plot based on desired signals, etc."""
        # Figure out which signals to plot
        value_signal = self.ui.signal_value_combobox.currentText()
        use_log = self.ui.logarithm_checkbox_2d.isChecked()
        use_invert = self.ui.invert_checkbox_2d.isChecked()
        use_grad = self.ui.gradient_checkbox_2d.isChecked()
        images = await self.db_task(self.db.images(value_signal), "2D plot")
        # Get axis labels
        # Eventually this will be replaced with robus choices for plotting multiple images
        metadata = await self.db_task(self.db.metadata(), "2D plot")
        metadata = list(metadata.values())[0]
        dimensions = metadata["start"]["hints"]["dimensions"]
        try:
            xlabel = dimensions[-1][0][0]
            ylabel = dimensions[-2][0][0]
        except IndexError:
            # Not a 2D scan
            return
        # Get spatial extent
        extents = metadata["start"]["extents"]
        self.ui.plot_2d_view.plot_runs(
            images, xlabel=xlabel, ylabel=ylabel, extents=extents
        )

    @asyncSlot()
    async def update_metadata(self, *args):
        """Render metadata for the runs into the metadata widget."""
        # Combine the metadata in a human-readable output
        text = ""
        all_md = await self.db_task(self.db.metadata(), "metadata")
        for uid, md in all_md.items():
            text += f"# {uid}"
            text += yaml.dump(md)
            text += f"\n\n{'=' * 20}\n\n"
        # Update the widget with the rendered metadata
        self.ui.metadata_textedit.document().setPlainText(text)

    def clear_plots(self):
        """Clear all the plots.

        If a *uid* is provided, only the plots matching the scan with
        *uid* will be updated.
        """
        self.plot_1d_view.clear_runs()

    @asyncSlot()
    @cancellable
    async def update_plots(self):
        """Get new data, and update all the plots.

        If a *uid* is provided, only the plots matching the scan with
        *uid* will be updated.
        """

        await asyncio.gather(
            self.update_metadata(),
            self.update_1d_plot(),
            self.update_2d_plot(),
            self.update_multi_plot(),
        )

    @asyncSlot()
    @cancellable
    async def update_selected_runs(self, *args):
        """Get the current runs from the database and stash them."""
        # Get UID's from the selection
        col_idx = self._run_col_names.index("UID")
        indexes = self.ui.run_tableview.selectedIndexes()
        uids = [i.siblingAtColumn(col_idx).data() for i in indexes]
        # Get selected runs from the database
        with self.busy_hints(run_widgets=True, run_table=False, filter_widgets=False):
            task = self.db_task(
                self.db.load_selected_runs(uids=uids), "update selected runs"
            )
            self.selected_runs = await task
            # Update the necessary UI elements
            await asyncio.gather(
                self.update_multi_signals(),
                self.update_1d_signals(),
                self.update_2d_signals(),
            )
            # Update the plots
            self.clear_plots()
            await self.update_plots()
            self.update_export_button()

    def filters(self, *args):
        new_filters = {
            "proposal": self.ui.filter_proposal_combobox.currentText(),
            "esaf": self.ui.filter_esaf_combobox.currentText(),
            "sample": self.ui.filter_sample_combobox.currentText(),
            "exit_status": self.ui.filter_exit_status_combobox.currentText(),
            "use_current_proposal": bool(
                self.ui.filter_current_proposal_checkbox.checkState()
            ),
            "use_current_esaf": bool(self.ui.filter_current_esaf_checkbox.checkState()),
            "plan": self.ui.filter_plan_combobox.currentText(),
            "full_text": self.ui.filter_full_text_lineedit.text(),
            "edge": self.ui.filter_edge_combobox.currentText(),
            "user": self.ui.filter_user_combobox.currentText(),
        }
        null_values = ["", False]
        new_filters = {k: v for k, v in new_filters.items() if v not in null_values}
        return new_filters

    def load_models(self):
        # Set up the model
        self.runs_model = QStandardItemModel()
        # Add the model to the UI element
        self.ui.run_tableview.setModel(self.runs_model)

    def ui_filename(self):
        return "run_browser/run_browser.ui"
