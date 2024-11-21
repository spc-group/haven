import logging
from datetime import datetime, time
from typing import Mapping

import qtawesome as qta
from bluesky_queueserver_api import BPlan
from bluesky.protocols import Readable
from pydm.widgets.label import PyDMLabel
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTableWidgetItem
from qasync import asyncSlot
from qtpy import QtCore, QtWidgets
from tiled.adapters.mapping import MapAdapter
from tiled.client import Context, from_context
from tiled.server.app import build_app
from ophydregistry.exceptions import ComponentNotFound

import haven
import asyncio
from firefly.component_selector import ComponentSelector
from firefly.plans import regions_display
from firefly.tests.fake_position_runs import position_runs
from haven.motor_position import get_motor_position, get_motor_positions

log = logging.getLogger()

test = True
if test:
    # Fake client for testing purpose
    def create_fake_client():
        tree = MapAdapter(position_runs)
        app = build_app(tree)
        with Context.from_app(app) as context:
            client = from_context(context)
            return client

    fake_client = create_fake_client()
    haven.motor_position.tiled_client = lambda: fake_client


class TitleRegion:
    def __init__(self):
        self.setup_ui()

    def setup_ui(self):
        self.layout = QtWidgets.QHBoxLayout()

        # Enable checkbox
        self.regions_all_checkbox = QtWidgets.QCheckBox()
        self.regions_all_checkbox.setChecked(True)
        self.regions_all_checkbox.setFixedWidth(15)

        self.layout.addWidget(self.regions_all_checkbox)

        labels = ["Motor", "Value"]

        Qlabels_all = {}
        for label_i in labels:
            Qlabel_i = QtWidgets.QLabel(label_i)
            self.layout.addWidget(Qlabel_i)
            Qlabels_all[label_i] = Qlabel_i

        # Fix widths so the labels are aligned with MotorRegions
        Qlabels_all["Value"].setFixedWidth(60)


class MotorRegion(regions_display.RegionBase):
    def setup_ui(self):
        self.layout = QtWidgets.QHBoxLayout()

        # First item, Enable checkbox
        self.region_checkbox = QtWidgets.QCheckBox()
        self.region_checkbox.setChecked(True)
        self.layout.addWidget(self.region_checkbox)

        # Second item, ComponentSelector
        self.motor_box = ComponentSelector()
        self.layout.addWidget(self.motor_box)

        # Third item, motor readback values
        self.rbv_label = QtWidgets.QLabel()
        self.update_rbv()
        self.layout.addWidget(self.rbv_label)

        # Update rbv when motor is changed and edit is finished
        self.motor_box.combo_box.currentIndexChanged.connect(self.update_rbv)
        self.motor_box.combo_box.lineEdit().editingFinished.connect(self.update_rbv)

        # Disable/enable regions when uncheck/check region checkbox
        self.region_checkbox.stateChanged.connect(self.on_region_checkbox)

    def on_region_checkbox(self, is_checked):
        # disable/enable motor box and rbv label
        self.motor_box.setEnabled(is_checked)
        self.rbv_label.setEnabled(is_checked)

    @asyncSlot()
    async def update_rbv(self):
        await self._update_rbv()

    async def _update_rbv(self):
        try:
            motor = self.motor_box.current_component()
            if motor is None:
                self.rbv_label.setText("No motor selected")
                return

            if not isinstance(motor, Readable):
                self.rbv_label.setText("Not readable")
                return
            value_dict = await motor.read()
            # add warnings to users about unmovable motors
            if not isinstance(motor, Movable):
                logging.error(f"warn user that this is not movable and cannot be moved")

            if len(value_dict) == 1:
                value = list(value_dict.values())[0]["value"]
                self.rbv_label.setText(str(value))
            elif len(value_dict) > 1:
                self.rbv_label.setText("Multiple values")
            else:
                self.rbv_label.setText("No values")
        except ComponentNotFound as e:
            self.rbv_label.setText("")
            logging.error(f"ComponentNotFound: {e}")
        except Exception as e:
            self.rbv_label.setText("Error")
            logging.error(f"An error occurred in _update_rbv: {e}")


class QTextBrowserHandler(logging.Handler):
    def __init__(self, text_browser):
        super().__init__()
        self.text_browser = text_browser

    def emit(self, record):
        if "ComponentNotFound" in record.msg or "_update_rbv" in record.msg:
            msg = self.format(record)
            self.text_browser.append(msg)


class SaveMotorDisplay(regions_display.RegionsDisplay):

    Region = MotorRegion
    default_num_regions = 1

    def customize_ui(self):
        super().customize_ui()

        # Add title layout
        self.title_region = TitleRegion()
        self.ui.title_layout.addLayout(self.title_region.layout)

        # Initialize saved positions table
        self.init_saved_positions_table()

        self.title_region.regions_all_checkbox.stateChanged.connect(
            self.on_regions_all_checkbox
        )
        self.ui.refresh_button.setIcon(qta.icon("fa5s.sync-alt"))

        # Redirect logs to the textBrowser
        log_handler = QTextBrowserHandler(self.ui.textBrowser)
        log_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        log_handler.setLevel(logging.DEBUG)
        logging.getLogger().addHandler(log_handler)

    def init_saved_positions_table(self):
        # Set the headers for the table
        self.ui.saved_positions_tableWidget.setHorizontalHeaderLabels(
            ["Name", "Savetime", "UID"]
        )

        # Connect double click to show saved position info
        self.ui.saved_positions_tableWidget.itemDoubleClicked.connect(
            self.show_saved_position_info
        )

        # Set selection behavior to select rows rather than individual cells
        self.ui.saved_positions_tableWidget.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectRows
        )

        # Connect the refresh button to the slot
        self.ui.refresh_button.clicked.connect(self.refresh_saved_position_list_slot)
        # Schedule the initial refresh after the event loop starts
        QtCore.QTimer.singleShot(0, self.refresh_saved_position_list_slot)

        # Connect signals & slots for checkboxes to enable/disable date edits
        self.ui.checkBox_start.toggled.connect(self.ui.dateEdit_start.setEnabled)
        self.ui.checkBox_stop.toggled.connect(self.ui.dateEdit_stop.setEnabled)

        # For saving motor positions
        self.ui.run_now_button.clicked.connect(self.queue_plan_now)

        # For recalling motor positions
        self.ui.recall_button.clicked.connect(self.recall_motor_queue_plan)
        self.ui.recall_now_button.clicked.connect(self.recall_motor_queue_plan_now)

        # Enable/disable recall buttons based on selection
        self.ui.saved_positions_tableWidget.itemSelectionChanged.connect(
            self.update_recall_buttons
        )

        # Connect Enter key to refresh table
        self.ui.lineEdit_filter_names.returnPressed.connect(
            self.refresh_saved_position_list_slot
        )

    def update_recall_buttons(self):
        if self.ui.saved_positions_tableWidget.selectedItems():
            self.ui.recall_button.setEnabled(True)
            self.ui.recall_now_button.setEnabled(True)
        else:
            self.ui.recall_button.setEnabled(False)
            self.ui.recall_now_button.setEnabled(False)

    @asyncSlot()
    async def refresh_saved_position_list(self):
        # Disable sorting temporarily to prevent UID missing bug
        self.ui.saved_positions_tableWidget.setSortingEnabled(False)

        # Clear the existing rows in the table
        self.ui.saved_positions_tableWidget.setRowCount(0)

        # Determine dates 'after' and 'before' based on checkboxes
        after = None
        before = None

        # Get the filter text from the line edit
        filter_text = self.ui.lineEdit_filter_names.text()
        if not filter_text:
            filter_text = None

        if self.ui.checkBox_start.isChecked():
            start_date = self.ui.dateEdit_start.date().toPyDate()
            # Set the time to the earliest time of the day (00:00:00)
            start_datetime = datetime.combine(start_date, datetime.min.time())
            after = start_datetime.timestamp()

        if self.ui.checkBox_stop.isChecked():
            stop_date = self.ui.dateEdit_stop.date().toPyDate()
            # Set the time to the latest time of the day (23:59:59)
            stop_time = time(23, 59, 59)
            stop_datetime = datetime.combine(stop_date, stop_time)
            before = stop_datetime.timestamp()

        # Retrieve the saved positions with filtering
        saved_positions_all = get_motor_positions(
            after=after, before=before, name=filter_text, case_sensitive=False
        )

        positions_list = []

        async for saved_position_i in saved_positions_all:
            positions_list.append(saved_position_i)
            current_row_position = self.ui.saved_positions_tableWidget.rowCount()
            self.ui.saved_positions_tableWidget.insertRow(current_row_position)

            # Format the savetime
            savetime_str = datetime.fromtimestamp(saved_position_i.savetime).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            # Add names, UIDs, and Savetime to the table widget
            name_item = QTableWidgetItem(saved_position_i.name)
            savetime_item = QTableWidgetItem(savetime_str)
            uid_item = QTableWidgetItem(saved_position_i.uid)

            self.ui.saved_positions_tableWidget.setItem(
                current_row_position, 0, name_item
            )
            self.ui.saved_positions_tableWidget.setItem(
                current_row_position, 1, savetime_item
            )
            self.ui.saved_positions_tableWidget.setItem(
                current_row_position, 2, uid_item
            )

        # Re-enable sorting after the rows have been added
        self.ui.saved_positions_tableWidget.setSortingEnabled(True)
        # Sort the table by the savetime column, the latest saved position will be on top
        self.ui.saved_positions_tableWidget.sortItems(1, Qt.DescendingOrder)
        # Resize columns to fit contents
        self.ui.saved_positions_tableWidget.resizeColumnsToContents()

        # Set default filter dates if there are items in the table and if the checkboxes are unchecked
        if positions_list:
            # Sort positions_list by savetime
            positions_list.sort(key=lambda x: x.savetime)
            first_savetime = positions_list[0].savetime
            last_savetime = positions_list[-1].savetime

            if not self.ui.checkBox_start.isChecked():
                self.ui.dateEdit_start.setDateTime(
                    datetime.fromtimestamp(first_savetime)
                )

            if not self.ui.checkBox_stop.isChecked():
                self.ui.dateEdit_stop.setDateTime(datetime.fromtimestamp(last_savetime))

    @asyncSlot()
    async def refresh_saved_position_list_slot(self):
        await self.refresh_saved_position_list()

    def show_saved_position_info(self, item):
        # Get the row of the clicked item
        row = self.ui.saved_positions_tableWidget.row(item)

        # Get the name, uid, and other details for this row
        name_item = self.ui.saved_positions_tableWidget.item(row, 0)
        uid_item = self.ui.saved_positions_tableWidget.item(row, 2)
        if not name_item or not uid_item:
            self.ui.textBrowser.append("Failed to retrieve selected motor positions.")
            return

        name = name_item.text()
        uid = uid_item.text()

        # Create a dialog window
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Position Details")

        # Create a QTreeWidget to display the details
        tree = QtWidgets.QTreeWidget(dialog)
        tree.setColumnCount(3)  # Set columns for Motor, Readback, and Offset
        tree.setHeaderLabels(["Motor", "Readback", "Offset"])

        # Allow selection of individual cells
        tree.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        tree.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)

        # Create the root item (the position name and uid)
        root = QtWidgets.QTreeWidgetItem(tree)
        timestamp = self.ui.saved_positions_tableWidget.item(row, 1).text()
        root.setText(0, f'{name} (uid="{uid}", timestamp={timestamp})')

        motor_result = get_motor_position(uid=uid)

        # Add the motors as children
        for motor in motor_result.motors:
            motor_item = QtWidgets.QTreeWidgetItem(root)
            motor_item.setText(0, motor.name)
            motor_item.setText(1, f"{motor.readback}")
            motor_item.setText(2, f"{motor.offset}")

        # Expand all nodes
        tree.expandAll()

        # Set the layout and display the dialog
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.addWidget(tree)
        dialog.setLayout(layout)
        dialog.exec_()

    def on_regions_all_checkbox(self, is_checked):
        for region_i in self.regions:
            region_i.region_checkbox.setChecked(is_checked)

    def get_scan_parameters(self):
        # Get parameters from each row of line regions:
        motor_lst = []
        for region_i in self.regions:
            if region_i.region_checkbox.isChecked():
                motor_lst.append(region_i.motor_box.current_component().name)
        return motor_lst

    def get_current_selected_row(self):
        """Get the current selected row in the saved positions table."""
        row = self.ui.saved_positions_tableWidget.currentRow()
        if row < 0:
            self.ui.textBrowser.append("No saved motor positions selected.")
            return None, None

        # Get the name, uid, and other details for this row
        name = self.ui.saved_positions_tableWidget.item(row, 0).text()
        uid = self.ui.saved_positions_tableWidget.item(row, 2).text()
        return name, uid

    def recall_motor_queue_plan(self, run_now=False):
        """Recall motor positions plan and submit the plan to the queue server.

        Parameters:
            run_now (bool): If True, the plan will be executed immediately."""

        name, uid = self.get_current_selected_row()
        if not uid:
            return

        item = BPlan("recall_motor_position", uid=uid)

        # Provide feedback
        if run_now:
            self.ui.textBrowser.append("Executing recall of motor positions now.")
        else:
            self.ui.textBrowser.append("Added recall of motor positions to queue.")
        self.ui.textBrowser.append(
            f'<span style="color: blue;">Name: <strong>{name}</strong></span>'
        )
        self.ui.textBrowser.append("-" * 20)

        # Submit the item to the queueserver
        self.submit_queue_item(item, run_now=run_now)

    def recall_motor_queue_plan_now(self):
        """Recall motor positions plan. Execute now."""
        self.recall_motor_queue_plan(run_now=True)

    def queue_plan(self, run_now=False):
        """
        Save motor positions to the database and submit the plan to the queue server.

        Parameters:
            run_now (bool): If True, the plan will be executed immediately.
        """

        motor_args = self.get_scan_parameters()
        if not motor_args:
            self.ui.textBrowser.append(
                "No motors selected. Please select motors to save."
            )
            return
        save_name = self.ui.lineEdit_name.text()
        if not save_name:
            self.ui.textBrowser.append(
                "Please enter a name for the saved motor positions."
            )
            return
        item = BPlan(
            "save_motor_position",
            *motor_args,
            name=save_name,
        )
        # Submit the plan to the queue server
        self.submit_queue_item(item, run_now=run_now)
        if run_now:
            # Refresh the saved position list
            QtCore.QTimer.singleShot(0, self.refresh_saved_position_list_slot)
        # Disable the filter stop time to current
        self.ui.checkBox_stop.setChecked(False)
        self.ui.textBrowser.append("-" * 20)
        self.ui.textBrowser.append("Saving motor configurations: ")
        self.ui.textBrowser.append(
            f'<span style="color: blue;">Name: <strong>{save_name}</strong></span>'
        )

    def queue_plan_now(self):
        """Save motor positions to the database. Execute now."""
        self.queue_plan(run_now=True)

    def ui_filename(self):
        return "plans/save_motor_window.ui"

    def update_queue_status(self, status: Mapping):
        super().update_queue_status(status=status)
        self.ui.recall_button.update_queue_style(status)
        # Schedule the refresh after the event loop starts
        QtCore.QTimer.singleShot(0, self.refresh_saved_position_list_slot)


# -----------------------------------------------------------------------------
# :author:    Juanjuan Huang & Mark Wolfman
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
