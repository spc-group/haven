import logging

from bluesky_queueserver_api import BPlan
from pydm.widgets.label import PyDMLabel
from pymongo import MongoClient
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QDateTime
from datetime import datetime

from qtpy import QtWidgets
from firefly.component_selector import ComponentSelector
from firefly.plans import regions_display
from haven import (
    get_motor_position,
    list_motor_positions,
    save_motor_position,
    recall_motor_position,
)
import qtawesome as qta

log = logging.getLogger()


test = True
if test:
    # Connect to MongoDB for testing
    client = MongoClient('mongodb://localhost:27017/')
    mongodb = client['test_db'] 
    collection = mongodb['multiple_motors_positions']

else: 
    collection = None
    
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

        labels = ["Motor", "RBV"]

        Qlabels_all = {}
        for label_i in labels:
            Qlabel_i = QtWidgets.QLabel(label_i)
            self.layout.addWidget(Qlabel_i)
            Qlabels_all[label_i] = Qlabel_i

        # fix widths so the labels are aligned with MotorRegions
        Qlabels_all["RBV"].setFixedWidth(60)

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
        self.update_RBV()
        self.layout.addWidget(self.RBV_label)
        
        # update RBV when motor is changed
        self.motor_box.combo_box.currentTextChanged.connect(self.update_RBV)

        # Disable/enable regions when uncheck/check region checkboxs
        self.region_checkbox.stateChanged.connect(self.on_region_checkbox)

    def on_region_checkbox(self, is_checked):
        # disable/enable motor box and RBV label
        self.motor_box.setEnabled(is_checked)
        self.RBV_label.setEnabled(is_checked)
    
    def update_RBV(self):
        try:
            motor = self.motor_box.current_component()
            if motor:
                self.RBV_label = PyDMLabel(self, init_channel=f"haven://{motor.name}.user_readback")
            else:
                raise Exception("No motor selected")

        except Exception as e:
            print(e)
            self.RBV_label = PyDMLabel("nan")

class SaveMotorDisplay(regions_display.RegionsDisplay):
    Region = MotorRegion
    default_num_regions = 1

    def customize_ui(self):
        super().customize_ui()
        
        # add title layout
        self.title_region = TitleRegion()
        self.ui.title_layout.addLayout(self.title_region.layout)
        
        # connect buttons
        self.ui.save_button.clicked.connect(self.save_motors)
        
        # init saved positions table
        self.init_saved_positions_table()
        
        # connect checkboxes with all regions' check box
        self.title_region.regions_all_checkbox.stateChanged.connect(
            self.on_regions_all_checkbox
        )
        self.ui.refresh_button.setIcon(qta.icon("fa5s.sync-alt"))
        

    def init_saved_positions_table(self):
        # Set the headers for the table
        self.ui.saved_positions_tableWidget.setHorizontalHeaderLabels(["Name", "Savetime", "UID"])

        # connect double click to show saved position info
        self.ui.saved_positions_tableWidget.itemDoubleClicked.connect(self.show_saved_position_info)
        
        # set selection behavior to select rows rather than individual cells
        self.ui.saved_positions_tableWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        # refresh saved list
        self.ui.refresh_button.clicked.connect(self.refresh_saved_position_list)
        self.refresh_saved_position_list()
        
        # connect filter button to filter dates and names
        self.ui.pushButton_filter.clicked.connect(self.filter_dates_and_names)
        
    def refresh_saved_position_list(self):
        # Disable sorting temporarily to prevent UID missing bug
        self.ui.saved_positions_tableWidget.setSortingEnabled(False)

        # Clear the existing rows in the table
        self.ui.saved_positions_tableWidget.setRowCount(0)

        # Retrieve the saved positions
        saved_positions_all = list_motor_positions(collection=collection, printit=False)
        
        for saved_position_i in saved_positions_all:
            current_row_position = self.ui.saved_positions_tableWidget.rowCount()
            self.ui.saved_positions_tableWidget.insertRow(current_row_position)

            # Format the savetime
            savetime_str = datetime.fromtimestamp(saved_position_i.savetime).strftime('%Y-%m-%d %H:%M:%S')

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
        
        # Set filter name to empty
        self.ui.lineEdit_filter_names.setText("")
        
        # Set default filter dates if there are items in the table
        if saved_positions_all:
            last_savetime = saved_positions_all[-1].savetime
            first_savetime = saved_positions_all[0].savetime
            
            # Convert to QDateTime and set to dateEdits
            self.ui.dateEdit_start.setDateTime(datetime.fromtimestamp(first_savetime))
            self.ui.dateEdit_stop.setDateTime(datetime.fromtimestamp(last_savetime))

    def filter_dates_and_names(self):
        # Get the start and stop dates from the date edits
        start_date = self.ui.dateEdit_start.date().toPyDate()
        stop_date = self.ui.dateEdit_stop.date().toPyDate()
        
        # Get the filter text from the line edit, remove spaces, and convert to lowercase
        filter_text = self.ui.lineEdit_filter_names.text().replace(" ", "").strip().lower()

        # Loop through each row in the table and filter out rows outside the date range
        for row in range(self.ui.saved_positions_tableWidget.rowCount()):
            # Get the savetime from the table
            savetime_item = self.ui.saved_positions_tableWidget.item(row, 1)
            savetime_str = savetime_item.text()
            savetime_date = datetime.strptime(savetime_str, '%Y-%m-%d %H:%M:%S').date()
            
            # Get the name from the table and convert to lowercase
            name_item = self.ui.saved_positions_tableWidget.item(row, 0)
            name_text = name_item.text().strip().lower()

            # Check if the savetime date is within the specified range and the name contains the filter text
            if start_date <= savetime_date <= stop_date and filter_text in name_text:
                self.ui.saved_positions_tableWidget.setRowHidden(row, False)
            else:
                self.ui.saved_positions_tableWidget.setRowHidden(row, True)
                
    def show_saved_position_info(self, item):
        # Get the row of the clicked item
        row = self.ui.saved_positions_tableWidget.row(item)
        
        # Get the name, uid, and other details for this row
        name = self.ui.saved_positions_tableWidget.item(row, 0).text()
        uid = self.ui.saved_positions_tableWidget.item(row, 2).text()
        
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
        root.setText(0, f'{name} (uid="{uid}", timestamp={self.ui.saved_positions_tableWidget.item(row, 1).text()})')
        
        motor_result = get_motor_position(uid=uid, collection=collection)
        
        # Add the motors as children
        for motor in motor_result.motors:
            motor_item = QtWidgets.QTreeWidgetItem(root)
            motor_item.setText(0, motor.name)
            motor_item.setText(1, f'{motor.readback}')
            motor_item.setText(2, f'{motor.offset}')

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
        # get paramters from each rows of line regions:
        motor_lst = []
        for region_i in self.regions:
            if region_i.region_checkbox.isChecked():
                motor_lst.append(region_i.motor_box.current_component().name)
        return motor_lst

    def save_motors(self, *args, **kwargs):
        """Save motor positions to the database."""
        motor_args = self.get_scan_parameters()
        
        if not motor_args:
            self.ui.textBrowser.append("No motors selected. Please select motors to save.")
            return  
        
        save_name = self.ui.lineEdit_name.text()
        if not save_name:
            self.ui.textBrowser.append("Please enter a name for the saved motor positions.")
            return
        
        pos_id = save_motor_position(
            *motor_args,
            name=save_name,
            collection=collection, 
        )
        
        # refresh after saving a new position
        self.refresh_saved_position_list()
        
        # set the filter stop time to current
        self.ui.dateEdit_stop.setDateTime(QDateTime.currentDateTime())

        self.ui.textBrowser.append("-" * 20)
        self.ui.textBrowser.append("Saving motor configurations: ")
        self.ui.textBrowser.append(
            f'<span style="color: red;">Name: <strong>{save_name}</strong></span>'
        )
        self.ui.textBrowser.append(
            f'<span style="color: blue;">UID: <strong>{pos_id}</strong></span>'
        )
        return pos_id


    def get_current_selected_row(self):
        """Get the current selected row in the saved positions table."""

        # get the current selected row
        row = self.ui.saved_positions_tableWidget.currentRow()
        # Get the name, uid, and other details for this row
        name = self.ui.saved_positions_tableWidget.item(row, 0).text()
        uid = self.ui.saved_positions_tableWidget.item(row, 2).text()    
        return name, uid
    
    def queue_plan(self, *args, **kwargs):
        """Execute this plan on the queueserver."""
        if test:
            self.ui.run_button.setEnabled(True)

        name, uid = self.get_current_selected_row()
        
        if not uid:
            self.ui.textBrowser.append("No saved motor positions selected.")
            return
        
        plan = recall_motor_position(uid=uid, collection=collection)
        # send a message to the text browser
        self.show_message(f"Recalling motor configurations: {name}: {uid}")
        self.ui.textBrowser.append("-" * 20)
        self.ui.textBrowser.append(f"Queuing selected motor configurations {name}: {uid}")
        
        # Submit the item to the queueserver
        log.info("Added line scan() plan to queue.")
        self.queue_item_submitted.emit(plan)

    def ui_filename(self):
        return "plans/save_motor_window.ui"
    
    # add a filter field for dates
    

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