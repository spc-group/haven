import logging
from datetime import date, datetime

from dm.common.constants.dmEsafConstants import (
    DM_ESAF_ID_KEY,
    DM_ESAF_TITLE_KEY,
    DM_EXPERIMENTERS_KEY,
    DM_TITLE_KEY,
)
from dm.common.constants.dmExperimentConstants import DM_EXPERIMENT_USERS_KEY
from dm.common.constants.dmObjectLabels import DM_ID_KEY, DM_NAME_KEY
from dm.common.constants.dmUserConstants import (
    DM_EMAIL_KEY,
    DM_FIRST_NAME_KEY,
    DM_LAST_NAME_KEY,
    DM_USERNAME_KEY,
)
from dm.common.exceptions.communicationError import CommunicationError
from dm.common.exceptions.configurationError import DmException
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QFontMetrics, QPalette, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .apiFactory import ApiFactory
from .objects.userInfo import UserInfo
from .subclasses import (
    customSelectionModel,
    customSortFilterProxyModel,
    customStyledDelegate,
    frozenTable,
)
from .subclasses.style import (
    DM_FONT_ARIAL_KEY,
    DM_FONT_TIMES_KEY,
    DM_GUI_LIGHT_GREY,
    DM_GUI_WHITE,
)

log = logging.getLogger("dm_tools")


# Define the experiments tab content:
class ManageUsersTab(QWidget):
    def __init__(self, stationName, beamlineName, parent, id=-1):
        super(ManageUsersTab, self).__init__(parent)
        self.stationName = stationName
        self.beamlineName = beamlineName
        self.parent = parent
        self.filters = {0: "", 1: "", 2: "", 3: ""}
        if not self.parent.onlyEsaf and self.parent.beamlineName:
            self.experimentPropApi = ApiFactory.getInstance().getBssApsDbApi()
        self.experimentDsApi = ApiFactory.getInstance().getExperimentDsApi()
        self.esafPropApi = ApiFactory.getInstance().getEsafApsDbApi()
        self.userApi = ApiFactory.getInstance().getUserDsApi()
        self.manageUsersTabLayout()
        self.userLoadThread = GetUsersThread(self.userApi)
        self.userLoadThread.sendUsers.connect(self.sendUsers)
        self.userLoadThread.start()

    # Sets up the tab's layout, each block is a row
    def manageUsersTabLayout(self):
        grid = QGridLayout()
        labelFont = QFont(DM_FONT_ARIAL_KEY, 18, QFont.Bold)
        self.titleLbl = QLabel(self.stationName + " User Management", self)
        self.titleLbl.setAlignment(Qt.AlignCenter)
        self.titleLbl.setFont(labelFont)
        grid.addWidget(self.titleLbl, 0, 0, 1, 3)

        if self.parent.useEsaf == 1:
            self.propToggle = QPushButton("Show Proposals", self)
        else:
            self.propToggle = QPushButton("Show Esafs", self)
        self.propToggle.setFocusPolicy(Qt.NoFocus)
        if self.parent.onlyEsaf == 1:
            self.propToggle.hide()

        backBtn = QPushButton("Back", self)
        backBtn.setFocusPolicy(Qt.NoFocus)
        # backBtn.clicked.connect(self.revertChanges)
        backBtn.clicked.connect(lambda: self.parent.setTab(self.parent.genParamsTab))
        grid.addWidget(backBtn, 0, 0, Qt.AlignLeft)
        backBtn.setMaximumWidth(100)

        self.currentUserTable = QTableWidget()
        self.currentUserTable.doubleClicked.connect(self.moveToDatabase)
        self.currentUserTable.setItemDelegate(
            customStyledDelegate.CustomStyledDelegate(self.currentUserTable, self)
        )
        self.currentUserTable.setSelectionModel(
            customSelectionModel.CustomSelectionModel(
                self, self.currentUserTable.model()
            )
        )
        self.availableUserTable = QTableView()
        self.availableUserTableModel = QStandardItemModel()
        self.availableUserTable.setModel(self.availableUserTableModel)
        self.availableUserTable.setItemDelegate(
            customStyledDelegate.CustomStyledDelegate(self.availableUserTable, self)
        )
        self.availableUserTable.setSelectionModel(
            customSelectionModel.CustomSelectionModel(
                self, self.availableUserTable.model()
            )
        )
        self.availableUserTable.doubleClicked.connect(self.moveToCurrent)
        self.availableUserTable.hide()
        self.allUserTableModel = QStandardItemModel()
        self.allUserTable = frozenTable.FreezeTableWidget(self, self.allUserTableModel)
        # self.allUserTable.setModel(self.allUserTableModel)
        self.allUserTable.doubleClicked.connect(self.moveToCurrent)
        self.allUserTable.setItemDelegate(
            customStyledDelegate.CustomStyledDelegate(self.allUserTable, self)
        )
        self.allUserTable.setSelectionModel(
            customSelectionModel.CustomSelectionModel(self, self.allUserTable.model())
        )

        self.usernameFilter = QLineEdit()
        self.usernameFilter.setPlaceholderText(DM_USERNAME_KEY.title())
        self.usernameFilter.returnPressed.connect(
            lambda: self.addFilter(self.usernameFilter.text(), 0)
        )
        self.usernameFilter.editingFinished.connect(
            lambda: self.addFilter(self.usernameFilter.text(), 0)
        )
        self.firstFilter = QLineEdit()
        self.firstFilter.setPlaceholderText(DM_FIRST_NAME_KEY.title())
        self.firstFilter.returnPressed.connect(
            lambda: self.addFilter(self.firstFilter.text(), 1)
        )
        self.firstFilter.editingFinished.connect(
            lambda: self.addFilter(self.firstFilter.text(), 1)
        )
        self.lastFilter = QLineEdit()
        self.lastFilter.setPlaceholderText(DM_LAST_NAME_KEY.title())
        self.lastFilter.returnPressed.connect(
            lambda: self.addFilter(self.lastFilter.text(), 2)
        )
        self.lastFilter.editingFinished.connect(
            lambda: self.addFilter(self.lastFilter.text(), 2)
        )
        self.emailFilter = QLineEdit()
        self.emailFilter.setPlaceholderText(DM_EMAIL_KEY.title())
        self.emailFilter.returnPressed.connect(
            lambda: self.addFilter(self.emailFilter.text(), 3)
        )
        self.emailFilter.editingFinished.connect(
            lambda: self.addFilter(self.emailFilter.text(), 3)
        )

        self.allUserTable.getFrozenView().setIndexWidget(
            self.allUserTable.getFrozenView().model().index(0, 0), self.usernameFilter
        )
        self.allUserTable.getFrozenView().setIndexWidget(
            self.allUserTable.getFrozenView().model().index(0, 1), self.firstFilter
        )
        self.allUserTable.getFrozenView().setIndexWidget(
            self.allUserTable.getFrozenView().model().index(0, 2), self.lastFilter
        )
        self.allUserTable.getFrozenView().setIndexWidget(
            self.allUserTable.getFrozenView().model().index(0, 3), self.emailFilter
        )

        alternate = QPalette()
        alternate.setColor(QPalette.AlternateBase, DM_GUI_LIGHT_GREY)
        alternate.setColor(QPalette.Base, DM_GUI_WHITE)
        self.currentUserTable.setAlternatingRowColors(True)
        self.currentUserTable.setPalette(alternate)
        self.availableUserTable.setAlternatingRowColors(True)
        self.availableUserTable.setPalette(alternate)
        self.allUserTable.setAlternatingRowColors(True)
        self.allUserTable.setPalette(alternate)
        self.moveUserBtn = QPushButton("<->", self)
        self.moveUserBtn.setFocusPolicy(Qt.NoFocus)
        self.moveUserBtn.clicked.connect(self.moveUsers)
        self.moveUserBtn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)

        currentLabel = QLabel("Current Users", self)
        currentLabel.setAlignment(Qt.AlignCenter)
        currentLabel.setFixedHeight(30)
        self.userDropdown = QComboBox(self)
        self.userDropdown.setFocusPolicy(Qt.NoFocus)
        self.userDropdown.currentIndexChanged.connect(self.updateAvailableUsers)
        self.userDropdown.setMaximumWidth(250)
        self.runDropdown = QComboBox(self)
        self.runDropdown.setFocusPolicy(Qt.NoFocus)
        self.runDropdown.currentIndexChanged.connect(self.updateRun)
        self.updateDropdown()

        self.saveUsersBtn = QPushButton("Save", self)
        self.saveUsersBtn.setFocusPolicy(Qt.NoFocus)
        self.saveUsersBtn.clicked.connect(self.refreshGen)
        self.saveUsersBtn.setFixedHeight(40)

        self.resetBtn = QPushButton("Reset", self)
        self.resetBtn.setFocusPolicy(Qt.NoFocus)
        self.resetBtn.clicked.connect(self.revertChanges)
        self.resetBtn.setFixedHeight(40)

        self.propToggle.clicked.connect(self.proposalDBToggle)
        self.propToggle.setMaximumWidth(130)
        if self.parent.esafSector is None:
            self.propToggle.hide()

        grid.addItem(
            QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum), 5, 0
        )

        hRow1 = QHBoxLayout()
        hRow1.addWidget(self.propToggle)

        hRow2 = QHBoxLayout()
        hRow2.addWidget(self.userDropdown)
        hRow2.addWidget(self.runDropdown)

        vColumn1 = QVBoxLayout()
        vColumn1.addWidget(currentLabel)
        vColumn1.addWidget(self.currentUserTable)
        grid.addLayout(vColumn1, 3, 0)

        vColumn2 = QVBoxLayout()
        vColumn2.addWidget(self.moveUserBtn)
        grid.addLayout(vColumn2, 3, 1)

        vColumn3 = QVBoxLayout()
        vColumn3.addLayout(hRow1)
        vColumn3.addLayout(hRow2)
        vColumn3.addWidget(self.availableUserTable)
        vColumn3.addWidget(self.allUserTable)
        grid.addLayout(vColumn3, 3, 2)

        saveResetBtns = QHBoxLayout()
        saveResetBtns.addWidget(self.saveUsersBtn)
        saveResetBtns.addWidget(self.resetBtn)

        grid.addLayout(saveResetBtns, 4, 0, 1, 3, Qt.AlignCenter)

        self.setLayout(grid)

    # Populates the proposal and run dropdowns with valid entries
    def updateDropdown(self):
        self.userDropdown.blockSignals(True)
        self.userDropdown.clear()
        self.userDropdown.blockSignals(False)
        if not self.parent.beamlineName and not self.parent.esafSector:
            self.runDropdown.addItem("Beamline Name and Esaf Sector not set")
            return
        if self.parent.useEsaf == 1:
            self.proposalList = self.esafPropApi.listStationEsafs(
                self.stationName, self.beamlineName, datetime.today().year
            )
        else:
            self.proposalList = self.parent.currentProposals
        self.userDropdown.addItem("All Users", -1)
        self.runList = []
        for proposal in self.proposalList:
            fm = QFontMetrics(QFont(DM_FONT_TIMES_KEY, 12))
            if self.parent.useEsaf == 1:
                elidedText = fm.elidedText(
                    proposal.get(DM_ESAF_TITLE_KEY), Qt.ElideRight, 250
                )
                self.runList = [
                    str(datetime.today().year - 1),
                    str(datetime.today().year - 2),
                    str(datetime.today().year - 3),
                    str(datetime.today().year - 4),
                    str(datetime.today().year - 5),
                ]
                self.userDropdown.addItem(elidedText, proposal.get(DM_ESAF_ID_KEY))
            else:
                elidedText = fm.elidedText(
                    proposal.get(DM_TITLE_KEY), Qt.ElideRight, 250
                )
                runs = self.experimentPropApi.listRuns()
                for run in runs:
                    self.runList.append(run.get(DM_NAME_KEY))
                self.userDropdown.addItem(elidedText, proposal.get(DM_ID_KEY))
        self.runDropdown.blockSignals(True)
        self.runDropdown.clear()

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

    # Repopulates the potential proposals based on the new run
    def updateRun(self):
        if not self.parent.beamlineName and not self.parent.esafSector:
            self.userDropdown.blockSignals(True)
            self.userDropdown.clear()
            self.userDropdown.addItem("-------", -1)
            self.userDropdown.blockSignals(False)
            return
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
                    self.proposalList = self.experimentPropApi.listStationProposals(
                        self.stationName,
                        self.beamlineName,
                        str(self.runDropdown.currentText()),
                    )
            except DmException:
                self.noRunErrorDialog()
                QApplication.restoreOverrideCursor()
                return
        self.userDropdown.blockSignals(True)
        self.userDropdown.clear()
        self.userDropdown.blockSignals(False)
        self.userDropdown.addItem("All Users", -1)
        self.userDropdown.blockSignals(True)
        for proposal in self.proposalList:
            fm = QFontMetrics(QFont(DM_FONT_TIMES_KEY, 12))
            if self.parent.useEsaf == 1:
                elidedText = fm.elidedText(
                    proposal.get(DM_ESAF_TITLE_KEY), Qt.ElideRight, 250
                )
                self.userDropdown.addItem(elidedText, proposal.get(DM_ESAF_ID_KEY))
            else:
                elidedText = fm.elidedText(
                    proposal.get(DM_TITLE_KEY), Qt.ElideRight, 250
                )
                self.userDropdown.addItem(elidedText, proposal.get(DM_ID_KEY))
        self.userDropdown.blockSignals(False)
        QApplication.restoreOverrideCursor()

    # Expands the given row to fit the size of its content
    def expandRow(self, row, column, table):
        table.resizeRowToContents(row)

    # Populates the current user table with users
    def updateCurrentUsers(self):
        self.currentUserTable.setSortingEnabled(False)
        if self.parent.generalSettings.get(DM_NAME_KEY) is not None:
            self.titleLbl.setText(
                self.parent.generalSettings.get(DM_NAME_KEY) + " User Management"
            )
        # Set up the current users table
        self.currentUserTable.setRowCount(len(self.parent.currentUsers))
        self.currentUserTable.setColumnCount(4)
        self.currentUserTable.setSelectionMode(QAbstractItemView.SingleSelection)
        self.currentUserTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.currentUserTable.setHorizontalHeaderLabels(
            "Username;First;Last;Email;".split(";")
        )

        i = 0
        for experimenter in self.parent.currentUsers:
            rowUsername = QTableWidgetItem()
            rowUsername.setData(Qt.EditRole, experimenter.getUsername())
            rowFirstName = QTableWidgetItem(experimenter.getFirstName())
            rowLastName = QTableWidgetItem(experimenter.getLastName())
            rowEmail = QTableWidgetItem(experimenter.getEmail())
            self.currentUserTable.setItem(i, 0, rowUsername)
            self.currentUserTable.setItem(i, 1, rowFirstName)
            self.currentUserTable.setItem(i, 2, rowLastName)
            self.currentUserTable.setItem(i, 3, rowEmail)
            i += 1

        self.currentUserTable.horizontalHeader().setStretchLastSection(True)
        self.currentUserTable.setSortingEnabled(True)
        self.currentUserTable.clearSelection()
        self.currentUserTable.clearFocus()

    # Setup the available & all users tables
    def updateAvailableUsers(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.availableUserTable.setSortingEnabled(False)
        self.availableUserTable.clearSelection()
        self.availableUserTable.clearFocus()
        self.allUserTable.clearSelection()
        self.allUserTable.clearFocus()
        id = self.userDropdown.itemData(self.userDropdown.currentIndex(), Qt.UserRole)
        objectAllUsers = []
        if id != -1:
            if not self.parent.beamlineName:
                QApplication.restoreOverrideCursor()
                return
            if (
                self.runDropdown.currentText() == "Current Run"
                or self.runDropdown.currentText() == "Current Year"
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
                allUsers = proposal.get(DM_EXPERIMENT_USERS_KEY)
            else:
                allUsers = proposal.get(DM_EXPERIMENTERS_KEY)
            usernames = []
            currentUserUsernames = [x.getUsername() for x in self.parent.currentUsers]
            for x in allUsers:
                userInfo = UserInfo(x)
                if userInfo.getUsername() in currentUserUsernames:
                    continue
                else:
                    objectAllUsers.append(userInfo)
                    usernames.append(userInfo.getUsername())

            # QStandardItemModel somehow appends an additional column, so starting with 3 columns results in 4.
            self.availableUserTable.model().setColumnCount(3)
            self.availableUserTable.horizontalHeader().setStretchLastSection(True)
            self.availableUserTable.setSelectionMode(QAbstractItemView.SingleSelection)
            self.availableUserTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.availableUserTable.model().setHorizontalHeaderLabels(
                "Username;First;Last;Email;".split(";")
            )
            self.availableUserTable.model().setRowCount(len(objectAllUsers))

            i = 0
            currentUsernames = [x.getUsername() for x in self.parent.currentUsers]
            for experimenter in objectAllUsers:
                if experimenter.getUsername() in currentUsernames:
                    self.availableUserTable.model().removeRow(i)
                    continue
                rowUsername = QStandardItem(experimenter.getUsername())
                if rowUsername is None:
                    continue
                rowFirstName = QStandardItem(experimenter.getFirstName())
                rowLastName = QStandardItem(experimenter.getLastName())
                rowEmail = QStandardItem(experimenter.getEmail())
                if rowEmail is None:
                    rowEmail = QStandardItem("")
                self.availableUserTable.model().setItem(i, 0, rowUsername)
                self.availableUserTable.model().setItem(i, 1, rowFirstName)
                self.availableUserTable.model().setItem(i, 2, rowLastName)
                self.availableUserTable.model().setItem(i, 3, rowEmail)
                i += 1
            self.availableUserTable.model().takeColumn(4)
            self.allUserTable.hide()
            self.availableUserTable.show()
        else:
            self.filterAllUserTable()
            self.availableUserTable.hide()
            self.allUserTable.show()
            self.allUserTable.updateSectionWidth(
                0, 100, self.allUserTable.getFrozenView().columnWidth(0)
            )
        self.availableUserTable.setSortingEnabled(True)
        QApplication.restoreOverrideCursor()

    # Permanently setup the allUserTable
    def cacheUsers(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        objectAllUsers = []
        count = 0
        pd = QProgressDialog(
            "Caching APS Users...", "Cancel", 0, len(self.parent.allUsers)
        )
        buttonToHide = QPushButton()
        pd.setCancelButton(buttonToHide)
        buttonToHide.hide()
        pd.setWindowModality(Qt.WindowModal)
        for x in self.parent.allUsers:
            uInfo = UserInfo(x)
            objectAllUsers.append(uInfo)
        for user in objectAllUsers:
            rowUsername = QStandardItem(user.getUsername())
            if rowUsername is None:
                continue
            rowFirstName = QStandardItem(user.getFirstName())
            rowLastName = QStandardItem(user.getLastName())
            rowEmail = QStandardItem(user.getEmail())
            if rowEmail is None:
                rowEmail = QStandardItem("")
            self.allUserTableModel.appendRow(
                [rowUsername, rowFirstName, rowLastName, rowEmail]
            )
            if count % 2000 == 0:
                pd.setValue(count)
            count += 1
        self.allUserTable.setModel(self.allUserTableModel)
        self.parent.allUsers = objectAllUsers
        self.allUserTableModel.setRowCount(len(self.parent.allUsers))

        # QStandardItemModel somehow appends an additional column, so starting with 3 columns results in 4.
        self.allUserTableModel.setColumnCount(4)
        self.allUserTable.horizontalHeader().setStretchLastSection(True)
        # self.allUserTable.horizontalHeader().sortIndicatorChanged.connect(self.sortIndicatorChanged)
        self.allUserTable.setSelectionMode(QAbstractItemView.SingleSelection)
        self.allUserTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.allUserTableModel.setHorizontalHeaderLabels(
            "Username;First;Last;Email;".split(";")
        )
        self.allUserTableModel.takeColumn(4)
        self.allUserTableModel.insertRow(0)

        # Sets up the proxy for filtering, must be done after model is prebuilt and added to view for speed
        self.proxy = customSortFilterProxyModel.CustomSortFilterProxyModel()
        self.proxy.setDynamicSortFilter(True)
        self.proxy.setSourceModel(self.allUserTableModel)
        self.allUserTable.setModel(self.proxy)
        self.allUserTable.setSelectionModel(
            customSelectionModel.CustomSelectionModel(self, self.allUserTable.model())
        )
        QApplication.restoreOverrideCursor()

    # Moves all selected users in both tables to the other table
    def moveUsers(self, qtVar=-1, selected=True, database=True):
        self.currentUserTable.setSortingEnabled(False)
        self.availableUserTable.setSortingEnabled(False)

        if selected:
            if self.availableUserTable.isVisible():
                selectedAvailable = [
                    self.availableUserTable.model().item(x.row(), 0).text()
                    for x in self.availableUserTable.selectionModel().selectedIndexes()
                ]
                for index in self.availableUserTable.selectionModel().selectedIndexes():
                    self.availableUserTable.model().takeRow(index.row())
            else:
                selectedAvailable = [
                    self.allUserTableModel.item(
                        self.allUserTable.model().mapToSource(x).row(), 0
                    ).text()
                    for x in self.allUserTable.selectionModel().selectedIndexes()
                ]
            for username in selectedAvailable:
                user = self.userApi.getUserByUsername(username)
                self.parent.currentUsers.append(UserInfo(user))

        if database:
            currentAvailable = [
                self.currentUserTable.item(x.row(), 0).text()
                for x in self.currentUserTable.selectionModel().selectedIndexes()
            ]
            for username in currentAvailable:
                for user in self.parent.currentUsers:
                    if user.username == username:
                        self.parent.currentUsers.remove(user)
                        self.allUserTableModel.appendRow(
                            [
                                QStandardItem(user.getUsername()),
                                QStandardItem(user.getFirstName()),
                                QStandardItem(user.getLastName()),
                                QStandardItem(user.getEmail()),
                            ]
                        )
        self.updateCurrentUsers()
        self.filterAllUserTable()
        if self.availableUserTable.isVisible():
            self.updateAvailableUsers()
        self.availableUserTable.setSortingEnabled(True)
        self.currentUserTable.setSortingEnabled(True)

    # Move highlighted users out of user database and into currentUsers table
    def moveToCurrent(self):
        self.moveUsers(selected=True, database=False)

    # Move highlighted users out of currentUsers table and into the database
    def moveToDatabase(self):
        self.moveUsers(selected=False, database=True)

    # Sets up a typable filter to parse users
    def addFilter(self, text, column):
        if column in self.filters and text == self.filters[column]:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.filters[column] = text
        for key in self.filters:
            if key == 0:
                self.proxy.setUsernameFilter(str(self.filters[key]).lower())
            elif key == 1:
                self.proxy.setFirstFilter(str(self.filters[key]).lower())
            elif key == 2:
                self.proxy.setLastFilter(str(self.filters[key]).lower())
            elif key == 3:
                self.proxy.setEmailFilter(str(self.filters[key]).lower())
        QApplication.restoreOverrideCursor()

    # Reverts the changes made in the gui
    def revertChanges(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        # Appends the users back into the Current Users table
        self.parent.restoreCurrentUsers()
        self.updateCurrentUsers()
        self.updateAvailableUsers()
        QApplication.restoreOverrideCursor()

    # Adds the users back to the allUser table when switching experiments
    def experimentSwitched(self):
        for user in self.parent.currentUsers:
            temp = self.allUserTableModel.findItems(
                user.getUsername(), Qt.MatchExactly, 0
            )
            if len(temp) > 1 or user.getUsername() in self.parent.beamlineManagers:
                continue
            elif len(temp) == 0:
                self.allUserTableModel.appendRow(
                    [
                        QStandardItem(user.getUsername()),
                        QStandardItem(user.getFirstName()),
                        QStandardItem(user.getLastName()),
                        QStandardItem(user.getEmail()),
                    ]
                )

    def filterAllUserTable(self):
        usernames = []
        for x in self.parent.currentUsers:
            username = x.getUsername()
            usernames.append(username)

        for username in usernames:
            temp = self.allUserTableModel.findItems(username, Qt.MatchExactly, 0)
            for t in temp:
                self.allUserTableModel.removeRow(t.row())
        self.allUserTable.clearSelection()
        self.allUserTable.clearFocus()

    def refreshGen(self):
        self.parent.setTab(self.parent.genParamsTab)
        self.parent.genParamsTab.fillUser()
        self.parent.genParamsTab.saveUsers()

    # Catches indicator change from freezeTable and makes sure that there is an empty row under the filters
    def sortCatcher(self, sortOrder):
        origin = self.allUserTable.verticalHeader().logicalIndex(0)
        if sortOrder == Qt.AscendingOrder:
            self.allUserTable.verticalHeader().moveSection(
                self.allUserTable.verticalHeader().count() - 1, origin
            )
        else:
            self.allUserTable.verticalHeader().moveSection(0, origin)

    # Toggle between showing proposals and esafs
    def proposalDBToggle(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.allUserTable.clearSelection()
        self.allUserTable.clearFocus()
        self.availableUserTable.clearSelection()
        self.availableUserTable.clearFocus()
        if self.parent.useEsaf == 1:
            self.parent.useEsaf = 0
            self.propToggle.setText("Show Esafs")
        else:
            if self.parent.esafSector != 0:
                self.parent.useEsaf = 1
                self.propToggle.setText("Show Proposals")
            else:
                self.noEsafDialog()
        self.updateDropdown()
        self.updateAvailableUsers()
        self.updateRun()
        QApplication.restoreOverrideCursor()

    # Stores the user changes to the parent
    def sendUsers(self, users):
        self.parent.allUsers = users

    # Manually updates the tableView
    def updateView(self, index):
        if self.allUserTable.isVisible():
            self.allUserTable.update(index)
        else:
            self.availableUserTable.update(index)
        self.currentUserTable.update(index)

    # Signals the parent to handle the right click event
    def contextMenuEvent(self, event):
        if self.currentUserTable.underMouse():
            self.parent.handleRightClickMenu(self.currentUserTable, event)
        else:
            if self.allUserTable.isVisible():
                self.parent.handleRightClickMenu(self.allUserTable, event)
            else:
                self.parent.handleRightClickMenu(self.availableUserTable, event)

    # Returns the tables on this tab
    def getTables(self):
        tables = [self.currentUserTable, self.allUserTable, self.availableUserTable]
        return tables

    # Error dialog for parsing additional parameters field
    def noRunErrorDialog(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText("Unable to fetch run")
        msg.setInformativeText(
            "Alternatively, try to find users by filtering the All User table"
        )
        msg.setWindowTitle("DM Warning")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    # Error dialog for adding a user that is already in an experiment
    def userInExpErrorDialog(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText("User already in experiment")
        msg.setWindowTitle("DM Warning")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    # Error dialog to alert the user there is no esaf sector set
    def noEsafDialog(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText("No Esaf sector set")
        msg.setInformativeText(
            "Please ensure the environment variables are set correctly if you wish to use esaf"
        )
        msg.setWindowTitle("DM Warning")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()


class GetUsersThread(QThread):
    sendUsers = pyqtSignal(object, name="sendUsers")

    def __init__(self, userApi):
        QThread.__init__(self)
        self.userApi = userApi

    def __del__(self):
        self.wait()

    def run(self):
        try:
            allUsers = self.userApi.getUsers()
        except CommunicationError as exc:
            log.error(exc)
            allUsers = []
        self.sendUsers.emit(allUsers)
