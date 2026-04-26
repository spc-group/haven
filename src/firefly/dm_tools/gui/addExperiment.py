import logging
from datetime import date, datetime

from dm.common.constants.dmEsafConstants import (
    DM_ESAF_ID_KEY,
    DM_ESAF_TITLE_KEY,
    DM_EXPERIMENTERS_KEY,
    DM_GUP_ID_KEY,
    DM_TITLE_KEY,
)
from dm.common.constants.dmExperimentConstants import (
    DM_END_DATE_KEY,
    DM_EXPERIMENT_USERS_KEY,
    DM_START_DATE_KEY,
)
from dm.common.constants.dmObjectLabels import (
    DM_DESCRIPTION_KEY,
    DM_ID_KEY,
    DM_NAME_KEY,
)
from dm.common.constants.dmUserConstants import (
    DM_BADGE_KEY,
    DM_EMAIL_KEY,
    DM_FIRST_NAME_KEY,
    DM_INSTITUTION_KEY,
    DM_LAST_NAME_KEY,
    DM_PI_FLAG_KEY,
)
from dm.common.exceptions.communicationError import CommunicationError
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPalette
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from .apiFactory import ApiFactory
from .objects.userInfo import UserInfo
from .subclasses import customSelectionModel, customStyledDelegate
from .subclasses.style import DM_FONT_ARIAL_KEY, DM_GUI_LIGHT_GREY, DM_GUI_WHITE

log = logging.getLogger("dm_tools")


# Define the experiments tab content:
class AddExperimentTab(QWidget):
    def __init__(self, stationName, beamlineName, parent, id=-1):
        super(AddExperimentTab, self).__init__(parent)
        self.stationName = stationName
        self.beamlineName = beamlineName
        self.parent = parent
        self.showingDetails = 0
        if self.parent.onlyEsaf == 0:
            self.experimentPropApi = ApiFactory.getInstance().getBssApsDbApi()
        self.esafPropApi = ApiFactory.getInstance().getEsafApsDbApi()
        self.userApi = ApiFactory.getInstance().getUserDsApi()
        self.addExperimentsTabLayout()

    # Sets up the tab's layout, each block is a row
    def addExperimentsTabLayout(self):
        grid = QGridLayout()

        labelFont = QFont(DM_FONT_ARIAL_KEY, 18, QFont.Bold)
        if self.parent.useEsaf == 1:
            self.lbl = QLabel(self.stationName + " ESAF List", self)
            self.propToggle = QPushButton("Use GUP DB", self)
            self.startBtn = QPushButton("Use ESAF", self)
        else:
            self.lbl = QLabel(self.stationName + " GUP List", self)
            self.propToggle = QPushButton("Use ESAF DB", self)
            self.startBtn = QPushButton("Use GUP", self)
        self.propToggle.setFocusPolicy(Qt.NoFocus)
        self.startBtn.setFocusPolicy(Qt.NoFocus)
        if self.parent.onlyEsaf == 1:
            self.propToggle.hide()
            grid.addWidget(self.lbl, 0, 1, 1, 3)
        else:
            grid.addWidget(self.propToggle, 0, 4)
            grid.addWidget(self.lbl, 0, 1, 1, 3)
        self.startBtn.clicked.connect(self.startProposal)
        self.startBtn.setMaximumWidth(130)
        self.lbl.setAlignment(Qt.AlignCenter)
        self.lbl.setFont(labelFont)

        self.backBtn = QPushButton("Back", self)
        self.backBtn.clicked.connect(self.checkBack)
        self.backBtn.setFocusPolicy(Qt.NoFocus)
        grid.addWidget(self.backBtn, 0, 0)
        self.backBtn.setMaximumWidth(100)

        self.runDropdown = QComboBox()
        self.runDropdown.setFocusPolicy(Qt.NoFocus)
        self.runDropdown.setMaximumWidth(130)
        self.runDropdown.currentIndexChanged.connect(self.updateList)
        self.updateDropdown()

        self.detailBtn = QPushButton("Show Details", self)
        self.detailBtn.setFocusPolicy(Qt.NoFocus)
        self.detailBtn.clicked.connect(self.toggleDetails)
        self.detailBtn.setMaximumWidth(130)

        self.tableWidget = QTableWidget()
        self.tableWidget.cellDoubleClicked.connect(self.startProposal)
        self.tableWidget.clicked.connect(self.enableButtons)
        self.tableWidget.setItemDelegate(
            customStyledDelegate.CustomStyledDelegate(self.tableWidget, self)
        )
        self.tableWidget.setSelectionModel(
            customSelectionModel.CustomSelectionModel(self, self.tableWidget.model())
        )

        self.updateList()
        self.detailsTable = QTableWidget()
        self.detailsTable.setItemDelegate(
            customStyledDelegate.CustomStyledDelegate(self.detailsTable, self)
        )
        self.detailsTable.setSelectionModel(
            customSelectionModel.CustomSelectionModel(self, self.detailsTable.model())
        )
        self.detailsTable.hide()

        alternate = QPalette()
        alternate.setColor(QPalette.AlternateBase, DM_GUI_LIGHT_GREY)
        alternate.setColor(QPalette.Base, DM_GUI_WHITE)
        self.detailsTable.setAlternatingRowColors(True)
        self.detailsTable.setPalette(alternate)
        self.tableWidget.setAlternatingRowColors(True)
        self.tableWidget.setPalette(alternate)

        self.modBtn = QPushButton("Continue Manually", self)
        self.modBtn.setFocusPolicy(Qt.NoFocus)
        self.modBtn.clicked.connect(self.startManual)
        self.modBtn.setMaximumWidth(130)

        self.propToggle.clicked.connect(self.proposalDBToggle)
        self.propToggle.setMaximumWidth(130)

        if self.parent.esafSector is None:
            self.propToggle.hide()

        hRow2 = QHBoxLayout()
        hRow2.addWidget(self.runDropdown)
        hRow2.setAlignment(self.backBtn, Qt.AlignRight)
        grid.addLayout(hRow2, 2, 4)

        hRow3 = QHBoxLayout()
        hRow3.addWidget(self.tableWidget)
        hRow3.addWidget(self.detailsTable)
        grid.addLayout(hRow3, 3, 0, 1, 5)

        hRow4 = QHBoxLayout()
        hRow4.addWidget(self.detailBtn)
        hRow4.addWidget(self.startBtn)
        hRow4.addWidget(self.modBtn)
        grid.addLayout(hRow4, 4, 0, 1, 5)

        self.setLayout(grid)

    # Populates the run dropdown with valid entries
    def updateDropdown(self):
        self.runDropdown.blockSignals(True)
        self.runDropdown.clear()
        if self.parent.useEsaf == 1:
            self.runList = [
                str(datetime.today().year - 1),
                str(datetime.today().year - 2),
                str(datetime.today().year - 3),
                str(datetime.today().year - 4),
                str(datetime.today().year - 5),
            ]
        else:
            # get the run list as a list of dates like above
            try:
                self.runList = [
                    run.get(DM_NAME_KEY) for run in self.experimentPropApi.listRuns()
                ]
            except CommunicationError as exc:
                log.error(exc)
                self.runList = []
        if self.parent.useEsaf == 1:
            self.runDropdown.addItem("Current Year")
            for run in self.runList:
                self.runDropdown.addItem(run)
        else:
            self.runDropdown.addItem("Current Run")
            for run in self.runList:
                if int(run[:4]) < date.today().year - 5:
                    continue
                else:
                    self.runDropdown.addItem(run)
        self.runDropdown.blockSignals(False)

    # Fills the table with proposals from experimentPropApi
    def updateList(self):
        self.startBtn.setEnabled(False)
        self.detailBtn.setEnabled(False)
        self.tableWidget.setSortingEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        if (
            str(self.runDropdown.currentText()) == "Current Year"
            or str(self.runDropdown.currentText()) == "Current Run"
        ):
            if self.parent.useEsaf == 1:
                self.proposalList = self.esafPropApi.listStationEsafs(
                    self.stationName, self.beamlineName, datetime.today().year
                )
            else:
                self.proposalList = self.parent.currentProposals
        else:
            try:
                if self.parent.useEsaf == 1:
                    self.proposalList = self.esafPropApi.listStationEsafs(
                        self.stationName,
                        self.beamlineName,
                        int(self.runDropdown.currentText()),
                    )
                else:
                    self.proposalList = self.esafPropApi.listStationProposals(
                        self.stationName,
                        self.beamlineName,
                        str(self.runDropdown.currentText()),
                    )
            except Exception:
                self.proposalList = []
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Warning)
                msg.setText("No proposals found")
                msg.setInformativeText("Please select a different run")
                msg.setWindowTitle("DM Warning")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec_()
        ids = []
        if self.parent.useEsaf == 1:
            for esaf in self.esafPropApi.listStationEsafs(
                self.stationName, self.beamlineName, datetime.today().year
            ):
                if esaf.get(DM_ESAF_ID_KEY) in ids:
                    self.proposalList.remove(esaf)
                else:
                    ids.append(esaf.get(DM_ESAF_ID_KEY))
        else:
            for proposal in self.proposalList:
                if proposal.get(DM_ID_KEY) in ids:
                    self.proposalList.remove(proposal)
                else:
                    ids.append(proposal.get(DM_ID_KEY))
        self.tableWidget.setRowCount(len(self.proposalList))
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tableWidget.setHorizontalHeaderLabels("ID;Description;".split(";"))
        self.tableWidget.horizontalHeader().setStretchLastSection(True)

        i = 0
        for proposal in self.proposalList:
            if self.parent.useEsaf == 1:
                rowID = QTableWidgetItem(str(proposal.get(DM_ESAF_ID_KEY)))
                rowID.setData(Qt.UserRole, proposal.get(DM_ESAF_ID_KEY))
                rowPropName = QTableWidgetItem(proposal.get(DM_ESAF_TITLE_KEY))
            else:
                rowID = QTableWidgetItem(str(proposal.get(DM_ID_KEY)))
                rowID.setData(Qt.UserRole, proposal.get(DM_ID_KEY))
                rowPropName = QTableWidgetItem(proposal.get(DM_TITLE_KEY))
            self.tableWidget.setItem(i, 0, rowID)
            self.tableWidget.setItem(i, 1, rowPropName)
            i += 1
        QApplication.restoreOverrideCursor()
        self.tableWidget.setSortingEnabled(True)

    # Expands the given row to fit the size of its contents
    def expandRow(self, row, column, table):
        table.resizeRowToContents(row)

    # Fills out as much information about an experiment as possible using the proposal
    def startProposal(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        id = self.tableWidget.item(self.tableWidget.currentRow(), 0).data(Qt.UserRole)
        # set the esaf id in the parent to be available in other tabs
        if self.parent.useEsaf == 1:
            proposal = self.esafPropApi.getStationEsafById(self.stationName, id)
            self.parent.generalSettings = {
                DM_DESCRIPTION_KEY: proposal.get(DM_ESAF_TITLE_KEY)
            }
            self.parent.generalSettings[DM_ESAF_ID_KEY] = proposal.get(DM_ESAF_ID_KEY)
            propUsers = proposal.get(DM_EXPERIMENT_USERS_KEY)
        else:
            if (
                str(self.runDropdown.currentText()) == "Current Year"
                or str(self.runDropdown.currentText()) == "Current Run"
            ):
                currentRun = self.experimentPropApi.getCurrentRun().data[DM_NAME_KEY]
                proposal = self.experimentPropApi.getStationProposalById(
                    self.stationName, id, runName=currentRun
                )
            else:
                proposal = self.experimentPropApi.getStationProposalById(
                    self.stationName, id, str(self.runDropdown.currentText())
                )
            self.parent.generalSettings = {
                DM_DESCRIPTION_KEY: proposal.get(DM_TITLE_KEY)
            }
            self.parent.generalSettings[DM_GUP_ID_KEY] = proposal.get(DM_ID_KEY)
            propUsers = proposal.get(DM_EXPERIMENTERS_KEY)

        self.parent.generalSettings[DM_START_DATE_KEY] = proposal.getStartDate()
        self.parent.generalSettings[DM_END_DATE_KEY] = proposal.getEndDate()
        objectAllUsers = []
        userUsernames = []
        for x in self.parent.beamlineManagers:
            userInstance = self.userApi.getUserByUsername(x)
            userInfo = UserInfo(userInstance)
            objectAllUsers.append(userInfo)
            userUsernames.append(userInfo.getUsername())

        for user in propUsers:
            userInfo = UserInfo(user)
            if userInfo.getUsername() not in userUsernames:
                objectAllUsers.append(userInfo)
                userUsernames.append(userInfo.getUsername())

        self.parent.expSwitched()
        self.parent.currentUsers = objectAllUsers
        QApplication.restoreOverrideCursor()
        self.parent.GenParamsTab.fillParams(self.parent.genParamsTab)
        self.parent.setTab(self.parent.genParamsTab)

    # Starts a blank experiment
    def startManual(self):
        self.parent.expSwitched()
        self.parent.currentUsers = []
        self.parent.generalSettings = {}
        for x in self.parent.beamlineManagers:
            userInstance = self.userApi.getUserByUsername(x)
            self.parent.currentUsers.append(UserInfo(userInstance))
        self.parent.GenParamsTab.fillParams(self.parent.genParamsTab)
        self.parent.setTab(self.parent.genParamsTab)

    # Toggles which table is visible
    def toggleDetails(self):
        if self.showingDetails == 1:
            self.detailsTable.clearFocus()
            self.detailsTable.clearSelection()
            self.tableWidget.show()
            self.detailsTable.hide()
            self.detailBtn.show()
            self.showingDetails = 0
            self.propToggle.setEnabled(True)
        else:
            try:
                self.tableWidget.item(self.tableWidget.currentRow(), 0).data(
                    Qt.UserRole
                ) is None
            except AttributeError:
                self.selectProposalDialog()
                return
            self.proposalDetails()
            self.detailsTable.show()
            self.tableWidget.setSelectionMode(QAbstractItemView.NoSelection)
            self.tableWidget.hide()
            self.tableWidget.setSelectionMode(QAbstractItemView.SingleSelection)
            self.detailBtn.hide()
            self.showingDetails = 1
            self.propToggle.setEnabled(False)

    # Fills detailsTable with user information from the selected proposal
    def proposalDetails(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        id = self.tableWidget.item(self.tableWidget.currentRow(), 0).data(Qt.UserRole)
        self.tableWidget.clearFocus()
        self.detailsTable.setColumnCount(5)
        if (
            str(self.runDropdown.currentText()) == "Current Run"
            or str(self.runDropdown.currentText()) == "Current Year"
        ):
            if self.parent.useEsaf == 1:
                proposal = self.esafPropApi.getStationEsafById(self.stationName, id)
            else:
                proposal = self.experimentPropApi.getStationProposalById(
                    self.stationName, id
                )
        else:
            if self.parent.useEsaf == 1:
                proposal = self.esafPropApi.getStationEsafById(self.stationName, id)
            else:
                proposal = self.experimentPropApi.getStationProposalById(
                    self.stationName, id, str(self.runDropdown.currentText())
                )
        if self.parent.useEsaf == 1:
            self.detailsTable.setRowCount(len(proposal.get(DM_EXPERIMENT_USERS_KEY)))
            experimenters = proposal[DM_EXPERIMENT_USERS_KEY]
            self.detailsTable.setHorizontalHeaderLabels(
                "Badge Number;First Name;Last Name;PI;Email".split(";")
            )
        else:
            self.detailsTable.setRowCount(len(proposal.get(DM_EXPERIMENTERS_KEY)))
            experimenters = proposal[DM_EXPERIMENTERS_KEY]
            self.detailsTable.setHorizontalHeaderLabels(
                "Badge Number;First Name;Last Name;PI;Institution".split(";")
            )
        self.detailsTable.setSelectionMode(QAbstractItemView.SingleSelection)
        self.detailsTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.detailsTable.cellDoubleClicked.connect(
            lambda row, column: self.expandRow(row, column, self.detailsTable)
        )
        self.detailsTable.horizontalHeader().setStretchLastSection(True)

        i = 0

        for experimenter in experimenters:
            rowBadge = QTableWidgetItem()
            rowBadge.setData(Qt.EditRole, int(experimenter.get(DM_BADGE_KEY)))
            rowFirstName = QTableWidgetItem(experimenter.get(DM_FIRST_NAME_KEY))
            rowLastName = QTableWidgetItem(experimenter.get(DM_LAST_NAME_KEY))
            rowPiFlag = QTableWidgetItem(experimenter.get(DM_PI_FLAG_KEY))
            if self.parent.useEsaf == 1:
                rowEmail = QTableWidgetItem(experimenter.get(DM_EMAIL_KEY))
                self.detailsTable.setItem(i, 4, rowEmail)
            else:
                rowInstitution = QTableWidgetItem(experimenter.get(DM_INSTITUTION_KEY))
                self.detailsTable.setItem(i, 4, rowInstitution)
            self.detailsTable.setItem(i, 0, rowBadge)
            self.detailsTable.setItem(i, 1, rowFirstName)
            self.detailsTable.setItem(i, 2, rowLastName)
            self.detailsTable.setItem(i, 3, rowPiFlag)
            i += 1
        self.detailsTable.setSortingEnabled(True)
        QApplication.restoreOverrideCursor()

    # Toggle between showing proposals and esafs
    def proposalDBToggle(self):
        self.tableWidget.clearSelection()
        if self.parent.useEsaf == 1:
            self.parent.useEsaf = 0
            self.propToggle.setText("Use ESAF DB")
            self.lbl.setText(self.stationName + " GUP List")
            self.startBtn.setText("Use GUP")
        else:
            if self.parent.esafSector != 0:
                self.parent.useEsaf = 1
                self.propToggle.setText("Use GUP DB")
                self.lbl.setText(self.stationName + " ESAF List")
                self.startBtn.setText("Use ESAF")
            else:
                self.noEsafDialog()
        self.updateDropdown()
        self.updateList()

    # Enables the buttons after the user has clicked on a row
    def enableButtons(self):
        self.startBtn.setEnabled(True)
        self.detailBtn.setEnabled(True)

    # Returns the tables on this tab
    def getTables(self):
        tables = [self.tableWidget, self.detailsTable]
        return tables

    # Checks to see if the back button should send the user out of the detail table or back a tab
    def checkBack(self):
        if self.showingDetails == 1:
            self.toggleDetails()
        else:
            self.parent.setTab(self.parent.experimentsTab)

    # Manually updates the tableView
    def updateView(self, index):
        if self.tableWidget.isVisible():
            self.tableWidget.update(index)
        else:
            self.detailsTable.update(index)

    # Signals the parent to handle the right click event
    def contextMenuEvent(self, event):
        if self.tableWidget.isVisible():
            self.parent.handleRightClickMenu(self.tableWidget, event)
        else:
            self.parent.handleRightClickMenu(self.detailsTable, event)

    # Error dialog to ensure the user selects an experiment to show details on
    def selectProposalDialog(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText("No Proposal Selected")
        msg.setInformativeText("Please select a proposal before trying to view details")
        msg.setWindowTitle("DM Warning")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    # Error dialog to alert the user there is no esaf sector set
    def noEsafDialog(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText("No ESAF sector set")
        msg.setInformativeText(
            "Please ensure the environment variables are set correctly if you wish to use ESAF DB"
        )
        msg.setWindowTitle("DM Warning")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
