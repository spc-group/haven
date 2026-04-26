import logging

from dm.common.constants.dmObjectLabels import DM_ID_KEY, DM_STATUS_KEY
from dm.common.constants.dmProcessingConstants import (
    DM_END_TIMESTAMP_KEY,
    DM_RUN_TIME_KEY,
    DM_STAGE_KEY,
    DM_START_TIMESTAMP_KEY,
)
from dm.common.constants.dmProcessingStatus import (
    DM_PROCESSING_STATUS_DONE,
    DM_PROCESSING_STATUS_FAILED,
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
    DM_GUI_GOLD,
    DM_GUI_GREEN,
    DM_GUI_LIGHT_GREY,
    DM_GUI_RED,
    DM_GUI_WHITE,
)

log = logging.getLogger("dm_tools")


# Define the Processing Jobs tab content:
class ProcessingJobsTab(QWidget):

    # Model constants
    SGE_JOB_NAME_KEY = "sgeJobName"
    SGE_JOB_ID_KEY = "sgeJobId"

    COLUMN_ORDER_KEY_LIST = [
        DM_START_TIMESTAMP_KEY,
        DM_END_TIMESTAMP_KEY,
        SGE_JOB_NAME_KEY,
        DM_STATUS_KEY,
        DM_STAGE_KEY,
        DM_RUN_TIME_KEY,
        DM_ID_KEY,
    ]

    COLUMN_DISPLAY_NAME = {
        DM_START_TIMESTAMP_KEY: "Start Time",
        DM_END_TIMESTAMP_KEY: "End Time",
        SGE_JOB_NAME_KEY: "Job Name",
        SGE_JOB_ID_KEY: "SGE Id",
        DM_STATUS_KEY: "Status",
        DM_STAGE_KEY: "Stage",
        DM_RUN_TIME_KEY: "Run Time",
        DM_ID_KEY: "Id",
    }

    DONE_COLOR = DM_GUI_GREEN
    EXECUTING_COLOR = DM_GUI_GOLD
    FAILED_COLOR = DM_GUI_RED

    def __init__(self, stationName, parent, id=-1):
        super(ProcessingJobsTab, self).__init__(parent)
        self.stationName = stationName
        self.parent = parent
        self.showingDetails = 0

        self.workflowApi = ApiFactory.getInstance().getWorkflowApi()

        self.processingJobsLayout()

    # GUI layout where each block is a row on the grid
    def processingJobsLayout(self):
        grid = QGridLayout()

        labelFont = QFont(DM_FONT_ARIAL_KEY, 18, QFont.Bold)
        lbl = QLabel(self.parent.username + " Processing Jobs List", self)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(labelFont)
        grid.addWidget(lbl, 0, 0, 1, 5)

        self.backBtn = QPushButton("Back", self)
        self.backBtn.clicked.connect(self.toggleDetails)
        self.backBtn.setFocusPolicy(Qt.NoFocus)
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

        alternate = QPalette()
        alternate.setColor(QPalette.AlternateBase, DM_GUI_LIGHT_GREY)
        alternate.setColor(QPalette.Base, DM_GUI_WHITE)

        self.processingJobsTable = QTableWidget()
        self.processingJobsTable.clicked.connect(self.enableDetails)
        self.processingJobsTable.doubleClicked.connect(self.toggleDetails)
        self.processingJobsTable.setItemDelegate(
            customStyledDelegate.CustomStyledDelegate(self.processingJobsTable, self)
        )
        self.processingJobsTable.setSelectionModel(
            customSelectionModel.CustomSelectionModel(
                self, self.processingJobsTable.model()
            )
        )
        grid.addWidget(self.processingJobsTable, 3, 0, 1, 5)

        self.detailsTable = QTableWidget()
        self.detailsTable.setAlternatingRowColors(True)
        self.detailsTable.setPalette(alternate)
        self.detailsTable.doubleClicked.connect(self.expandRow)
        self.detailsTable.hide()
        self.detailsTable.setItemDelegate(
            customStyledDelegate.CustomStyledDelegate(self.detailsTable, self)
        )
        self.detailsTable.setSelectionModel(
            customSelectionModel.CustomSelectionModel(self, self.detailsTable.model())
        )
        grid.addWidget(self.detailsTable, 3, 0, 1, 5)

        self.detailBtn = QPushButton("Show Details", self)
        self.detailBtn.clicked.connect(self.toggleDetails)
        self.detailBtn.setFocusPolicy(Qt.NoFocus)
        self.detailBtn.setMaximumWidth(130)

        hbox1 = QHBoxLayout()
        hbox1.addWidget(self.detailBtn)

        grid.addLayout(hbox1, 4, 0, 1, 5)
        grid.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding), 5, 0)

        self.setLayout(grid)
        self.updateList()

    def updateList(self):
        self.detailBtn.setEnabled(False)
        self.processingJobsTable.setColumnCount(len(self.COLUMN_ORDER_KEY_LIST))
        self.processingJobsTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.processingJobsTable.setSelectionMode(QAbstractItemView.SingleSelection)

        headerLabels = []
        for key in self.COLUMN_ORDER_KEY_LIST:
            headerLabels.append(self.COLUMN_DISPLAY_NAME[key])

        self.processingJobsTable.setHorizontalHeaderLabels(headerLabels)
        self.processingJobsTable.horizontalHeader().setStretchLastSection(True)

        try:
            jobs = self.workflowApi.listProcessingJobs(
                keyList=self.COLUMN_ORDER_KEY_LIST
            )
        except CommunicationError as exc:
            log.error(exc)
            jobs = []
        self.processingJobsTable.setRowCount(len(jobs))

        for rowIndex, processingJob in enumerate(jobs):
            status = str(processingJob.get(DM_STATUS_KEY))
            color = self.EXECUTING_COLOR
            if status == DM_PROCESSING_STATUS_DONE:
                color = self.DONE_COLOR
            elif status == DM_PROCESSING_STATUS_FAILED:
                color = self.FAILED_COLOR

            for columnIndex, processingJobKey in enumerate(self.COLUMN_ORDER_KEY_LIST):
                value = str(processingJob.get(processingJobKey))
                if value is None:
                    value = ""
                columnObj = QTableWidgetItem(value)
                columnObj.setBackground(color)
                self.processingJobsTable.setItem(rowIndex, columnIndex, columnObj)

        self.processingJobsTable.setSortingEnabled(True)

    # Toggles to show/hide the details table of the thing that is selected
    def toggleDetails(self):
        if self.showingDetails == 1:
            self.detailsTable.clearFocus()
            self.detailsTable.clearSelection()
            self.processingJobsTable.show()
            self.detailsTable.hide()
            self.detailBtn.show()
            self.backBtn.hide()
            self.showingDetails = 0
        else:
            self.showDetails()
            self.processingJobsTable.clearFocus()
            self.processingJobsTable.clearSelection()
            self.processingJobsTable.hide()
            self.detailsTable.show()
            self.detailBtn.hide()
            self.backBtn.show()
            self.showingDetails = 1

    # Set up the details table for the selected workflow
    def showDetails(self):
        self.detailsTable.setSortingEnabled(False)
        idIdx = self.COLUMN_ORDER_KEY_LIST.index(self.ID_KEY)
        id = str(
            self.processingJobsTable.item(
                self.processingJobsTable.currentRow(), idIdx
            ).text()
        )
        self.processingJobsTable.clearFocus()
        currentProcessingJob = self.workflowApi.getProcessingJobById(
            self.parent.username, id
        )

        rowCount = len(currentProcessingJob.data)
        self.detailsTable.setRowCount(rowCount)

        self.detailsTable.setColumnCount(2)
        self.detailsTable.setSelectionMode(QAbstractItemView.SingleSelection)
        self.detailsTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.detailsTable.setHorizontalHeaderLabels("Key;Value;".split(";"))
        self.detailsTable.horizontalHeader().setStretchLastSection(True)
        print("currentProcessingJob.items() %s" % currentProcessingJob.items())
        for rowIndex, key_val in enumerate(currentProcessingJob.items()):
            for colIndex, colVal in enumerate(key_val):
                colVal = str(colVal)
                print("colVal %s" % colVal)
                column = QTableWidgetItem(colVal)
                self.detailsTable.setItem(rowIndex, colIndex, column)

        self.detailsTable.setSortingEnabled(True)

    # Manually updates the tableView
    def updateView(self, index):
        if self.processingJobsTable.isVisible():
            self.processingJobsTable.update(index)
        else:
            self.detailsTable.update(index)

    # Enables the detail button when the table is selected
    def enableDetails(self):
        self.detailBtn.setEnabled(True)

    # Returns the tables on this tab
    def getTables(self):
        tables = [self.workFlowTable, self.detailsTable]
        return tables

    # Expands the targetted row to fit contents when doubleclicked
    def expandRow(self, index):
        self.detailsTable.resizeRowToContents(index.row())
