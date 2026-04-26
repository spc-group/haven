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


# Define the experiments tab content:
class UploadsTab(QWidget):
    def __init__(self, stationName, parent, id=-1):
        super(UploadsTab, self).__init__(parent)
        self.stationName = stationName
        self.parent = parent
        self.showingDetails = 0
        self.experimentDaqApi = ApiFactory.getInstance().getExperimentDaqApi()
        self.uploadTabLayout()

    # GUI layout where each block is a row on the grid
    def uploadTabLayout(self):
        grid = QGridLayout()

        labelFont = QFont(DM_FONT_ARIAL_KEY, 18, QFont.Bold)
        lbl = QLabel(self.stationName + " Uploads List", self)
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

        self.tableWidget = QTableWidget()
        self.tableWidget.clicked.connect(self.checkFail)
        self.tableWidget.clicked.connect(self.enableDetails)
        self.tableWidget.cellDoubleClicked.connect(self.toggleDetails)
        self.tableWidget.setItemDelegate(
            customStyledDelegate.CustomStyledDelegate(self.tableWidget, self)
        )
        self.tableWidget.setSelectionModel(
            customSelectionModel.CustomSelectionModel(self, self.tableWidget.model())
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
        grid.addWidget(self.tableWidget, 3, 0, 1, 5)

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
        self.clearBtn.clicked.connect(self.clearUpload)
        self.clearBtn.setMaximumWidth(130)

        self.stopBtn = QPushButton("Stop Selected", self)
        self.stopBtn.setFocusPolicy(Qt.NoFocus)
        self.stopBtn.clicked.connect(self.stopUpload)
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

    # Populates the table with the uploads from experimentDaqApi
    def updateList(self):
        if self.detailBtn.text() == "Hide Details":
            self.refreshBtn.setEnabled(False)
            self.stopBtn.setEnabled(False)
            self.clearBtn.setEnabled(False)
            self.tableWidget.hide()
            self.uploadDetails()
            self.detailsTable.show()
        else:
            self.clearBtn.setEnabled(False)
            self.stopBtn.setEnabled(False)
            self.detailBtn.setEnabled(False)
        self.tableWidget.setSortingEnabled(False)
        self.tableWidget.clearSelection()
        try:
            self.uploadList = self.experimentDaqApi.listUploads()
        except CommunicationError as exc:
            log.error(exc)
            self.uploadList = []
        self.tableWidget.setRowCount(len(self.uploadList))
        self.tableWidget.setColumnCount(8)
        self.tableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tableWidget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tableWidget.setHorizontalHeaderLabels(
            "Name;Status;Start Date;Files;Processed;Waiting;Errors;% Completed;".split(
                ";"
            )
        )
        self.tableWidget.horizontalHeader().setStretchLastSection(True)

        i = 0
        for upload in self.uploadList:
            rowName = QTableWidgetItem(upload.get(DM_EXPERIMENT_NAME_KEY))
            rowName.setData(Qt.UserRole, upload.get(DM_ID_KEY))
            rowStatus = QTableWidgetItem(upload.get(DM_STATUS_KEY))
            rowSDate = QTableWidgetItem(upload.get(DM_START_TIMESTAMP_KEY)[:10])
            rowFileNum = QTableWidgetItem(str(upload.get(DM_COUNT_FILES_KEY)))
            rowCompleted = QTableWidgetItem(str(upload.get(DM_N_PROCESSED_FILES_KEY)))
            rowWaiting = QTableWidgetItem(str(upload.get(DM_N_WAITING_FILES_KEY)))
            rowErrors = QTableWidgetItem(str(upload.get(DM_N_PROCESSING_ERRORS_KEY)))
            rowPerCompleted = QTableWidgetItem(
                str(upload.get(DM_PERCENTAGE_COMPLETE_KEY))
            )
            rowDataDir = str(upload.get(DM_DATA_DIRECTORY_KEY))
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
                self.tableWidget.setItem(i, j, columns[j])

            errors = upload.get(DM_PROCESSING_ERRORS_KEY)
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
        self.tableWidget.setSortingEnabled(True)

    # Expands the selected row to fit contents
    def expandRow(self, row, column):
        self.detailsTable.resizeRowToContents(row)

    # Stops the upload that is currently selected
    def stopUpload(self):
        id = self.tableWidget.item(self.tableWidget.currentRow(), 0).data(Qt.UserRole)
        self.experimentDaqApi.stopUpload(id)
        self.updateList()

    # Clears the history of the upload from the DB and refreshes the table
    def clearUpload(self):
        id = self.tableWidget.item(self.tableWidget.currentRow(), 0).data(Qt.UserRole)
        self.experimentDaqApi.clearUpload(id)
        self.parent.refreshTables()
        self.tableWidget.clearSelection()

    # Toggles to show/hide the details table of the thing that is selected
    def toggleDetails(self):
        tableView = [
            self.refreshBtn,
            self.tableWidget,
            self.detailBtn,
            self.clearBtn,
            self.detailBtn,
            self.stopBtn,
            self.addBtn,
        ]
        detailView = [self.detailsTable, self.backBtn]

        if self.showingDetails:
            show = tableView
            hide = detailView
            self.detailsTable.clearFocus()
            self.detailsTable.clearSelection()
            self.checkFail()
        else:
            show = detailView
            hide = tableView
            self.stopBtn.setEnabled(False)
            self.clearBtn.setEnabled(False)
            self.tableWidget.setSelectionMode(QAbstractItemView.NoSelection)
            self.tableWidget.setSelectionMode(QAbstractItemView.SingleSelection)
            self.uploadDetails()

        for s in show:
            s.show()
        for h in hide:
            h.hide()
        self.showingDetails = not self.showingDetails

    def uploadDetails(self):
        self.detailsTable.setSortingEnabled(False)
        id = self.tableWidget.item(self.tableWidget.currentRow(), 0).data(Qt.UserRole)
        self.tableWidget.clearFocus()
        allInfo = self.experimentDaqApi.getUploadInfo(id)

        self.detailsTable.setRowCount(len(allInfo.data))
        self.detailsTable.setColumnCount(2)
        self.detailsTable.setSelectionMode(QAbstractItemView.SingleSelection)
        self.detailsTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.detailsTable.setHorizontalHeaderLabels("Parameter;Value".split(";"))
        self.detailsTable.cellDoubleClicked.connect(self.expandRow)
        self.detailsTable.horizontalHeader().setStretchLastSection(True)

        i = 0
        for parameter in allInfo.data:
            rowName = QTableWidgetItem(parameter)
            valStr = str(allInfo.data[parameter])
            if len(valStr) > 150:
                for j in range(len(valStr)):
                    if j % 50 == 0 and j != 0:
                        valStr = valStr[:j] + " " + valStr[j:]
            rowValue = QTableWidgetItem(valStr)
            self.detailsTable.setItem(i, 0, rowName)
            self.detailsTable.setItem(i, 1, rowValue)
            i += 1
        self.detailsTable.setSortingEnabled(True)

    # Disables the stop upload button if the daq has already failed or stopped.
    def checkFail(self):
        if (
            self.tableWidget.item(self.tableWidget.currentRow(), 1).text()
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
        if self.tableWidget.isVisible():
            self.tableWidget.update(index)
        else:
            self.detailsTable.update(index)

    # Returns the tables on this tab
    def getTables(self):
        tables = [self.tableWidget, self.detailsTable]
        return tables

    # Signals the parent to handle the right click event
    def contextMenuEvent(self, event):
        if self.tableWidget.isVisible():
            self.parent.handleRightClickMenu(
                self.tableWidget, event, toggleDetailsAction=self.toggleDetails
            )
        else:
            self.parent.handleRightClickMenu(self.detailsTable, event)
