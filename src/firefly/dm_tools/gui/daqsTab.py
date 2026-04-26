import logging

from dm.common.constants.dmExperimentConstants import DM_EXPERIMENT_NAME_KEY
from dm.common.constants.dmObjectLabels import DM_ID_KEY, DM_STATUS_KEY
from dm.common.constants.dmProcessingConstants import (
    DM_COUNT_FILES_KEY,
    DM_DATA_DIRECTORY_KEY,
    DM_N_PROCESSED_FILES_KEY,
    DM_N_PROCESSING_ERRORS_KEY,
    DM_N_WAITING_FILES_KEY,
    DM_PERCENTAGE_COMPLETE_KEY,
    DM_PROCESSING_ERRORS_KEY,
    DM_START_TIMESTAMP_KEY,
)
from dm.common.constants.dmProcessingStatus import (
    DM_ACTIVE_PROCESSING_STATUS_LIST,
    DM_INACTIVE_PROCESSING_STATUS_LIST,
    DM_PROCESSING_STATUS_DONE,
)
from dm.common.exceptions.communicationError import CommunicationError
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPalette
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from .apiFactory import ApiFactory
from .subclasses import customSelectionModel, customStyledDelegate
from .subclasses.style import (
    DM_FONT_ARIAL_KEY,
    DM_GUI_BROWN,
    DM_GUI_GOLD,
    DM_GUI_GREEN,
    DM_GUI_LIGHT_GREY,
    DM_GUI_RED,
    DM_GUI_WHITE,
)

log = logging.getLogger("dm_tools")


# Define the DAQs tab content:
class DaqsTab(QWidget):
    def __init__(self, stationName, parent, id=-1):
        super(DaqsTab, self).__init__(parent)
        self.stationName = stationName
        self.parent = parent
        self.showingDetails = 0
        self.experimentDaqApi = ApiFactory.getInstance().getExperimentDaqApi()
        self.daqsTabLayout()

    # GUI layout where each block is a row on the grid
    def daqsTabLayout(self):
        grid = QGridLayout()

        labelFont = QFont(DM_FONT_ARIAL_KEY, 18, QFont.Bold)
        lbl = QLabel(self.stationName + " DAQs List", self)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(labelFont)
        grid.addWidget(lbl, 0, 0, 1, 5)

        self.backBtn = QPushButton("Back", self)
        self.backBtn.setFocusPolicy(Qt.NoFocus)
        self.backBtn.clicked.connect(self.toggleDetails)
        self.backBtn.setMinimumWidth(100)
        self.backBtn.hide()
        grid.addWidget(self.backBtn, 0, 0, Qt.AlignLeft)

        self.refreshBtn = QPushButton("Refresh", self)
        self.refreshBtn.setFocusPolicy(Qt.NoFocus)
        self.refreshBtn.setToolTip("Automatically refreshes every 60 seconds.")
        self.refreshBtn.clicked.connect(self.parent.refreshTables)
        self.refreshBtn.setMinimumWidth(100)
        grid.addWidget(self.refreshBtn, 1, 4)

        grid.addItem(QSpacerItem(20, 30, QSizePolicy.Expanding), 2, 0)

        self.daqTable = QTableWidget()
        self.daqTable.clicked.connect(self.checkFail)
        self.daqTable.clicked.connect(self.enableDetails)
        self.daqTable.cellDoubleClicked.connect(self.toggleDetails)
        self.daqTable.setSelectionMode(QAbstractItemView.SingleSelection)
        self.daqTable.setItemDelegate(
            customStyledDelegate.CustomStyledDelegate(self.daqTable, self)
        )
        self.daqTable.setSelectionModel(
            customSelectionModel.CustomSelectionModel(self, self.daqTable.model())
        )

        self.detailsTable = QTableWidget()
        alternate = QPalette()
        alternate.setColor(QPalette.AlternateBase, DM_GUI_LIGHT_GREY)
        alternate.setColor(QPalette.Base, DM_GUI_WHITE)
        self.detailsTable.setAlternatingRowColors(True)
        self.detailsTable.setPalette(alternate)
        self.detailsTable.setItemDelegate(
            customStyledDelegate.CustomStyledDelegate(self.detailsTable, self)
        )
        self.detailsTable.setSelectionModel(
            customSelectionModel.CustomSelectionModel(self, self.detailsTable.model())
        )
        grid.addWidget(self.detailsTable, 3, 0, 1, 5)
        grid.addWidget(self.daqTable, 3, 0, 1, 5)

        self.addBtn = QPushButton("Start New", self)
        self.addBtn.setFocusPolicy(Qt.NoFocus)
        self.addBtn.clicked.connect(lambda: self.parent.tabs.setCurrentIndex(0))
        self.addBtn.setMaximumWidth(130)

        self.detailBtn = QPushButton("Show Details", self)
        self.detailBtn.setFocusPolicy(Qt.NoFocus)
        self.detailBtn.clicked.connect(self.toggleDetails)
        self.detailBtn.setMaximumWidth(130)

        self.clearBtn = QPushButton("Clear Selected", self)
        self.clearBtn.setFocusPolicy(Qt.NoFocus)
        self.clearBtn.clicked.connect(self.clearDaq)
        self.clearBtn.setMaximumWidth(130)

        self.stopBtn = QPushButton("Stop Selected", self)
        self.stopBtn.setFocusPolicy(Qt.NoFocus)
        self.stopBtn.clicked.connect(self.stopDaq)
        self.stopBtn.setMaximumWidth(130)

        hbox1 = QHBoxLayout()
        hbox1.addWidget(self.addBtn)
        hbox1.addWidget(self.detailBtn)
        hbox1.addWidget(self.clearBtn)
        hbox1.addWidget(self.stopBtn)

        grid.addLayout(hbox1, 4, 0, 1, 5)

        grid.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding), 5, 0)

        self.setLayout(grid)
        self.updateList()

    # Fills the table with the daqs from experimentDaqApi
    def updateList(self):
        if self.detailBtn.text() == "Hide Details":
            self.refreshBtn.setEnabled(False)
            self.stopBtn.setEnabled(False)
            self.clearBtn.setEnabled(False)
            self.daqTable.hide()
            self.daqDetails()
            self.detailsTable.show()
        else:
            self.clearBtn.setEnabled(False)
            self.stopBtn.setEnabled(False)
            self.detailBtn.setEnabled(False)
        self.daqTable.setSortingEnabled(False)
        self.daqTable.clearSelection()
        try:
            self.daqList = self.experimentDaqApi.listDaqs()
        except CommunicationError as exc:
            log.error(exc)
            self.daqList = []
        self.daqTable.setRowCount(len(self.daqList))
        self.daqTable.setColumnCount(8)
        self.daqTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.daqTable.setSelectionMode(QAbstractItemView.SingleSelection)
        self.daqTable.setHorizontalHeaderLabels(
            "Name;Status;Start Date;Files;Processed;Waiting;Errors;% Completed;".split(
                ";"
            )
        )
        self.daqTable.horizontalHeader().setStretchLastSection(True)

        i = 0
        for daq in self.daqList:
            rowName = QTableWidgetItem(daq.get(DM_EXPERIMENT_NAME_KEY))
            rowName.setData(Qt.UserRole, daq.get(DM_ID_KEY))
            rowStatus = QTableWidgetItem(daq.get(DM_STATUS_KEY))
            rowSDate = QTableWidgetItem(daq.get(DM_START_TIMESTAMP_KEY)[:10])
            rowFileNum = QTableWidgetItem(str(daq.get(DM_COUNT_FILES_KEY)))
            rowCompleted = QTableWidgetItem(str(daq.get(DM_N_PROCESSED_FILES_KEY)))
            rowWaiting = QTableWidgetItem(str(daq.get(DM_N_WAITING_FILES_KEY)))
            rowErrors = QTableWidgetItem(str(daq.get(DM_N_PROCESSING_ERRORS_KEY)))
            rowPerCompleted = QTableWidgetItem(str(daq.get(DM_PERCENTAGE_COMPLETE_KEY)))
            rowDataDir = str(daq.get(DM_DATA_DIRECTORY_KEY))
            if len(rowDataDir) > 100:
                for j in range(len(rowDataDir)):
                    if j % 50 == 0 and j != 0:
                        rowDataDir = rowDataDir[:j] + " " + rowDataDir[j:]
            rowDataDir = QTableWidgetItem(rowDataDir)
            columns = [
                rowName,
                rowStatus,
                rowSDate,
                rowFileNum,
                rowCompleted,
                rowWaiting,
                rowErrors,
                rowPerCompleted,
            ]
            for j in range(len(columns)):
                self.daqTable.setItem(i, j, columns[j])

            errors = daq.get(DM_PROCESSING_ERRORS_KEY)
            rowColor = DM_GUI_GOLD
            if rowStatus.text() == DM_PROCESSING_STATUS_DONE:
                rowColor = DM_GUI_GREEN
            elif rowStatus.text() in DM_ACTIVE_PROCESSING_STATUS_LIST:
                if errors:
                    rowColor = DM_GUI_BROWN
                else:
                    rowColor = DM_GUI_GOLD
            elif rowStatus.text() in DM_INACTIVE_PROCESSING_STATUS_LIST:
                # already checked for 'done', so other inactive statuses are failures
                rowColor = DM_GUI_RED
            for column in columns:
                column.setBackground(rowColor)

            i += 1
        self.daqTable.setSortingEnabled(True)

    # Expands the targetted row to fit contents when doubleclicked
    def expandRow(self, row, column):
        self.detailsTable.resizeRowToContents(row)

    # Stops the daq that is selected
    def stopDaq(self):
        id = self.daqTable.item(self.daqTable.currentRow(), 0).data(Qt.UserRole)
        allInfo = self.experimentDaqApi.getDaqInfo(id)
        self.experimentDaqApi.stopDaq(
            allInfo[DM_EXPERIMENT_NAME_KEY], allInfo[DM_DATA_DIRECTORY_KEY]
        )
        self.updateList()

    # Clears the history of the daq from the DB and refreshes the table
    def clearDaq(self):
        id = self.daqTable.item(self.daqTable.currentRow(), 0).data(Qt.UserRole)
        self.experimentDaqApi.clearDaq(id)
        self.parent.refreshTables()
        self.daqTable.clearSelection()

    # Toggles to show/hide the details table of the thing that is selected
    def toggleDetails(self):
        if self.showingDetails == 1:
            self.detailsTable.clearFocus()
            self.detailsTable.clearSelection()
            self.refreshBtn.show()
            self.checkFail()
            self.daqTable.show()
            self.detailsTable.hide()
            self.detailBtn.show()
            self.backBtn.hide()
            self.addBtn.show()
            self.clearBtn.show()
            self.detailBtn.show()
            self.stopBtn.show()
            self.showingDetails = 0
        else:
            self.refreshBtn.hide()
            self.daqTable.setSelectionMode(QAbstractItemView.NoSelection)
            self.daqTable.hide()
            self.daqTable.setSelectionMode(QAbstractItemView.SingleSelection)
            self.daqDetails()
            self.detailsTable.show()
            self.detailBtn.hide()
            self.backBtn.show()
            self.addBtn.hide()
            self.clearBtn.hide()
            self.detailBtn.hide()
            self.stopBtn.hide()
            self.showingDetails = 1

    def daqDetails(self):
        self.detailsTable.setSortingEnabled(False)
        id = self.daqTable.item(self.daqTable.currentRow(), 0).data(Qt.UserRole)
        self.daqTable.clearFocus()
        allInfo = self.experimentDaqApi.getDaqInfo(id)

        self.detailsTable.setRowCount(len(allInfo.data))
        self.detailsTable.setColumnCount(2)
        self.detailsTable.setSelectionMode(QAbstractItemView.SingleSelection)
        self.detailsTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.detailsTable.setHorizontalHeaderLabels("Parameter;Value".split(";"))
        self.detailsTable.horizontalHeader().setStretchLastSection(True)

        i = 0
        for parameter in allInfo.data:
            paramName = QTableWidgetItem(parameter)
            valStr = str(allInfo.data[parameter])
            if len(valStr) > 150:
                for j in range(len(valStr)):
                    if j % 50 == 0 and j != 0:
                        valStr = valStr[:j] + " " + valStr[j:]
            paramValue = QTableWidgetItem(valStr)
            self.detailsTable.setItem(i, 0, paramName)
            self.detailsTable.setItem(i, 1, paramValue)
            i += 1
        self.detailsTable.setSortingEnabled(True)

    # Disables the stop daq button if the daq has already failed or stopped.
    def checkFail(self):
        if (
            self.daqTable.item(self.daqTable.currentRow(), 1).text()
            in DM_ACTIVE_PROCESSING_STATUS_LIST
        ):
            self.stopBtn.setEnabled(True)
            self.clearBtn.setEnabled(False)
        else:
            self.stopBtn.setEnabled(False)
            self.clearBtn.setEnabled(True)

    # Enables the detail button when the table is selected
    def enableDetails(self):
        self.detailBtn.setEnabled(True)

    # Manually updates the tableView
    def updateView(self, index):
        if self.daqTable.isVisible():
            self.daqTable.update(index)
        else:
            self.detailsTable.update(index)

    # Returns the tables on this tab
    def getTables(self):
        tables = [self.daqTable, self.detailsTable]
        return tables

    # Signals the parent to handle the right click event
    def contextMenuEvent(self, event):
        if self.daqTable.isVisible():
            self.parent.handleRightClickMenu(
                self.daqTable, event, toggleDetailsAction=self.toggleDetails
            )
        else:
            self.parent.handleRightClickMenu(self.detailsTable, event)
