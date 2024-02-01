import logging
from itertools import count
from typing import Sequence
import time
import asyncio

import numpy as np
import qtawesome as qta
import yaml
from qasync import asyncSlot
from matplotlib.colors import TABLEAU_COLORS
from pydantic.error_wrappers import ValidationError
from pyqtgraph import PlotItem, PlotWidget, ImageView
from qtpy.QtCore import Qt, QThread, Signal
from qtpy.QtGui import QStandardItem, QStandardItemModel
from qtpy.QtWidgets import QWidget

from firefly import display
from firefly.run_client import DatabaseWorker
from haven import exceptions

log = logging.getLogger(__name__)


colors = list(TABLEAU_COLORS.values())


def unsnake(arr: np.ndarray, snaking: list) -> np.ndarray:
    """Unsnake a nump array.

    For each axis in *arr*, there should be a corresponding True/False
    in *snaking* whether that axis should have alternating rows. The
    first entry is ignored as it doesn't make sense to snake the first
    axis.
    
    Returns
    =======
    unsnaked
      A copy of *arr* with the odd-numbered axes flipped (if indicated
      by *snaking*).

    """
    # arr = np.copy(arr)
    # Create some slice object for easier manipulation
    full_axis = slice(None)
    alternating = slice(None, None, 2)
    flipped = slice(None, None, -1)
    # Flip each axis if necessary (skipping the first axis)
    for axis, is_snaked in enumerate(snaking[1:]):
        if not is_snaked:
            continue
        slices = (full_axis,) * axis
        slices += (alternating,)
        arr[slices] = arr[slices + (flipped,)]
    return arr

class FiltersWidget(QWidget):
    returnPressed = Signal()

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        # Check for return keys pressed
        if event.key() in [Qt.Key_Enter, Qt.Key_Return]:
            self.returnPressed.emit()


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


class Browser2DPlotWidget(ImageView):

    """A plot widget for 2D maps."""
    def __init__(self, *args, view=None, **kwargs):
        if view is None:
            view = PlotItem()
        super().__init__(*args, view=view, **kwargs)
        

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

    # Signals
    runs_selected = Signal(list)
    runs_model_changed = Signal(QStandardItemModel)
    plot_1d_changed = Signal(object)
    filters_changed = Signal(dict)
    load_distinct_fields = Signal()
    ui_loaded = Signal()

    def __init__(self, root_node=None, args=None, macros=None, **kwargs):
        super().__init__(args=args, macros=macros, **kwargs)
        self.ui_loaded.connect(self.async_slot)
        # self.start_run_client(root_node=root_node)
        loop = asyncio.get_event_loop()
        print(loop)
        loop.create_task(self.async_slot())
        # self.ui_loaded.emit()

    async def async_slot(self):
        print("hello", end="", flush=True)
        for i in range(10):
            print(".", end="", flush=True)
            await asyncio.sleep(1)
        print("world", flush=True)

    def start_run_client(self, root_node):
        """Set up the database client in a separate thread."""
        # Create the thread and worker
        thread = QThread(parent=self)
        self._thread = thread
        worker = DatabaseWorker(root_node=root_node)
        self._db_worker = worker
        worker.moveToThread(thread)
        # Set up filters
        worker.new_message.connect(self.show_message)
        self.filters_changed.connect(worker.set_filters)
        self.update_filters()
        # Connect signals/slots
        thread.started.connect(worker.load_all_runs)
        worker.all_runs_changed.connect(self.set_runs_model_items)
        worker.selected_runs_changed.connect(self.update_metadata)
        worker.selected_runs_changed.connect(self.update_1d_signals)
        worker.selected_runs_changed.connect(self.update_2d_signals)
        worker.selected_runs_changed.connect(self.update_1d_plot)
        worker.selected_runs_changed.connect(self.update_2d_plot)
        worker.selected_runs_changed.connect(self.update_multi_plot)
        worker.db_op_started.connect(self.disable_run_widgets)
        worker.db_op_ended.connect(self.enable_run_widgets)
        self.runs_selected.connect(worker.load_selected_runs)
        self.ui.refresh_runs_button.clicked.connect(worker.load_all_runs)
        # Make sure filters are current
        self.update_filters()
        # Start the thread
        thread.start()
        # Get distinct fields so we can populate the comboboxes
        self.load_distinct_fields.connect(worker.load_distinct_fields)
        worker.distinct_fields_changed.connect(self.update_combobox_items)
        self.load_distinct_fields.emit()

    def update_combobox_items(self, fields):
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

    def customize_ui(self):
        self.load_models()
        # Setup controls for select which run to show
        self.ui.run_tableview.selectionModel().selectionChanged.connect(
            self.update_selected_runs
        )
        self.ui.refresh_runs_button.setIcon(qta.icon("fa5s.sync"))
        # Respond to changes in displaying the 1d plot
        self.ui.signal_y_combobox.currentTextChanged.connect(self.update_1d_plot)
        self.ui.signal_x_combobox.currentTextChanged.connect(self.update_1d_plot)
        self.ui.signal_r_combobox.currentTextChanged.connect(self.update_1d_plot)
        self.ui.signal_r_checkbox.stateChanged.connect(self.update_1d_plot)
        self.ui.logarithm_checkbox.stateChanged.connect(self.update_1d_plot)
        self.ui.invert_checkbox.stateChanged.connect(self.update_1d_plot)
        self.ui.gradient_checkbox.stateChanged.connect(self.update_1d_plot)
        self.ui.plot_1d_hints_checkbox.stateChanged.connect(self.update_1d_signals)
        # Respond to changes in displaying the 2d plot
        self.ui.signal_value_combobox.currentTextChanged.connect(self.update_2d_plot)
        self.ui.logarithm_checkbox_2d.stateChanged.connect(self.update_2d_plot)
        self.ui.invert_checkbox_2d.stateChanged.connect(self.update_2d_plot)
        self.ui.gradient_checkbox_2d.stateChanged.connect(self.update_2d_plot)
        self.ui.plot_2d_hints_checkbox.stateChanged.connect(self.update_2d_signals)
        # Respond to filter controls getting updated
        self.ui.filter_user_combobox.currentTextChanged.connect(self.update_filters)
        self.ui.filter_proposal_combobox.currentTextChanged.connect(self.update_filters)
        self.ui.filter_sample_combobox.currentTextChanged.connect(self.update_filters)
        self.ui.filter_exit_status_combobox.currentTextChanged.connect(
            self.update_filters
        )
        self.ui.filter_esaf_combobox.currentTextChanged.connect(self.update_filters)
        self.ui.filter_current_proposal_checkbox.stateChanged.connect(
            self.update_filters
        )
        self.ui.filter_current_esaf_checkbox.stateChanged.connect(self.update_filters)
        self.ui.filter_plan_combobox.currentTextChanged.connect(self.update_filters)
        self.ui.filter_full_text_lineedit.textChanged.connect(self.update_filters)
        self.ui.filter_edge_combobox.currentTextChanged.connect(self.update_filters)
        self.ui.filters_widget.returnPressed.connect(self.refresh_runs_button.click)
        # Set up 1D plotting widgets
        self.plot_1d_item = self.ui.plot_1d_view.getPlotItem()
        self.plot_2d_item = self.ui.plot_2d_view.getImageItem()
        self.plot_1d_item.addLegend()
        self.plot_1d_item.hover_coords_changed.connect(
            self.ui.hover_coords_label.setText
        )

    def get_signals(self, run, hinted_only=False):
        if hinted_only:
            xsignals = run.metadata["start"]["hints"]["dimensions"][0][0]
            ysignals = []
            hints = run["primary"].metadata["descriptors"][0]["hints"]
            for device, dev_hints in hints.items():
                ysignals.extend(dev_hints["fields"])
        else:
            xsignals = ysignals = run["primary"]["data"].keys()
        return xsignals, ysignals

    def set_runs_model_items(self, runs):
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
        self.runs_model_changed.emit(self.ui.runs_model)
        self.runs_total_label.setText(str(self.ui.runs_model.rowCount()))

    def disable_run_widgets(self):
        self.show_message("Loading...")
        widgets = [
            self.ui.run_tableview,
            self.ui.refresh_runs_button,
            self.ui.detail_tabwidget,
            self.ui.runs_total_layout,
            self.ui.filters_widget,
        ]
        for widget in widgets:
            widget.setEnabled(False)
        self.disabled_widgets = widgets
        self.setCursor(Qt.WaitCursor)

    def enable_run_widgets(self, exceptions=[]):
        if any(exceptions):
            self.show_message(exceptions[0])
        else:
            self.show_message("Done", 5000)
        # Re-enable the widgets
        for widget in self.disabled_widgets:
            widget.setEnabled(True)
        self.setCursor(Qt.ArrowCursor)

    def update_1d_signals(self, *args):
        # Store old values for restoring later
        comboboxes = [
            self.ui.signal_x_combobox,
            self.ui.signal_y_combobox,
            self.ui.signal_r_combobox,
        ]
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
        xcols = sorted(list(set(xcols)))
        ycols = sorted(list(set(ycols)))
        self.multi_y_signals = ycols
        for cb in [self.ui.multi_signal_x_combobox, self.ui.signal_x_combobox]:
            cb.clear()
            cb.addItems(xcols)
        for cb in [
            self.ui.signal_y_combobox,
            self.ui.signal_r_combobox,
        ]:
            cb.clear()
            cb.addItems(ycols)
        # Restore previous values
        for val, cb in zip(old_values, comboboxes):
            cb.setCurrentText(val)

    def update_2d_signals(self, *args):
        # Store current selection for restoring later
        val_cb = self.ui.signal_value_combobox
        old_value = val_cb.currentText()
        # Determine valid list of dependent signals to choose from
        vcols = set()
        runs = self._db_worker.selected_runs
        use_hints = self.ui.plot_2d_hints_checkbox.isChecked()
        for run in runs:
            try:
                _xcols, _vcols = self.get_signals(run, hinted_only=use_hints)
            except KeyError:
                continue
            else:
                vcols.update(_vcols)
        # Update the UI with the list of controls
        vcols = sorted(list(set(vcols)))
        val_cb.clear()
        val_cb.addItems(vcols)
        # Restore previous selection
        val_cb.setCurrentText(old_value)
            

    def calculate_ydata(
        self,
        x_data,
        y_data,
        r_data,
        x_signal,
        y_signal,
        r_signal,
        use_reference=False,
        use_log=False,
        use_invert=False,
        use_grad=False,
    ):
        """Take raw y and reference data and calculate a new y_data signal."""
        # Make sure we have numpy arrays
        x = np.asarray(x_data)
        y = np.asarray(y_data)
        r = np.asarray(r_data)
        # Apply transformations
        y_string = f"[{y_signal}]"
        try:
            if use_reference:
                y = y / r
                y_string = f"{y_string}/[{r_signal}]"
            if use_log:
                y = np.log(y)
                y_string = f"ln({y_string})"
            if use_invert:
                y *= -1
                y_string = f"-{y_string}"
            if use_grad:
                y = np.gradient(y, x)
                y_string = f"d({y_string})/d[{r_signal}]"
        except TypeError as exc:
            msg = f"Could not calculate transformation: {exc}"
            log.warning(msg)
            raise
            raise exceptions.InvalidTransformation(msg)
        return y, y_string

    def load_run_data(self, run, x_signal, y_signal, r_signal, use_reference=True):
        if "" in [x_signal, y_signal] or (use_reference and r_signal == ""):
            log.debug(
                f"Empty signal name requested: x='{x_signal}', y='{y_signal}',"
                f" r='{r_signal}'"
            )
            raise exceptions.EmptySignalName
        signals = [x_signal, y_signal]
        if use_reference:
            signals.append(r_signal)
        try:
            data = run["primary"]["data"]
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
        except ValidationError:
            print("Pydantic error:", run)
            raise
        return x_data, y_data, r_data

    def load_run_data_nd(self, run, signal: str):
        """Load N-dimensional data for a signal for a run.

        Returns
        =======
        data
          The signal data converted to the shape for the dataset."""
        try:
            data = run["primary"]["data"]
            data = np.array(data[signal].read())
        except KeyError as e:
            # No data, so nothing to plot
            msg = f"Cannot find key {e} in {run}."
            log.warning(msg)
            raise exceptions.SignalNotFound(msg)
        # Reshape the data to match the scan
        if "shape" in run.metadata['start']:
            shape = run.metadata['start']['shape']
            data = data.reshape(shape)
        # Flip alternating rows if snaking is enabled
        if "snaking" in run.metadata['start']:
            snaking = run.metadata['start']['snaking']
            data = unsnake(data, snaking)
        return data

    def multiplot_items(self, n_cols: int = 3):
        view = self.ui.plot_multi_view
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

    def update_multi_plot(self, *args):
        x_signal = self.ui.multi_signal_x_combobox.currentText()
        if x_signal == "":
            return
        y_signals = self.multi_y_signals
        all_signals = set((x_signal, *y_signals))
        view = self.ui.plot_multi_view
        view.clear()
        self._multiplot_items = {}
        n_cols = 3
        runs = self._db_worker.selected_runs
        for run in runs:
            data = run["primary"]["data"].read(all_signals)
            try:
                xdata = data[x_signal]
            except KeyError:
                log.warning(f"Cannot plot x='{x_signal}' for {list(data.keys())}")
                continue
            for y_signal, plot_item in zip(y_signals, self.multiplot_items()):
                # Get data from the database
                try:
                    plot_item.plot(xdata, data[y_signal])
                except KeyError:
                    log.warning(f"Cannot plot y='{y_signal}' for {list(data.keys())}")
                    continue
                else:
                    log.debug(f"Plotted {y_signal} vs. {x_signal} for {data}")
                finally:
                    plot_item.setTitle(y_signal)

    def update_1d_plot(self, *args):
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
        x_data = None
        for idx, run in enumerate(self._db_worker.selected_runs):
            # Load datasets from the database
            try:
                x_data, y_data, r_data = self.load_run_data(
                    run, x_signal, y_signal, r_signal, use_reference=use_reference
                )
            except exceptions.SignalNotFound as e:
                self.show_message(str(e), 0)
                continue
            except exceptions.EmptySignalName:
                continue
            # Screen out non-numeric data types
            try:
                np.isfinite(x_data)
                np.isfinite(y_data)
                np.isfinite(r_data)
            except TypeError as e:
                msg = str(e)
                log.warning(msg)
                self.show_message(msg)
                continue
            # Calculate plotting data
            try:
                y_data, y_string = self.calculate_ydata(
                    x_data,
                    y_data,
                    r_data,
                    x_signal,
                    y_signal,
                    r_signal,
                    use_reference=use_reference,
                    use_log=use_log,
                    use_invert=use_invert,
                    use_grad=use_grad,
                )
            except exceptions.InvalidTransformation as e:
                self.show_message(str(e))
                raise
                continue
            # Plot this run's data
            color = colors[idx % len(colors)]
            self.plot_1d_item.plot(
                x=x_data,
                y=y_data,
                pen=color,
                name=run.metadata["start"]["uid"],
                clear=False,
            )
        # Axis formatting
        self.plot_1d_item.setLabels(left=y_string, bottom=x_signal)
        if x_data is not None:
            self.plot_1d_item.addLine(
                x=np.median(x_data), movable=True, label="{value:.3f}"
            )
        self.plot_1d_changed.emit(self.plot_1d_item)

    def update_2d_plot(self):
        """Change the 2D map plot based on desired signals, etc."""
        # Figure out which signals to plot
        value_signal = self.ui.signal_value_combobox.currentText()
        use_log = self.ui.logarithm_checkbox_2d.isChecked()
        use_invert = self.ui.invert_checkbox_2d.isChecked()
        use_grad = self.ui.gradient_checkbox_2d.isChecked()
        # Load mapping data for each run
        images = []
        for idx, run in enumerate(self._db_worker.selected_runs):
            # Load datasets from the database
            try:
                image = self.load_run_data_nd(run, value_signal)
            except exceptions.SignalNotFound as e:
                self.show_message(str(e), 0)
                continue
            except exceptions.EmptySignalName:
                continue
            images.append(image)
        images = np.asarray(images)
        # Make sure there's some data to plot
        if not (2 < images.ndim < 4):
            self.plot_2d_item.clear()
            return
        # Combine the different runs into one image
        # To-do: make this respond to the combobox selection        
        image = np.mean(images, axis=0)
        # To-do: Apply transformations
        
        # # Plot the image
        self.plot_2d_view.setImage(image.T, autoRange=False)
        # Determine the axes labels
        dimensions = run.metadata['start']['hints']['dimensions']
        xlabel = dimensions[-1][0][0]
        self.plot_2d_view.view.setLabel(axis="bottom", text=xlabel)
        ylabel = dimensions[-2][0][0]
        self.plot_2d_view.view.setLabel(axis="left", text=ylabel)
        # Set axes extent
        yextent, xextent = run.metadata['start']['extents']
        x = xextent[0]
        y = yextent[0]
        w = xextent[1] - xextent[0]
        h = yextent[1] - yextent[0]
        self.plot_2d_item.setRect(x, y, w, h)

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

    def update_filters(self, *args):
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
        self.filters_changed.emit(new_filters)

    def load_models(self):
        # Set up the model
        self.runs_model = QStandardItemModel()
        # Add the model to the UI element
        self.ui.run_tableview.setModel(self.runs_model)

    def ui_filename(self):
        return "run_browser.ui"


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2023, UChicago Argonne, LLC
#
# Distributed under the terms of the 3-Clause BSD License
#
# The full license is in the file LICENSE, distributed with this software.
#
# DISCLAIMER
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# -----------------------------------------------------------------------------
