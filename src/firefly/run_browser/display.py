import asyncio
import datetime as dt
import logging
from collections import ChainMap, Counter
from contextlib import contextmanager
from functools import wraps
from typing import Mapping, Optional, Sequence

import httpx
import qtawesome as qta
from pydm import PyDMChannel
from qasync import asyncSlot
from qtpy.QtCore import QDateTime, Qt, Signal
from qtpy.QtGui import QStandardItem, QStandardItemModel
from qtpy.QtWidgets import QErrorMessage
from tiled.client import from_profile_async
from tiled.profiles import get_default_profile_name, list_profiles

from firefly import display
from firefly.run_browser.client import DatabaseWorker
from firefly.run_browser.widgets import ExportDialog
from haven import load_config

log = logging.getLogger(__name__)


DEFAULT_PROFILE = get_default_profile_name()


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
        "Scan",
        "Edge",
        "Exit Status",
        "Datetime",
        "UID",
    ]
    _multiplot_items = {}

    selected_runs: list
    _running_db_tasks: Mapping

    proposal_channel: PyDMChannel
    esaf_channel: PyDMChannel
    # (data keys, experiment hints, signal hints)
    data_keys_changed = Signal(ChainMap, set, set)
    data_frames_changed = Signal(dict)
    metadata_changed = Signal(dict)
    datasets_changed = Signal(dict)

    export_dialog: Optional[ExportDialog] = None

    # Counter for keeping track of UI hints for long DB hits
    _busy_hinters: Counter

    def __init__(self, args=None, macros=None, **kwargs):
        super().__init__(args=args, macros=macros, **kwargs)
        self.selected_runs = []
        self._running_db_tasks = {}
        self._busy_hinters = Counter()
        self.reset_default_filters()
        self.db = DatabaseWorker()

    def load_profiles(self):
        """Prepare to use a set of databases accessible through *tiled_client*."""
        profile_names = list_profiles().keys()
        self.ui.profile_combobox.addItems(profile_names)
        self.ui.profile_combobox.setCurrentText(DEFAULT_PROFILE)

    @asyncSlot(str)
    @cancellable
    async def change_catalog(self, profile_name: str = DEFAULT_PROFILE):
        """Activate a different catalog in the Tiled server."""
        self.db.catalog = await from_profile_async(profile_name)
        await self.db_task(
            asyncio.gather(self.load_runs(), self.update_combobox_items()),
            name="change_catalog",
        )

    def update_bss_metadata(self, md: Mapping[str, str]):
        super().update_bss_metadata(md)
        self.update_bss_widgets()

    def update_bss_widgets(self):
        """Set the ESAF/proposal ID's to last known values from the BSS display."""
        md = self._bss_metadata
        if self.filter_current_proposal_checkbox.isChecked() and md.get("proposal_id"):
            self.filter_proposal_combobox.setCurrentText(md["proposal_id"])
        if self.filter_current_esaf_checkbox.isChecked() and md.get("esaf_id"):
            self.filter_esaf_combobox.setCurrentText(md["esaf_id"])

    @asyncSlot(str)
    async def fetch_datasets(self, dataset_name: str):
        """Retrieve a dataset from disk, and provide it to the slot.

        Parameters
        ==========
        dataset_name
          The name in the Tiled catalog of the dataset to retrieve.

        Emits
        =====
        datasets_changed
          Emitted with the new datasets as a dictionary.

        """
        # Retrieve data from the database
        data = await self.db_task(
            self.db.dataset(dataset_name, stream=self.stream),
            name="retrieve_dataset",
        )
        self.datasets_changed.emit(data)

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
        self.ui.filter_plan_combobox.setCurrentText("")
        self.ui.filter_sample_combobox.setCurrentText("")
        self.ui.filter_formula_combobox.setCurrentText("")
        self.ui.filter_scan_combobox.setCurrentText("")
        self.ui.filter_edge_combobox.setCurrentText("")
        self.ui.filter_exit_status_combobox.setCurrentText("")
        self.ui.filter_user_combobox.setCurrentText("")
        self.ui.filter_proposal_combobox.setCurrentText("")
        self.ui.filter_esaf_combobox.setCurrentText("")
        self.ui.filter_current_proposal_checkbox.setChecked(False)
        self.ui.filter_current_esaf_checkbox.setChecked(False)
        self.ui.filter_beamline_combobox.setCurrentText("")
        self.ui.filter_after_checkbox.setChecked(False)
        self.ui.filter_before_checkbox.setChecked(False)
        self.ui.filter_full_text_lineedit.setText("")
        self.ui.filter_standards_checkbox.setChecked(False)

    def reset_default_filters(self):
        self.clear_filters()
        self.ui.filter_exit_status_combobox.setCurrentText("success")
        self.ui.filter_current_esaf_checkbox.setChecked(True)
        self.ui.filter_current_proposal_checkbox.setChecked(True)
        self.ui.filter_after_checkbox.setChecked(True)
        last_week = dt.datetime.now().astimezone() - dt.timedelta(days=7)
        last_week = QDateTime.fromTime_t(int(last_week.timestamp()))
        self.ui.filter_after_datetimeedit.setDateTime(last_week)
        next_week = dt.datetime.now().astimezone() + dt.timedelta(days=7)
        next_week = QDateTime.fromTime_t(int(next_week.timestamp()))
        self.ui.filter_before_datetimeedit.setDateTime(next_week)
        # Set beamline based on config file
        beamline_id = (
            load_config()
            .get("RUN_ENGINE", {})
            .get("DEFAULT_METADATA", {})
            .get("beamline", "")
        )
        self.ui.filter_beamline_combobox.setCurrentText(beamline_id)

    async def update_combobox_items(self):
        """"""
        filter_boxes = {
            "start.plan_name": self.ui.filter_plan_combobox,
            "start.sample_name": self.ui.filter_sample_combobox,
            "start.sample_formula": self.ui.filter_formula_combobox,
            "start.scan_name": self.ui.filter_scan_combobox,
            "start.edge": self.ui.filter_edge_combobox,
            "stop.exit_status": self.ui.filter_exit_status_combobox,
            "start.proposal_id": self.ui.filter_proposal_combobox,
            "start.esaf_id": self.ui.filter_esaf_combobox,
            "start.beamline_id": self.ui.filter_beamline_combobox,
        }
        # Clear old entries first so we don't have stale ones
        for key, cb in filter_boxes.items():
            cb.clear()
        # Populate with new results
        async for field_name, fields in self.db.distinct_fields():
            cb = filter_boxes[field_name]
            old_value = cb.currentText()
            cb.addItems(fields)
            cb.setCurrentText(old_value)

    def customize_ui(self):
        self.load_models()
        self.load_profiles()
        # Setup controls for select which run to show
        for slot in [self.update_streams, self.update_plots, self.update_export_button]:
            self.ui.run_tableview.selectionModel().selectionChanged.connect(slot)
        self.ui.refresh_runs_button.setIcon(qta.icon("fa6s.arrows-rotate"))
        self.ui.refresh_runs_button.clicked.connect(self.reload_runs)
        self.ui.reset_filters_button.clicked.connect(self.reset_default_filters)
        # Select a new catalog
        self.ui.profile_combobox.currentTextChanged.connect(self.change_catalog)
        # Respond to filter controls getting updated
        self.ui.filters_widget.returnPressed.connect(self.refresh_runs_button.click)
        self.filter_current_proposal_checkbox.stateChanged.connect(
            self.update_bss_widgets,
        )
        self.filter_current_esaf_checkbox.stateChanged.connect(
            self.update_bss_widgets,
        )
        # Respond to controls for the current run
        self.ui.reload_plots_button.clicked.connect(self.update_plots)
        self.ui.stream_combobox.currentTextChanged.connect(self.update_data_keys)
        self.ui.stream_combobox.currentTextChanged.connect(self.update_data_frames)
        # Connect to signals for individual tabs
        self.metadata_changed.connect(self.ui.metadata_view.display_metadata)
        self.metadata_changed.connect(self.ui.lineplot_view.stash_metadata)
        self.metadata_changed.connect(self.ui.gridplot_view.set_image_dimensions)
        self.data_keys_changed.connect(self.ui.multiplot_view.update_signal_widgets)
        self.data_keys_changed.connect(self.ui.lineplot_view.update_signal_widgets)
        self.data_keys_changed.connect(self.ui.gridplot_view.update_signal_widgets)
        self.data_keys_changed.connect(self.ui.frameset_tab.update_signal_widgets)
        self.data_frames_changed.connect(self.ui.multiplot_view.plot_multiples)
        self.data_frames_changed.connect(self.ui.lineplot_view.plot)
        self.data_frames_changed.connect(self.ui.gridplot_view.plot)
        self.data_frames_changed.connect(self.ui.frameset_tab.stash_data_frames)
        self.datasets_changed.connect(self.ui.frameset_tab.plot_datasets)
        self.ui.frameset_tab.dataset_selected.connect(self.fetch_datasets)
        # Create a new export dialog for saving files
        self.ui.export_button.clicked.connect(self.export_runs)
        self.export_dialog = ExportDialog(parent=self)
        self.error_dialog = QErrorMessage(parent=self)

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
    async def update_streams(self, *args):
        """Update the list of available streams to choose from."""
        stream_names = await self.db.stream_names(self.selected_uids())
        # Sort so that "primary" is first
        stream_names = sorted(stream_names, key=lambda x: x != "primary")
        self.ui.stream_combobox.clear()
        self.ui.stream_combobox.addItems(stream_names)
        if "primary" in stream_names:
            self.ui.stream_combobox.setCurrentText("primary")

    @property
    def stream(self):
        current_text = self.ui.stream_combobox.currentText()
        return current_text or "primary"

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
        mimetypes = await self.selected_runs[0].formats()
        filenames = dialog.ask(mimetypes=mimetypes)
        mimetype = dialog.selectedMimeTypeFilter()
        formats = [mimetype] * len(filenames)
        try:
            await self.db_task(
                self.db.export_runs(filenames, formats=formats), "export"
            )
        except httpx.ConnectError as exc:
            log.exception(exc)
            msg = "Could not connect to Tiled.<br /><br />"
            msg += f"{exc.request.url}"
            self.error_dialog.showMessage(msg, "connection error")
        except httpx.HTTPStatusError as exc:
            log.exception(exc)
            response = exc.response
            if 400 <= exc.response.status_code < 500:
                msg = "Scan export failed. Firefly could not complete request."
            elif 500 <= exc.response.status_code < 600:
                msg = "Scan export failed.  See Tiled server logs for details."
            else:
                # This shouldn't be possible, only 400 and 500 codes are errors
                msg = "Scan export failed with unknown status code."
            msg += f"<br /><br />Status code: {exc.response.status_code}"
            if response.headers["Content-Type"] == "application/json":
                detail = response.json().get("detail", "")
            else:
                # This can happen when we get an error from a proxy,
                # such as a 502, which serves an HTML error page.
                # Use the stock "reason phrase" for the error code
                # instead of dumping HTML into the terminal.
                detail = response.reason_phrase
            msg += f"<br /><br />{detail}"
            self.error_dialog.showMessage(msg, str(response.status_code))

    @asyncSlot()
    async def update_metadata(self, *args) -> dict[str, dict]:
        """Render metadata for the runs into the metadata widget."""
        # Combine the metadata in a human-readable output
        new_md = await self.db_task(
            self.db.metadata(uids=self.selected_uids()), "metadata"
        )
        self.metadata_changed.emit(new_md)
        return new_md

    @asyncSlot()
    @cancellable
    async def update_plots(self):
        """Get new data, and update all the plots.

        If a *uid* is provided, only the plots matching the scan with
        *uid* will be updated.
        """

        await self.update_metadata()
        await self.update_data_frames()

    @asyncSlot()
    @cancellable
    async def update_data_keys(self, *args):
        stream = self.ui.stream_combobox.currentText()
        uids = self.selected_uids()
        with self.busy_hints(run_widgets=True, run_table=False, filter_widgets=False):
            data_keys, hints = await asyncio.gather(
                self.db_task(self.db.data_keys(uids, stream), "update data keys"),
                self.db_task(self.db.hints(uids, stream), "update data hints"),
            )
        independent_hints, dependent_hints = hints
        self.data_keys_changed.emit(
            data_keys, set(independent_hints), set(dependent_hints)
        )

    @asyncSlot()
    @cancellable
    async def update_data_frames(self):
        stream = self.ui.stream_combobox.currentText()
        uids = self.selected_uids()
        if stream == "":
            data_frames = {}
            log.info("Not loading data frames for empty stream.")
        else:
            with self.busy_hints(
                run_widgets=True, run_table=False, filter_widgets=False
            ):
                data_frames = await self.db_task(
                    self.db.data_frames(uids, stream), "update data frames"
                )
        self.data_frames_changed.emit(data_frames)

    def selected_uids(self) -> set[str]:
        # Get UID's from the selection
        col_idx = self._run_col_names.index("UID")
        indexes = self.ui.run_tableview.selectedIndexes()
        uids = [i.siblingAtColumn(col_idx).data() for i in indexes]
        return set(uids)

    # @asyncSlot()
    # @cancellable
    # async def update_selected_runs(self, *args):
    #     """Get the current runs from the database and stash them."""
    #     # Get selected runs from the database
    #     self.selected_runs = self.db.load_selected_runs(uids=uids)
    #     # Update the necessary UI elements
    #     await self.update_streams()
    #     await self.update_data_keys()
    #     # Update the plots
    #     await self.update_plots()
    #     self.update_export_button()

    def filters(self, *args):
        new_filters = {
            "plan": self.ui.filter_plan_combobox.currentText(),
            "sample": self.ui.filter_sample_combobox.currentText(),
            "formula": self.ui.filter_formula_combobox.currentText(),
            "scan": self.ui.filter_scan_combobox.currentText(),
            "edge": self.ui.filter_edge_combobox.currentText(),
            "exit_status": self.ui.filter_exit_status_combobox.currentText(),
            "user": self.ui.filter_user_combobox.currentText(),
            "proposal": self.ui.filter_proposal_combobox.currentText(),
            "esaf": self.ui.filter_esaf_combobox.currentText(),
            "beamline": self.ui.filter_beamline_combobox.currentText(),
            "full_text": self.ui.filter_full_text_lineedit.text(),
        }
        # Special handling for the time-based filters
        if self.ui.filter_after_checkbox.checkState():
            after = self.ui.filter_after_datetimeedit.dateTime().toSecsSinceEpoch()
            new_filters["after"] = after
        if self.ui.filter_before_checkbox.checkState():
            before = self.ui.filter_before_datetimeedit.dateTime().toSecsSinceEpoch()
            new_filters["before"] = before
        # Limit the search to standards only
        if self.ui.filter_standards_checkbox.checkState():
            new_filters["standards_only"] = True
        # Only include values that were actually filled in
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
