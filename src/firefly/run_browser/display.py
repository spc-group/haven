import asyncio
import datetime as dt
import logging
from collections import Counter
from contextlib import contextmanager
from functools import wraps
from typing import Mapping, Optional, Sequence

import httpx
import pandas as pd
import qtawesome as qta
import xarray as xr
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
        "✓",
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
    data_changed = Signal(dict)
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

    def db_task(self, coro, name="default task"):
        """Executes a co-routine as a database task. Existing database
        tasks with the same *name* get cancelled.

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
                checkbox = QStandardItem(True)
                checkbox.setCheckable(True)
                checkbox.setCheckState(False)
                items = [checkbox]
                items += [QStandardItem(val) for val in run.values()]
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
            # self.ui.run_tableview.selectionModel().selectionChanged.connect(slot)
            self.ui.runs_model.dataChanged.connect(slot)
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
        self.ui.stream_combobox.currentTextChanged.connect(self.update_signal_widgets)
        self.ui.stream_combobox.currentTextChanged.connect(self.update_datasets)
        # Connect to signals for individual tabs
        self.metadata_changed.connect(self.ui.metadata_tab.display_metadata)
        self.metadata_changed.connect(self.ui.gridplot_tab.set_image_dimensions)
        # Create a new export dialog for saving files
        self.ui.export_button.clicked.connect(self.export_runs)
        self.export_dialog = ExportDialog(parent=self)
        self.error_dialog = QErrorMessage(parent=self)
        # Respond to signal selection widgets
        self.ui.use_hints_checkbox.stateChanged.connect(self.update_signal_widgets)
        self.ui.x_signal_combobox.currentTextChanged.connect(self.update_plots)
        self.ui.y_signal_combobox.currentTextChanged.connect(self.update_plots)
        self.ui.swap_button.setIcon(qta.icon("mdi.swap-horizontal"))
        self.ui.swap_button.clicked.connect(self.swap_signals)
        self.ui.r_signal_combobox.currentTextChanged.connect(self.update_plots)
        self.ui.r_signal_checkbox.stateChanged.connect(self.update_plots)
        self.ui.logarithm_checkbox.stateChanged.connect(self.update_plots)
        self.ui.invert_checkbox.stateChanged.connect(self.update_plots)
        self.ui.gradient_checkbox.stateChanged.connect(self.update_plots)

    def swap_signals(self):
        """Swap the value and reference signals."""
        new_r = self.ui.y_signal_combobox.currentText()
        new_y = self.ui.r_signal_combobox.currentText()
        self.ui.y_signal_combobox.setCurrentText(new_y)
        self.ui.r_signal_combobox.setCurrentText(new_r)

    @asyncSlot()
    @cancellable
    async def update_signal_widgets(self):
        """Update the UI based on new data keys and hints.

        If any of *data_keys*, *independent_hints* or
        *dependent_hints* are used, then the last seen values will be
        used.

        """
        data_keys, ihints, dhints = await self.data_signals()
        # Decide whether we want to use hints
        use_hints = self.ui.use_hints_checkbox.isChecked()
        if use_hints:
            new_xcols = ihints
            new_ycols = dhints
        else:
            new_xcols = list(data_keys.keys())
            new_ycols = list(data_keys.keys())
        # Update the UI
        comboboxes = [
            self.ui.x_signal_combobox,
            self.ui.y_signal_combobox,
            self.ui.r_signal_combobox,
        ]
        for combobox, new_cols in zip(comboboxes, [new_xcols, new_ycols, new_ycols]):
            old_value = combobox.currentText()
            combobox.clear()
            combobox.addItems(sorted(new_cols, key=str.lower))
            if old_value in new_cols:
                combobox.setCurrentText(old_value)

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
        await self.update_datasets()
        await self.update_internal_dataframes()

    async def data_signals(self) -> tuple[dict, set[str], set[str]]:
        """Get valid keys and hints for the selected UIDs."""
        stream = self.ui.stream_combobox.currentText()
        uids = self.selected_uids()
        with self.busy_hints(run_widgets=True, run_table=False, filter_widgets=False):
            data_keys, hints = await asyncio.gather(
                self.db_task(self.db.data_keys(uids, stream), "update data keys"),
                self.db_task(self.db.hints(uids, stream), "update data hints"),
            )
        independent_hints, dependent_hints = hints
        return data_keys, set(independent_hints), set(dependent_hints)

    # def axis_labels(self):
    #     xlabel = self.ui.x_signal_combobox.currentText()
    #     ylabel = self.ui.y_signal_combobox.currentText()
    #     rlabel = self.ui.r_signal_combobox.currentText()
    #     use_reference = self.ui.r_signal_checkbox.checkState()
    #     inverted = self.ui.invert_checkbox.checkState()
    #     logarithm = self.ui.logarithm_checkbox.checkState()
    #     gradient = self.ui.gradient_checkbox.checkState()
    #     if use_reference and inverted:
    #         ylabel = f"{rlabel}/{ylabel}"
    #     elif use_reference:
    #         ylabel = f"{ylabel}/{rlabel}"
    #     elif inverted:
    #         ylabel = f"1/{ylabel}"
    #     if logarithm:
    #         ylabel = f"ln({ylabel})"
    #     if gradient:
    #         ylabel = f"grad({ylabel})"
    #     return xlabel, ylabel

    # def label_from_metadata(self, start_doc: Mapping) -> str:
    #     # Determine label from metadata
    #     uid = start_doc.get("uid", "")
    #     sample_name = start_doc.get("sample_name")
    #     scan_name = start_doc.get("scan_name")
    #     sample_formula = start_doc.get("sample_formula")
    #     if sample_name is not None and sample_formula is not None:
    #         sample_name = f"{sample_name} ({sample_formula})"
    #     elif sample_formula is not None:
    #         sample_name = sample_formula
    #     md_values = [val for val in [sample_name, scan_name] if val is not None]
    #     # Use the full UID unless we have something else to show
    #     if len(md_values) > 0:
    #         uid = uid.split("-")[0]
    #     # Build the label
    #     label = " — ".join([uid, *md_values])
    #     if start_doc.get("is_standard", False):
    #         label = f"{label} ★"
    #     return label

    ### From lineplot_view
    # def prepare_plotting_data(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    #     xsignal = self.ui.x_signal_combobox.currentText()
    #     ysignal = self.ui.y_signal_combobox.currentText()
    #     rsignal = self.ui.r_signal_combobox.currentText()
    #     # Get data from dataframe
    #     xdata = df[xsignal].values
    #     ydata = df[ysignal].values
    #     rdata = df[rsignal].values
    #     # Apply corrections
    #     if self.ui.r_signal_checkbox.checkState():
    #         ydata = ydata / rdata
    #     if self.ui.invert_checkbox.checkState():
    #         ydata = 1 / ydata
    #     if self.ui.logarithm_checkbox.checkState():
    #         ydata = np.log(ydata)
    #     if self.ui.gradient_checkbox.checkState():
    #         ydata = np.gradient(ydata, xdata)
    #     return (xdata, ydata)

    ### From gridplot_view
    # def prepare_plotting_data(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    #     """Prepare independent and dependent datasets from this
    #     dataframe and UI state.

    #     Based on the state of various UI widgets, the image data may
    #     be reference-corrected or inverted and be converted to its
    #     natural-log or gradeient. Additionally, the images may be
    #     re-gridded: interpolated to match the readback values of a
    #     independent, scanned axis (e.g. motor position).

    #     Parameters
    #     ==========
    #     df
    #       The dataframe from which to pull data.

    #     Returns
    #     =======
    #     img
    #       The 2D or 3D image data to plot in (slice, row, col) order.

    #     """
    #     xsignal = self.ui.regrid_xsignal_combobox.currentText()
    #     ysignal = self.ui.regrid_ysignal_combobox.currentText()
    #     vsignal = self.ui.value_signal_combobox.currentText()
    #     rsignal = self.ui.r_signal_combobox.currentText()
    #     # Get data from dataframe
    #     values = df[vsignal]
    #     # Make the grid linear based on measured motor positions
    #     if self.ui.regrid_checkbox.checkState():
    #         xdata = df[xsignal]
    #         ydata = df[ysignal]
    #         values = self.regrid(points=np.c_[ydata, xdata], values=values)
    #     # Apply scaler filters
    #     if self.ui.r_signal_checkbox.checkState():
    #         values = values / df[rsignal]
    #     if self.ui.invert_checkbox.checkState():
    #         values = 1 / values
    #     if self.ui.logarithm_checkbox.checkState():
    #         values = np.log(values)
    #     # Reshape to an image
    #     img = np.reshape(values, self.shape)
    #     # Apply gradient filter
    #     if self.ui.gradient_checkbox.checkState():
    #         img = np.gradient(img)
    #         img = np.linalg.norm(img, axis=0)
    #     return img

    @asyncSlot()
    @cancellable
    async def update_internal_dataframes(self) -> dict[str, pd.DataFrame]:
        """Load only signals for the "internal" part of the run, and plot."""
        stream = self.ui.stream_combobox.currentText()
        uids = self.selected_uids()
        if stream == "":
            dataframes = {}
            log.info("Not loading dataframes for empty stream.")
        else:
            with self.busy_hints(
                run_widgets=True, run_table=False, filter_widgets=False
            ):
                # dataframes = await self.db_task(
                #     self.db.dataframes(uids, stream),
                #     "update_dataframes"
                # )
                dataframes = await self.db.dataframes(uids, stream)

        self.ui.multiplot_tab.plot(dataframes)
        return dataframes

    @asyncSlot()
    @cancellable
    async def update_datasets(self) -> dict[str, xr.Dataset]:
        stream = self.ui.stream_combobox.currentText()
        uids = self.selected_uids()
        xsig = self.x_signal_combobox.currentText()
        ysig = self.y_signal_combobox.currentText()
        rsig = self.r_signal_combobox.currentText()
        print(xsig, ysig, rsig)
        if stream == "":
            datasets = {}
            log.info("Not loading datasets for empty stream.")
        else:
            with self.busy_hints(
                run_widgets=True, run_table=False, filter_widgets=False
            ):
                # datasets = await self.db_task(
                #     self.db.datasets(uids, stream, xcolumn=xsig, ycolumn=ysig, rcolumn=rsig),
                #     "update_datasets"
                # )
                datasets = await self.db.datasets(
                    uids, stream, xcolumn=xsig, ycolumn=ysig, rcolumn=rsig
                )

        print(datasets)
        self.ui.lineplot_tab.plot(datasets)
        self.ui.gridplot_tab.plot(datasets)
        self.ui.frameset_tab.plot(datasets)
        self.ui.spectra_tab.plot(datasets)
        return datasets

    def selected_uids(self) -> set[str]:
        # Get UID's from the selection
        uid_col = self._run_col_names.index("UID")
        cbox_col = 0
        model = self.runs_model
        uids = [
            model.item(row_idx, uid_col).text()
            for row_idx in range(self.runs_model.rowCount())
            if model.item(row_idx, cbox_col).checkState()
        ]
        return set(uids)

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

    def print_data(self, *args, **kwargs):
        print(args)
        print(kwargs)

    def load_models(self):
        # Set up the model
        self.runs_model = QStandardItemModel()
        self.runs_model.dataChanged.connect(self.print_data)
        # Add the model to the UI element
        self.ui.run_tableview.setModel(self.runs_model)

    def ui_filename(self):
        return "run_browser/run_browser.ui"
