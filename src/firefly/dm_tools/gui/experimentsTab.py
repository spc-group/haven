import logging
from datetime import datetime
from re import search

from dm.common.constants.dmExperimentConstants import (
    DM_END_DATE_KEY,
    DM_EXPERIMENT_TYPE_KEY,
    DM_EXPERIMENT_USERNAME_LIST_KEY,
    DM_START_DATE_KEY,
)
from dm.common.constants.dmObjectLabels import (
    DM_DESCRIPTION_KEY,
    DM_ID_KEY,
    DM_NAME_KEY,
)
from dm.common.utility.timeUtility import TimeUtility
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QFont, QPalette
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from ..common.dataTransferMonitor import DataTransferMonitor
from ..common.experimentDeleter import ExperimentDeleter
from .apiFactory import ApiFactory
from .objects.userInfo import UserInfo
from .subclasses import customSelectionModel, customStyledDelegate
from .subclasses.style import DM_FONT_ARIAL_KEY, DM_GUI_LIGHT_GREY, DM_GUI_WHITE

log = logging.getLogger("dm_tools")


# Define the experiments tab content:
class ExperimentsTab(QWidget):

    def __init__(self, stationName, parent, id=-1):
        super(ExperimentsTab, self).__init__(parent)
        self.stationName = stationName
        self.parent = parent
        self.experimentDsApi = ApiFactory.getInstance().getExperimentDsApi()
        self.userApi = ApiFactory.getInstance().getUserDsApi()
        self.fileCatApi = ApiFactory.getInstance().getFileCatApi()
        self.dataTransferMonitor = DataTransferMonitor(
            experimentDaqApi=ApiFactory.getInstance().getExperimentDaqApi()
        )
        self.experimentDeleter = ExperimentDeleter(
            dataTransferMonitor=self.dataTransferMonitor,
            experimentDsApi=self.experimentDsApi,
            fileCatApi=self.fileCatApi,
            stationName=self.stationName,
        )
        self.experimentsTabLayout()

    # Sets up the tab's layout, each block is a row
    def experimentsTabLayout(self):
        grid = QGridLayout()
        self.dialog = None  # reference for dialogs

        labelFont = QFont(DM_FONT_ARIAL_KEY, 18, QFont.Bold)
        lbl = QLabel(self.stationName + " DM Experiment List", self)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(labelFont)
        grid.addWidget(lbl, 0, 0, 1, 5)

        self.refBtn = QPushButton("Refresh", self)
        self.refBtn.setFocusPolicy(Qt.NoFocus)
        self.refBtn.setToolTip("Automatically refreshes every 60 seconds.")
        self.refBtn.clicked.connect(self.parent.refreshTables)
        self.refBtn.setMinimumWidth(100)
        grid.addWidget(self.refBtn, 1, 4, Qt.AlignCenter)

        grid.addItem(QSpacerItem(20, 30, QSizePolicy.Expanding), 2, 0)

        self.tableWidget = QTableWidget()
        self.tableWidget.cellDoubleClicked.connect(self.setExperiment)
        self.tableWidget.clicked.connect(self.enableButtons)
        self.tableWidget.setItemDelegate(
            customStyledDelegate.CustomStyledDelegate(self.tableWidget, self)
        )
        self.tableWidget.setSelectionModel(
            customSelectionModel.CustomSelectionModel(self, self.tableWidget.model())
        )
        alternate = QPalette()
        alternate.setColor(QPalette.AlternateBase, DM_GUI_LIGHT_GREY)
        alternate.setColor(QPalette.Base, DM_GUI_WHITE)
        self.tableWidget.setAlternatingRowColors(True)
        self.tableWidget.setPalette(alternate)
        grid.addWidget(self.tableWidget, 3, 0, 1, 5)

        self.addBtn = QPushButton("Add Experiment", self)
        self.addBtn.setFocusPolicy(Qt.NoFocus)
        self.addBtn.clicked.connect(self.addExperiment)
        self.addBtn.setMaximumWidth(130)

        self.delBtn = QPushButton("Delete Experiment", self)
        self.delBtn.setFocusPolicy(Qt.NoFocus)
        self.delBtn.clicked.connect(self.deleteExperiment)
        self.delBtn.setMaximumWidth(130)

        self.modBtn = QPushButton("Use Selected", self)
        self.modBtn.setFocusPolicy(Qt.NoFocus)
        self.modBtn.clicked.connect(self.setExperiment)
        self.modBtn.setMaximumWidth(130)

        hbox1 = QHBoxLayout()
        hbox1.addWidget(self.addBtn)
        hbox1.addWidget(self.modBtn)
        hbox1.addWidget(self.delBtn)

        grid.addLayout(hbox1, 4, 0, 1, 5)

        grid.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding), 5, 0)

        self.updateList()

        self.setLayout(grid)

    # Sets up the table structure and fills it with data
    def updateList(self):
        self.delBtn.setEnabled(False)
        self.modBtn.setEnabled(False)
        self.tableWidget.setSortingEnabled(False)
        if self.stationName:
            self.experimentList = self.experimentDsApi.getExperimentsByStation(
                self.stationName
            )
        else:
            log.warning("No DM station name, Setting empty experiment.")
            self.experimentList = []
        self.tableWidget.setRowCount(len(self.experimentList))
        self.tableWidget.setColumnCount(4)
        self.tableWidget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tableWidget.setHorizontalHeaderLabels(
            "Name;Type;Start Date;Description;".split(";")
        )
        self.tableWidget.horizontalHeader().setStretchLastSection(True)

        i = 0
        for experiment in self.experimentList:
            rowName = QTableWidgetItem(experiment.get(DM_NAME_KEY))
            rowName.setData(Qt.UserRole, experiment.get(DM_ID_KEY))
            rowType = QTableWidgetItem(
                str(experiment.get(DM_EXPERIMENT_TYPE_KEY).get(DM_NAME_KEY))
            )
            rowStartDate = QTableWidgetItem(
                str(experiment.get(DM_START_DATE_KEY, "")[:19])
            )
            rowDescription = QTableWidgetItem(experiment.get(DM_DESCRIPTION_KEY, ""))
            self.tableWidget.setItem(i, 0, rowName)
            self.tableWidget.setItem(i, 1, rowType)
            self.tableWidget.setItem(i, 2, rowStartDate)
            self.tableWidget.setItem(i, 3, rowDescription)
            i += 1

        self.tableWidget.setSortingEnabled(True)

    # Expands the given row to fit the size of its contents
    def expandRow(self, row, column):
        self.tableWidget.resizeRowToContents(row)

    # Remembers the information of the experiment selected so that it may be used in the future
    def setExperiment(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        id = self.tableWidget.item(self.tableWidget.currentRow(), 0).data(Qt.UserRole)
        self.setExperimentById(id)

    def setExperimentById(self, id):
        self.parent.generalSettings = {}
        experiment = self.experimentDsApi.getExperimentById(id)
        self.parent.generalSettings = experiment.data
        if DM_START_DATE_KEY in self.parent.generalSettings:
            match = search(
                r"\d{4}-\d{2}-\d{2}", self.parent.generalSettings[DM_START_DATE_KEY]
            )
            date = datetime.strptime(
                match.group(), TimeUtility.GMT_FORMAT_SHORT
            ).strftime(TimeUtility.GMT_FORMAT_SHORT)
            self.parent.generalSettings[DM_START_DATE_KEY] = QDate.fromString(
                date, TimeUtility.PYQT_FORMAT_YMD
            )
        if DM_END_DATE_KEY in self.parent.generalSettings:
            match = search(
                r"\d{4}-\d{2}-\d{2}", self.parent.generalSettings[DM_END_DATE_KEY]
            )
            date = datetime.strptime(
                match.group(), TimeUtility.GMT_FORMAT_SHORT
            ).strftime(TimeUtility.GMT_FORMAT_SHORT)
            self.parent.generalSettings[DM_END_DATE_KEY] = QDate.fromString(
                date, TimeUtility.PYQT_FORMAT_YMD
            )

        self.parent.expSwitched()
        self.loadCurrentUsers(experiment)

        QApplication.restoreOverrideCursor()
        self.parent.genParamsTab.fillParams()
        self.parent.setTab(self.parent.genParamsTab)

    def loadCurrentUsers(self, experiment=None):
        if experiment is None:
            experimentId = self.parent.generalSettings.get(DM_ID_KEY)
            experiment = self.experimentDsApi.getExperimentById(experimentId)

        userList = [
            self.userApi.getUserByUsername(user)
            for user in experiment.get(DM_EXPERIMENT_USERNAME_LIST_KEY)
        ]
        self.parent.currentUsers = []
        userUsernames = []
        for x in userList:
            userInfo = UserInfo(x)
            if userInfo.getBadge() not in userUsernames:
                self.parent.currentUsers.append(userInfo)
                userUsernames.append(userInfo.getBadge())

    # Removes all temporarily stored experiment data and switches to the correct page
    def addExperiment(self):
        self.parent.generalSettings = {}
        self.parent.expSwitched()
        self.parent.currentUsers = []
        if self.parent.beamlineName or self.parent.onlyEsaf == 1:
            self.parent.setTab(self.parent.addExperimentTab)
        else:
            self.parent.GenParamsTab.fillParams(self.parent.genParamsTab)
            self.parent.setTab(self.parent.genParamsTab)

    # Warning dialog to check that the user truly wants to delete the experiment
    def deleteExperiment(self):
        experimentName = str(
            self.tableWidget.item(self.tableWidget.currentRow(), 0).text()
        )

        if not self.experimentDeleter.canDeleteExperiment(experimentName):
            self.dialog = QMessageBox()
            self.dialog.setIcon(QMessageBox.Warning)
            self.dialog.setWindowTitle("Cannot delete experiment")
            self.dialog.setText(
                "Experiment cannot be deleted. It has a daq or upload still running."
            )
            self.dialog.exec_()
            self.dialog = None
            return

        experimentFiles = self.fileCatApi.getExperimentFiles(experimentName)
        text = (
            "There are "
            + str(len(experimentFiles))
            + " cataloged files for experiment "
            + experimentName
            + ".\nIf you continue:\n1) Experiment "
            + experimentName
            + " will be deleted from the DM DB.\n2) All experiment files will be removed from "
            "storage.\n3) Experiment file catalog will be destroyed.\nProceed?"
        )
        self.dialog = QMessageBox(
            QMessageBox.Warning,
            "Delete Experiment",
            text,
            QMessageBox.Yes | QMessageBox.No,
        )
        reply = self.dialog.exec_()
        # remove reference when dialog closes
        self.dialog = None

        if reply == QMessageBox.Yes:
            self.experimentDeleter.deleteExperiment(experimentName)
            self.parent.refreshTables()

    # Enables the buttons after the user has clicked on a row
    def enableButtons(self):
        self.delBtn.setEnabled(True)
        self.modBtn.setEnabled(True)

    # Manually updates the tableView
    def updateView(self, index):
        self.tableWidget.update(index)

    # Returns the tables on this tab
    def getTables(self):
        tables = [self.tableWidget]
        return tables

    # Signals the parent to handle the right click event
    def contextMenuEvent(self, event):
        self.parent.handleRightClickMenu(self.tableWidget, event)

    def canUpdateExperiment(self, experimentName: str) -> bool:
        return self.experimentDeleter.canDeleteExperiment(experimentName)
