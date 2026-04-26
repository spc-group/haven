#!/usr/bin/env python

import datetime
import json
import os
import re
import traceback

from dm import ConfigurationError
from dm.common.constants.dmEsafConstants import DM_ESAF_ID_KEY, DM_GUP_ID_KEY
from dm.common.constants.dmExperimentConstants import (
    DM_END_DATE_KEY,
    DM_EXPERIMENT_ID_KEY,
    DM_EXPERIMENT_NAME_KEY,
    DM_EXPERIMENT_TYPE_KEY,
    DM_EXPERIMENT_USERNAME_LIST_KEY,
    DM_FINALIZATION_KEY,
    DM_INITIALIZATION_KEY,
    DM_ROOT_PATH_KEY,
    DM_START_DATE_KEY,
)
from dm.common.constants.dmObjectLabels import (
    DM_BEAMLINE_NAME_KEY,
    DM_DESCRIPTION_KEY,
    DM_EXIT_STATUS_KEY,
    DM_ID_KEY,
    DM_NAME_KEY,
    DM_TYPE_NAME_KEY,
    DM_VERBOSE_KEY,
)
from dm.common.constants.dmProcessingConstants import DM_EXPERIMENT_FILE_PATH_KEY
from dm.common.constants.dmRole import DM_USER_EXPERIMENT_ROLE
from dm.common.constants.dmServiceConstants import DM_SERVICE_TYPE_DAQ
from dm.common.constants.experimentIsolationOption import ExperimentIsolationOption
from dm.common.exceptions.dmException import DmException
from dm.common.exceptions.invalidRequest import InvalidRequest
from dm.common.exceptions.objectAlreadyExists import ObjectAlreadyExists
from dm.common.objects.dataDirectoryUrlFactory import DataDirectoryUrlFactory
from dm.common.utility.configurationManager import ConfigurationManager
from dm.common.utility.timeUtility import TimeUtility
from PyQt5.QtCore import QDate, QRegularExpression, QSize, Qt
from PyQt5.QtGui import QFont, QIcon, QPalette, QRegularExpressionValidator
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCalendarWidget,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .apiFactory import ApiFactory
from .subclasses import customSelectionModel, customStyledDelegate, databaseStats
from .subclasses.daqParams import DaqParams
from .subclasses.experimentIsolationWizard import ExperimentIsolationWizard
from .subclasses.style import DM_FONT_ARIAL_KEY, DM_GUI_LIGHT_GREY, DM_GUI_WHITE
from .subclasses.uploadParams import UploadParams


# Define the experiments tab content:
class GenParamsTab(QWidget):
    FILE_UPLOAD_FILTER_DIRECTORY = "Directory(*)"
    FILE_UPLOAD_FILTER_FILE = "File(*)"
    START_KEY = "start"
    END_KEY = "end"
    PROTOCOL_REGEX = "^[A-z]+:\\/\\/[A-z]+"

    STORAGE_PATH_OPTION_USE_AS_DIRECTORY = "Use Path As Directory"

    FILE_UPLOAD_FILTER = [FILE_UPLOAD_FILTER_DIRECTORY, FILE_UPLOAD_FILTER_FILE]

    def __init__(self, stationName, parent, id=-1):
        super(GenParamsTab, self).__init__(parent)
        self.stationName = stationName
        self.parent = parent
        self.experimentDsApi = ApiFactory.getInstance().getExperimentDsApi()
        self.experimentDaqApi = ApiFactory.getInstance().getExperimentDaqApi()
        self.fileCatApi = ApiFactory.getInstance().getFileCatApi()
        self.userApi = ApiFactory.getInstance().getUserDsApi()
        self.genParamsTabLayout()
        self.fillParams()
        self.dataDirectoryUrlFactory = DataDirectoryUrlFactory.createFromEnvironment()

    def getDataDirectory(self, dataDirectory: str) -> str:
        url = self.dataDirectoryUrlFactory.createUrl(dataDirectory)
        return str(url)

    # Sets up the tab's layout, each block is a row
    def genParamsTabLayout(self):
        grid = QGridLayout()
        self.dialog = None  # reference for dialogs
        labelFont = QFont(DM_FONT_ARIAL_KEY, 18, QFont.Bold)
        self.titleLbl = QLabel(self.stationName + " Settings", self)
        self.titleLbl.setAlignment(Qt.AlignCenter)
        self.titleLbl.setFont(labelFont)
        grid.addWidget(self.titleLbl, 0, 0, 1, 4)

        self.fileBtn = QPushButton("View Files", self)
        self.fileBtn.setFocusPolicy(Qt.NoFocus)
        self.fileBtn.clicked.connect(lambda: self.parent.setTab(self.parent.fileTab))

        self.fileStats = QPushButton("File Collection Stats", self)
        self.fileStats.clicked.connect(self.fileStatDialog)
        self.fileStats.setFocusPolicy(Qt.NoFocus)

        vboxTop = QVBoxLayout()
        vboxTop.addWidget(self.fileBtn)
        vboxTop.addWidget(self.fileStats)
        grid.addLayout(vboxTop, 0, 1, Qt.AlignRight)

        self.backBtn = QPushButton("Back", self)
        self.backBtn.setFocusPolicy(Qt.NoFocus)
        self.backBtn.clicked.connect(
            lambda: self.parent.setTab(self.parent.experimentsTab)
        )
        self.backBtn.setMinimumWidth(100)
        grid.addWidget(self.backBtn, 0, 0, Qt.AlignLeft)

        nameLabel = QLabel("Name:")
        self.nameField = QLineEdit()
        self.nameField.setPlaceholderText(DM_NAME_KEY.title())
        self.nameField.setValidator(
            QRegularExpressionValidator(
                QRegularExpression("[^#%&} {\\\\<>*?/$!:@'\"]+")
            )
        )
        self.nameField.textChanged.connect(self.saveFieldsChanged)
        calIcon = QIcon(":/icons/calendar.svg")
        wrenchIcon = QIcon(":/icons/wrench.svg")
        self.daqConfig = QPushButton()
        self.daqConfig.setFocusPolicy(Qt.NoFocus)
        self.daqConfig.setIcon(wrenchIcon)
        self.daqConfig.setIconSize(QSize(15, 15))
        self.daqConfig.setMaximumWidth(50)
        self.daqConfig.clicked.connect(lambda: self.toggleParams(DM_SERVICE_TYPE_DAQ))
        self.uploadConfig = QPushButton()
        self.uploadConfig.setFocusPolicy(Qt.NoFocus)
        self.uploadConfig.setIcon(wrenchIcon)
        self.uploadConfig.setIconSize(QSize(15, 15))
        self.uploadConfig.setMaximumWidth(50)
        self.uploadConfig.clicked.connect(lambda: self.toggleParams("upload"))

        startLabel = QLabel("Start Date:")
        self.startDateField = QDateEdit()
        self.startDateField.setDate(
            QDate.fromString(
                datetime.date.today().strftime(TimeUtility.GMT_FORMAT_SHORT),
                TimeUtility.PYQT_FORMAT_YMD,
            )
        )
        self.startDateField.dateChanged.connect(self.saveFieldsChanged)
        self.startBrowse = QPushButton()
        self.startBrowse.setFocusPolicy(Qt.NoFocus)
        self.startBrowse.setIcon(calIcon)
        self.startBrowse.setMaximumWidth(50)
        self.startBrowse.clicked.connect(lambda: self.toggleDate(self.START_KEY))

        endLabel = QLabel("End Date:")
        self.endDateField = QDateEdit()
        self.endDateField.setDate(
            QDate.fromString(
                datetime.date.today().strftime(TimeUtility.GMT_FORMAT_SHORT),
                TimeUtility.PYQT_FORMAT_YMD,
            )
        )
        self.endDateField.dateChanged.connect(self.saveFieldsChanged)
        self.endBrowse = QPushButton()
        self.endBrowse.setFocusPolicy(Qt.NoFocus)
        self.endBrowse.setIcon(calIcon)
        self.endBrowse.setMaximumWidth(50)
        self.endBrowse.clicked.connect(lambda: self.toggleDate(self.END_KEY))

        typeLabel = QLabel("Type:")
        self.typeDropdown = QComboBox(self)
        self.typeDropdown.setFocusPolicy(Qt.NoFocus)
        for type in self.parent.allowedExperimentTypes:
            self.typeDropdown.addItem(type)
        self.typeDropdown.currentIndexChanged.connect(self.saveFieldsChanged)

        descLabel = QLabel("Description:")
        self.descField = QLineEdit()
        self.descField.setPlaceholderText("Description")
        self.descField.textChanged.connect(self.saveFieldsChanged)

        rootPathLabel = QLabel("Storage Root Path")
        self.rootPathField = QLineEdit()
        self.rootPathField.setPlaceholderText("Storage Root Path")
        self.rootPathField.textChanged.connect(self.saveFieldsChanged)

        self.currentUserTable = QTableWidget()
        alternate = QPalette()
        alternate.setColor(QPalette.AlternateBase, DM_GUI_LIGHT_GREY)
        alternate.setColor(QPalette.Base, DM_GUI_WHITE)
        self.currentUserTable.setAlternatingRowColors(True)
        self.currentUserTable.setPalette(alternate)
        self.currentUserTable.setItemDelegate(
            customStyledDelegate.CustomStyledDelegate(self.currentUserTable, self)
        )
        self.currentUserTable.setSelectionModel(
            customSelectionModel.CustomSelectionModel(
                self, self.currentUserTable.model()
            )
        )

        self.toUserBtn = QPushButton("Modify Users", self)
        self.toUserBtn.setFocusPolicy(Qt.NoFocus)
        self.toUserBtn.clicked.connect(self.checkExp)
        self.toUserBtn.setMaximumWidth(130)

        self.saveSettingsBtn = QPushButton("Save", self)
        self.saveSettingsBtn.setFocusPolicy(Qt.NoFocus)
        self.saveSettingsBtn.clicked.connect(self.updateParams)
        self.saveSettingsBtn.setMaximumWidth(130)
        self.saveSettingsBtn.setDisabled(True)

        dataLabel = QLabel("Data Directory or Single File Path:")
        self.dataPathLineEdit = QLineEdit()
        self.dataPathLineEdit.textChanged.connect(self.dataPathLineEditTextChanged)
        self.dataPathLineEdit.setPlaceholderText("Data Directory or Single File Path")
        self.dataPathLineEdit.setToolTip(
            "Data Path or Single File Path for the files that user desires to upload. For single file change file type in browse menu."
        )
        self.fileBrowserBtn = QPushButton("Browse", self)
        self.fileBrowserBtn.setFocusPolicy(Qt.NoFocus)
        self.fileBrowserBtn.clicked.connect(self.getFileSystem)

        self.singleFileStoragePathLabel = QLabel(
            "Experiment File Path (For Single File Upload):"
        )
        self.singleFileStoragePathComboBox = QComboBox()
        self.singleFileStoragePathComboBox.setToolTip(
            "The directory structure that will be stored along with the single file."
        )
        self.singleFileStoragePathLabel.hide()
        self.singleFileStoragePathComboBox.hide()

        taskInfo = QLabel("Additional Parameters:")
        self.daqField = QLineEdit()
        self.daqField.setToolTip(
            "For example: a workflow name parameter can be provided for processing every file."
        )
        self.daqField.setPlaceholderText("Param1:Value1,Param2:Value2, ...")

        beamlineName = ConfigurationManager.getInstance().get(DM_BEAMLINE_NAME_KEY)
        # check if isolation settings configured for station and in daq service
        # self.isExperimentIsolationEnabled = (self.parent.configManager.hasExperimentIsolationSettingsFile() and
        #     self.experimentDaqApi.isConfiguredForIsolation(beamlineName))
        self.isExperimentIsolationEnabled = False

        # add isolation buttons
        if self.isExperimentIsolationEnabled:
            self.initBtn = QPushButton("Initialize", self)
            self.initBtn.setFocusPolicy(Qt.NoFocus)
            self.initBtn.clicked.connect(
                lambda: self.isolateExperiment(DM_INITIALIZATION_KEY)
            )
            self.initBtn.setMaximumWidth(130)

            self.finalBtn = QPushButton("Finalize", self)
            self.finalBtn.setFocusPolicy(Qt.NoFocus)
            self.finalBtn.clicked.connect(
                lambda: self.isolateExperiment(DM_FINALIZATION_KEY)
            )
            self.finalBtn.setMaximumWidth(130)

        self.startDaqBtn = QPushButton("Start DAQ", self)
        self.startDaqBtn.setFocusPolicy(Qt.NoFocus)
        self.startDaqBtn.clicked.connect(self.startDaq)
        self.startDaqBtn.setMaximumWidth(130)

        self.startUploadBtn = QPushButton("Start Upload", self)
        self.startUploadBtn.setFocusPolicy(Qt.NoFocus)
        self.startUploadBtn.clicked.connect(self.startUpload)
        self.startUploadBtn.setMaximumWidth(130)

        hRow1 = QHBoxLayout()
        hRow1.addWidget(startLabel)
        hRow1.addWidget(endLabel)

        hRow2 = QHBoxLayout()
        hRow2.addWidget(self.startDateField)
        hRow2.addWidget(self.startBrowse)
        hRow2.addWidget(self.endDateField)
        hRow2.addWidget(self.endBrowse)

        hRow3 = QHBoxLayout()
        hRow3.addWidget(self.saveSettingsBtn)
        hRow3.addWidget(self.toUserBtn)

        vColumn1 = QVBoxLayout()
        vColumn1.addWidget(nameLabel)
        vColumn1.addWidget(self.nameField)
        vColumn1.addLayout(hRow1)
        vColumn1.addLayout(hRow2)
        vColumn1.addWidget(typeLabel)
        vColumn1.addWidget(self.typeDropdown)
        vColumn1.addWidget(descLabel)
        vColumn1.addWidget(self.descField)
        vColumn1.addWidget(rootPathLabel)
        vColumn1.addWidget(self.rootPathField)
        grid.addLayout(vColumn1, 2, 0)

        grid.addLayout(hRow3, 3, 0, 1, 2)

        hRow6 = QHBoxLayout()
        hRow6.addWidget(self.dataPathLineEdit)
        hRow6.addWidget(self.fileBrowserBtn)

        hRow7 = QHBoxLayout()
        hRow7.addWidget(self.daqField)

        vColumn5 = QVBoxLayout()
        vColumn5.addWidget(dataLabel)
        vColumn5.addLayout(hRow6)
        vColumn5.addWidget(self.singleFileStoragePathLabel)
        vColumn5.addWidget(self.singleFileStoragePathComboBox)
        vColumn5.addWidget(taskInfo)
        vColumn5.addLayout(hRow7)
        vColumn5.setAlignment(Qt.AlignTop)

        # container for daq options which should be hidden
        # for unsaved experiment
        self.hideFrame = QFrame()
        hideBox = QVBoxLayout()
        self.hideFrame.setLayout(hideBox)

        hRow4 = QHBoxLayout()
        hRow4.addLayout(vColumn5)

        hRow5 = QHBoxLayout()
        hRow5.addStretch()

        if self.isExperimentIsolationEnabled:
            hRow5.addWidget(self.initBtn)
            hRow5.addStretch()

        hRow5.addWidget(self.startDaqBtn)
        hRow5.addWidget(self.daqConfig)
        hRow5.addStretch()
        hRow5.addWidget(self.startUploadBtn)
        hRow5.addWidget(self.uploadConfig)
        hRow5.addStretch()

        if self.isExperimentIsolationEnabled:
            hRow5.addWidget(self.finalBtn)
            hRow5.addStretch()

        hideBox.addLayout(hRow4)
        hideBox.addLayout(hRow5)
        grid.addWidget(self.hideFrame, 4, 0, 1, 2)

        vColumn2 = QVBoxLayout()
        vColumn2.addWidget(self.currentUserTable)

        grid.addLayout(vColumn2, 2, 1)

        self.calendarPicker = QCalendarWidget()
        self.calendarPicker.clicked.connect(self.setDate)
        self.calendarPicker.setGridVisible(True)
        self.calendarPicker.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.calendarPicker.setVisible(False)
        self.calendarPicker.a = lambda: None
        grid.addWidget(self.calendarPicker, 2, 1)

        self.setLayout(grid)

    # Fills ui with any known information, most is gotten from selecting an experiment/proposal
    def fillParams(self):
        # Initialize daq and upload configuration for default settings
        self.daqDialog = DaqParams(self, {})
        self.uploadDialog = UploadParams(self, {})

        # experiment has been saved
        if DM_NAME_KEY in self.parent.generalSettings:
            self.titleLbl.setText(
                self.parent.generalSettings[DM_NAME_KEY] + " Settings"
            )
            self.fileBtn.setDisabled(False)
            self.fileStats.setDisabled(False)
            self.hideFrame.show()
            if self.isExperimentIsolationEnabled:
                self.initBtn.setDisabled(False)
                self.initBtn.setToolTip(
                    "Perform experiment initialization including modification of user permissions"
                )
                self.finalBtn.setDisabled(False)
                self.finalBtn.setToolTip(
                    "Perform experiment finalization including modification of user permissions"
                )
        # new experiment has not been saved
        else:
            self.titleLbl.setText(self.stationName + " Settings")
            self.fileBtn.setDisabled(True)
            self.fileStats.setDisabled(True)
            self.nameField.clear()
            self.hideFrame.hide()
            if self.isExperimentIsolationEnabled:
                self.initBtn.setDisabled(True)
                self.initBtn.setToolTip("Save experiment before initializing.")
                self.finalBtn.setDisabled(True)
                self.finalBtn.setToolTip("Save experiment before finalizing.")
        self.startDateField.setDate(
            QDate.fromString(
                datetime.date.today().strftime(TimeUtility.GMT_FORMAT_SHORT),
                TimeUtility.PYQT_FORMAT_YMD,
            )
        )
        self.endDateField.setDate(
            QDate.fromString(
                datetime.date.today().strftime(TimeUtility.GMT_FORMAT_SHORT),
                TimeUtility.PYQT_FORMAT_YMD,
            )
        )
        self.descField.clear()
        self.dataPathLineEdit.clear()

        if not self.parent.generalSettings.get(DM_ROOT_PATH_KEY):
            self.parent.generalSettings[DM_ROOT_PATH_KEY] = ""

        for key in self.parent.generalSettings:
            if key == DM_NAME_KEY:
                self.nameField.setText(self.parent.generalSettings.get(key))
            elif key == DM_START_DATE_KEY:
                self.startDateField.setDate(self.parent.generalSettings.get(key))
            elif key == DM_END_DATE_KEY:
                self.endDateField.setDate(self.parent.generalSettings.get(key))
            elif key == DM_EXPERIMENT_TYPE_KEY:
                index = self.typeDropdown.findText(
                    self.parent.generalSettings.get(key).get(DM_NAME_KEY)
                )
                self.typeDropdown.setCurrentIndex(index)
            elif key == DM_DESCRIPTION_KEY:
                self.descField.setText(self.parent.generalSettings.get(key))
            elif key == DM_ROOT_PATH_KEY:
                self.rootPathField.setText(self.parent.generalSettings.get(key))

        if self.endDateField.text() == datetime.date.today().strftime(
            TimeUtility.GMT_FORMAT_SHORT
        ) and self.startDateField.text() != datetime.date.today().strftime(
            TimeUtility.GMT_FORMAT_SHORT
        ):
            self.endDateField.setDate(
                self.parent.generalSettings.get(DM_START_DATE_KEY)
            )
        # Set up the current users table
        self.fillUser()

        # Hide until a single file path selection is made.
        self.singleFileStoragePathComboBox.hide()
        self.singleFileStoragePathLabel.hide()

        self.disableButtons()

    def fillUser(self):
        self.currentUserTable.clearSelection()
        self.currentUserTable.setSortingEnabled(False)
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
            try:
                rowUsername.setData(Qt.UserRole, experimenter.getID())
            except ValueError:
                pass

            rowFirstName = QTableWidgetItem(experimenter.getFirstName())
            rowLastName = QTableWidgetItem(experimenter.getLastName())
            try:
                rowEmail = QTableWidgetItem(experimenter.getEmail())
            except KeyError:
                rowEmail = QTableWidgetItem("")
            self.currentUserTable.setItem(i, 0, rowUsername)
            self.currentUserTable.setItem(i, 1, rowFirstName)
            self.currentUserTable.setItem(i, 2, rowLastName)
            self.currentUserTable.setItem(i, 3, rowEmail)
            i += 1

        self.currentUserTable.horizontalHeader().setStretchLastSection(True)
        self.currentUserTable.setSortingEnabled(True)

    # Updates the experiment information to match what is supplied by the GUI
    def updateParams(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)

        if DM_NAME_KEY in self.parent.generalSettings:
            self.titleLbl.setText(
                self.parent.generalSettings.get(DM_NAME_KEY) + " Settings"
            )

        # new experiment
        experimentId = self.parent.generalSettings.get(DM_ID_KEY)

        if experimentId is None:
            self.saveNewExperiment()
        else:
            experimentName = self.parent.generalSettings.get(DM_NAME_KEY)

            if self.parent.experimentsTab.canUpdateExperiment(experimentName):
                changes = self.getChanges()
                updateSummary = f"You are about to update experiment: '{experimentName}' with the following changes: {changes}"
                newParams = self.getNewParamsFromChanges(experimentId, changes)
                self.verifyUpdateDialog(updateSummary, newParams)
                # Reload newly saved item into UI
                self.parent.experimentsTab.setExperimentById(experimentId)
            else:
                self.cannotUpdateErrorDialog()

        QApplication.restoreOverrideCursor()

    # check if any of the saveable fields have changed
    def getChanges(self):
        changes = ""
        if self.parent.generalSettings.get(DM_NAME_KEY) != self.nameField.text():
            changes += self._appendChange(
                DM_NAME_KEY,
                self.parent.generalSettings.get(DM_NAME_KEY),
                self.nameField.text(),
            )
        if self.parent.generalSettings.get(DM_DESCRIPTION_KEY) != self.descField.text():
            changes += self._appendChange(
                DM_DESCRIPTION_KEY,
                self.parent.generalSettings.get(DM_DESCRIPTION_KEY),
                self.descField.text(),
            )
        if (
            self.parent.generalSettings.get(DM_ROOT_PATH_KEY)
            != self.rootPathField.text()
        ):
            changes += self._appendChange(
                DM_ROOT_PATH_KEY,
                self.parent.generalSettings.get(DM_ROOT_PATH_KEY),
                self.rootPathField.text(),
            )

        expType = self.parent.generalSettings.get(DM_EXPERIMENT_TYPE_KEY)
        if expType is not None:
            expType = expType.get(DM_NAME_KEY)
        if expType is None:
            expType = ""
        if expType != self.typeDropdown.currentText():
            changes += self._appendChange(
                DM_EXPERIMENT_TYPE_KEY, expType, self.typeDropdown.currentText()
            )

        oldStartDate = self.parent.generalSettings.get(DM_START_DATE_KEY)
        if oldStartDate != self.startDateField.date():
            oldStartDate = (
                str(oldStartDate) if oldStartDate is None else oldStartDate.toString()
            )
            changes += self._appendChange(
                DM_START_DATE_KEY, oldStartDate, self.startDateField.date().toString()
            )

        oldEndDate = self.parent.generalSettings.get(DM_END_DATE_KEY)
        if oldEndDate != self.endDateField.date():
            oldEndDate = (
                str(oldEndDate) if oldEndDate is None else oldEndDate.toString()
            )
            changes += self._appendChange(
                DM_END_DATE_KEY, oldEndDate, self.endDateField.date().toString()
            )

        return changes

    # format change message
    def _appendChange(self, attibuteName, oldSetting, newSetting):
        return f'\n--- {attibuteName}: "{oldSetting}" --> "{newSetting}"'

    # converts string of changed params (for gui dialog) to dict (for api call)
    def getNewParamsFromChanges(self, experimentId, changes):
        newParams = {DM_EXPERIMENT_ID_KEY: experimentId}
        if DM_NAME_KEY in changes:
            name = self.nameField.text()
            self.parent.generalSettings[DM_NAME_KEY] = name
            newParams[DM_EXPERIMENT_NAME_KEY] = name
        if DM_START_DATE_KEY in changes:
            startDate = self.startDateField.date()
            self.parent.generalSettings[DM_START_DATE_KEY] = startDate
            newParams[DM_START_DATE_KEY] = startDate.toString(
                TimeUtility.PYQT_FORMAT_DMY
            )
        if DM_END_DATE_KEY in changes:
            endDate = self.endDateField.date()
            self.parent.generalSettings[DM_END_DATE_KEY] = endDate
            newParams[DM_END_DATE_KEY] = endDate.toString(TimeUtility.PYQT_FORMAT_DMY)
        if DM_EXPERIMENT_TYPE_KEY in changes:
            expType = self.typeDropdown.currentText()
            self.parent.generalSettings[DM_EXPERIMENT_TYPE_KEY][DM_NAME_KEY] = expType
            newParams[DM_TYPE_NAME_KEY] = expType
        if DM_DESCRIPTION_KEY in changes:
            description = self.descField.text()
            self.parent.generalSettings[DM_DESCRIPTION_KEY] = description
            newParams[DM_DESCRIPTION_KEY] = description
        if DM_ROOT_PATH_KEY in changes:
            rootPath = self.rootPathField.text()
            self.parent.generalSettings[DM_ROOT_PATH_KEY] = rootPath
            newParams[DM_ROOT_PATH_KEY] = rootPath
        return newParams

    def saveNewExperiment(self):
        try:
            # GUI needs ability to specify globus group id
            globusGroupId = None
            name = self.nameField.text()
            storageName = None
            exp = self.experimentDsApi.addExperiment(
                name,
                self.stationName,
                self.typeDropdown.currentText(),
                self.descField.text(),
                self.rootPathField.text(),
                storageName,
                globusGroupId,
                self.startDateField.date().toString(TimeUtility.PYQT_FORMAT_DMY),
                self.endDateField.date().toString(TimeUtility.PYQT_FORMAT_DMY),
            )
        except ObjectAlreadyExists:
            self.nameInUseDialog()
        else:
            # grab esaf info which is not stored w experiment
            esafID = self.parent.generalSettings.get(DM_ESAF_ID_KEY)
            gupID = self.parent.generalSettings.get(DM_GUP_ID_KEY)
            if esafID:
                self.parent.setExperimentEsafId(name, esafID)
            if gupID:
                self.parent.setExperimentPropId(name, gupID)
            self.parent.generalSettings = exp.data
            self.parent.refreshTables()
            self.saveUsers()

            # Reload new experiment using standard method
            id = self.parent.generalSettings.get(DM_ID_KEY)
            self.parent.experimentsTab.setExperimentById(id)
            self.saveSettingsBtn.setDisabled(True)

    # Updates the experiment to include the current users
    def saveUsers(self):
        experimentId = self.parent.generalSettings.get(DM_ID_KEY)
        if experimentId is not None:
            try:
                experiment = self.experimentDsApi.getExperimentById(experimentId)
                userList = [
                    user for user in experiment.get(DM_EXPERIMENT_USERNAME_LIST_KEY)
                ]
                guiList = [user.getUsername() for user in self.parent.currentUsers]

                for user in userList:
                    if user not in guiList:
                        self.userApi.deleteUserExperimentRole(
                            user,
                            DM_USER_EXPERIMENT_ROLE,
                            self.parent.generalSettings.get(DM_NAME_KEY),
                            self.stationName,
                        )

                for user in self.parent.currentUsers:
                    if user.getUsername() not in userList:
                        self.userApi.addUserExperimentRole(
                            user.getUsername(),
                            DM_USER_EXPERIMENT_ROLE,
                            self.parent.generalSettings.get(DM_NAME_KEY),
                            self.stationName,
                        )
                self.parent.setTab(self.parent.genParamsTab)
            except ValueError:
                self.parent.setTab(self.parent.genParamsTab)
            QApplication.restoreOverrideCursor()

    # Starts a daq using the experiment that is currently selected, somewhat complicated text parsing to correctly
    # format the visible string into a dictionary.  Maybe clean this up at some point.
    def startDaq(self):
        if self.parent.generalSettings.get(DM_NAME_KEY) is None:
            self.saveExperimentDialog()
            return
        try:
            taskInfo = self.getUploadDaqConfiguration(self.daqDialog.params)
            self.experimentDaqApi.startDaq(
                self.parent.generalSettings.get(DM_NAME_KEY),
                self.getDataDirectory(self.dataPathLineEdit.text()),
                taskInfo,
            )
        except InvalidRequest:
            self.noStartErrorDialog(traceback.format_exc())
            return
        except DmException:
            self.paramParsingErrorDialog()
            return
        except SyntaxError:
            self.paramParsingErrorDialog()
            return
        self.parent.refreshTables()
        self.parent.tabs.setCurrentIndex(1)

    # Starts an upload using the experiment that is currently selected, somewhat complicated text parsing to correctly
    # format the visible string into a dictionary.  Maybe clean this up at some point.
    def startUpload(self):
        if self.parent.generalSettings.get(DM_NAME_KEY) is None:
            self.saveExperimentDialog()
            return
        try:
            taskInfo = self.getUploadDaqConfiguration(self.uploadDialog.params)
            dataDirectory = self.parseDataDirectory()

            if not self.isProcessAsDirectory():
                storagePath = str(self.singleFileStoragePathComboBox.currentText())
                taskInfo[DM_EXPERIMENT_FILE_PATH_KEY] = storagePath

            self.experimentDaqApi.upload(
                self.parent.generalSettings.get(DM_NAME_KEY), dataDirectory, taskInfo
            )
        except InvalidRequest:
            self.noStartErrorDialog(traceback.format_exc())
            return
        except DmException:
            self.paramParsingErrorDialog()
            return
        except SyntaxError:
            self.paramParsingErrorDialog()
            return
        self.parent.refreshTables()
        self.fileBtn.show()
        self.parent.tabs.setCurrentIndex(2)

    # parse data directory from data field
    def parseDataDirectory(self):
        dataPathLineEdit = str(self.dataPathLineEdit.text())

        # Single File specified for upload
        if not self.isProcessAsDirectory():
            storagePath = str(self.singleFileStoragePathComboBox.currentText())
            index = dataPathLineEdit.index(storagePath)
            return dataPathLineEdit[0 : index - 1]
        else:
            return self.getDataDirectory(dataPathLineEdit)

    def isProcessAsDirectory(self):
        storagePath = str(self.singleFileStoragePathComboBox.currentText())

        isDirStoragePath = (
            storagePath == GenParamsTab.STORAGE_PATH_OPTION_USE_AS_DIRECTORY
            or storagePath == ""
        )

        return isDirStoragePath

    def getUploadDaqConfiguration(self, configParams):
        additionalParametersDict = {}

        # Check if additional parameters were specified
        if len(self.daqField.text()) > 0:
            parameterList = re.split(",", str(self.daqField.text()))

            if parameterList.__len__() == 0:
                raise ConfigurationError

            additionalParametersDict = {}

            for parameter in parameterList:
                if parameter == "":
                    continue
                parameterSplit = re.split("=|:", parameter)
                if parameterSplit.__len__() != 2:
                    raise ConfigurationError

                additionalParametersDict[parameterSplit[0]] = parameterSplit[1]

        result = {}
        result.update(additionalParametersDict)
        result.update(configParams)
        return result

    def fileStatDialog(self):
        if DM_NAME_KEY in self.parent.generalSettings:
            self.dialog = databaseStats.DatabaseStats(
                self, self.parent.generalSettings[DM_NAME_KEY]
            )
            self.dialog.exec_()
            self.dialog = None
        else:
            self.saveExperimentDialog()

    # Check that the experiment is valid before adding users
    def checkExp(self):
        # if self.parent.generalSettings.get('name') is None:
        #    self.modifyUserDialog()
        #    return
        self.parent.setTab(self.parent.manageUsersTab)

    # Displays the file system for the user to navigate
    def getFileSystem(self):
        self.fileBrowserDialog = QFileDialog()
        dialog = self.fileBrowserDialog
        dialog.setOption(QFileDialog.DontUseNativeDialog, True)

        # Set default mode
        self.fileDialogFilterChanged(self.FILE_UPLOAD_FILTER_DIRECTORY)

        dialog.filterSelected.connect(self.fileDialogFilterChanged)

        if dialog.exec_():
            file = dialog.selectedFiles()[0]
            # Data text field text changed event will take over.
            self.dataPathLineEdit.setText(file)
        self.fileBrowserDialog = None

    def disableButtons(self):
        # disable the buttons that shouldn't ba clicked for an unsaved experiment
        buttons = [
            self.startDaqBtn,
            self.startUploadBtn,
            self.uploadConfig,
            self.daqConfig,
        ]
        for btn in buttons:
            btn.setDisabled(True)
            btn.setToolTip("Save experiment and choose data directory.")

    def dataPathLineEditTextChanged(self):
        dataPath = str(self.dataPathLineEdit.text())

        # text box was cleared
        if dataPath == "":
            self.singleFileStoragePathComboBox.clear()
            self.singleFileStoragePathLabel.hide()
            self.singleFileStoragePathComboBox.hide()
            self.disableButtons()

        elif os.path.exists(dataPath):
            self.startUploadBtn.setDisabled(False)
            self.startUploadBtn.setToolTip("Start upload")
            self.uploadConfig.setDisabled(False)
            self.uploadConfig.setToolTip("Configure upload settings")

            if not self.isDataPathALocalDirectory():
                self.daqConfig.setDisabled(True)
                self.startDaqBtn.setDisabled(True)

                self.singleFileStoragePathLabel.show()
                self.singleFileStoragePathComboBox.show()

                self.populateStoragePathOptions()
            else:
                self.daqConfig.setDisabled(False)
                self.daqConfig.setToolTip("Configure DAQ settings")
                self.startDaqBtn.setDisabled(False)
                self.startDaqBtn.setToolTip("Start DAQ")

                self.singleFileStoragePathComboBox.clear()
                self.singleFileStoragePathLabel.hide()
                self.singleFileStoragePathComboBox.hide()
        else:
            self.startUploadBtn.setDisabled(False)
            self.startUploadBtn.setToolTip("Start upload")
            self.uploadConfig.setDisabled(False)
            self.uploadConfig.setToolTip("Configure upload settings")
            self.daqConfig.setDisabled(False)
            self.daqConfig.setToolTip("Configure DAQ settings")
            self.startDaqBtn.setDisabled(False)
            self.startDaqBtn.setToolTip("Start DAQ")

            if dataPath.endswith("/"):
                self.singleFileStoragePathComboBox.clear()
                self.singleFileStoragePathLabel.hide()
                self.singleFileStoragePathComboBox.hide()
            else:
                self.singleFileStoragePathLabel.show()
                self.singleFileStoragePathComboBox.show()
                self.populateStoragePathOptions(dirOption=True)

        # chose directory but new unsaved experiment
        if DM_NAME_KEY not in self.parent.generalSettings:
            self.disableButtons()

    def saveFieldsChanged(self):
        name = str(self.nameField.text())
        # name not empty and is a new experiment or something changed
        if name != "" and (
            self.parent.generalSettings.get(DM_ID_KEY) is None
            or self.getChanges() != ""
        ):
            self.saveSettingsBtn.setDisabled(False)
        else:
            self.saveSettingsBtn.setDisabled(True)

    def populateStoragePathOptions(self, dirOption=False):
        self.singleFileStoragePathComboBox.clear()

        filePath = str(self.dataPathLineEdit.text())

        if self.doesDataPathSpecifyAProtocol():
            result = re.search(self.PROTOCOL_REGEX, filePath)
            filePath = filePath[result.end() :]

        pathParts = filePath.split("/")
        pathPartsCount = len(pathParts)

        storagePathOptions = []

        if dirOption:
            storagePathOptions.append(GenParamsTab.STORAGE_PATH_OPTION_USE_AS_DIRECTORY)

        for i in range(pathPartsCount - 1, 0, -1):
            storagePathOption = ""
            for part in pathParts[i:]:
                storagePathOption += part + "/"

            storagePathOption = storagePathOption[:-1]
            storagePathOptions.append(storagePathOption)

        self.singleFileStoragePathComboBox.addItems(storagePathOptions)

    def fileDialogFilterChanged(self, filter):
        if filter == self.FILE_UPLOAD_FILTER_DIRECTORY:
            self.fileBrowserDialog.setFileMode(QFileDialog.Directory)
            self.fileBrowserDialog.setOption(QFileDialog.ShowDirsOnly, True)
        else:
            self.fileBrowserDialog.setFileMode(QFileDialog.ExistingFile)
            self.fileBrowserDialog.setOption(QFileDialog.ShowDirsOnly, False)

        self.fileBrowserDialog.setNameFilters(self.FILE_UPLOAD_FILTER)
        self.fileBrowserDialog.selectNameFilter(filter)

    def isDataPathALocalDirectory(self) -> bool:
        dataPath = self.dataPathLineEdit.text()
        result = False

        if dataPath is not None:
            result = os.path.isdir(dataPath)

        return result

    def doesDataPathSpecifyAProtocol(self) -> bool:
        dataPath = self.dataPathLineEdit.text()
        result = False

        if dataPath is not None:
            match = re.search(self.PROTOCOL_REGEX, dataPath)
            result = match is not None

        return result

    # Calendar overlay to select date
    def toggleDate(self, fieldType=None):
        if fieldType:
            setattr(self.calendarPicker.a, "fieldType", fieldType)
        if self.calendarPicker.isVisible():
            self.calendarPicker.setVisible(False)
        else:
            self.calendarPicker.setVisible(True)

    # Returns the tables on this tab
    def getTables(self):
        tables = [self.currentUserTable]
        return tables

    # Popup to show the user common parameters
    def toggleParams(self, specifier):
        if specifier == DM_SERVICE_TYPE_DAQ:
            self.dialog = self.daqDialog
            self.daqDialog.exec_()
        else:
            self.dialog = self.uploadDialog
            self.uploadDialog.updateProcessAsDirectory(self.isProcessAsDirectory())
            self.uploadDialog.exec_()
        self.dialog = None

    # Updates the date
    def setDate(self):
        if self.sender().a.fieldType == self.START_KEY:
            self.startDateField.setDate(self.calendarPicker.selectedDate())
        else:
            self.endDateField.setDate(self.calendarPicker.selectedDate())
        if (
            self.endDateField.date() < self.startDateField.date()
            and self.sender().a.fieldType == self.END_KEY
        ):
            self.endDateField.setDate(self.startDateField.date())
            self.dateInvalidDialog()
        elif self.endDateField.date() < self.startDateField.date():
            self.endDateField.setDate(self.startDateField.date())
            self.toggleDate()
        else:
            self.toggleDate()

    # Manually updates the tableView
    def updateView(self, index):
        self.currentUserTable.update(index)

    # Signals the parent to handle the right click event
    def contextMenuEvent(self, event):
        self.parent.handleRightClickMenu(self.currentUserTable, event)

    def cannotUpdateErrorDialog(self):
        cannotUpdateNameMsg = QMessageBox()
        cannotUpdateNameMsg.setIcon(QMessageBox.Warning)
        cannotUpdateNameMsg.setWindowTitle("Cannot update experiment")
        cannotUpdateNameMsg.setText(
            "Experiment cannot be updated because it has a daq or upload still running."
        )
        QApplication.restoreOverrideCursor()
        cannotUpdateNameMsg.exec_()

    # dialog which shows users changes made and confirms they want to save changes
    def verifyUpdateDialog(self, updateSummary, updateParams):
        self.dialog = QMessageBox(
            QMessageBox.Question, "Proceed with update of experiment?", updateSummary
        )
        self.dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        response = self.dialog.exec_()
        self.dialog = None
        if response == QMessageBox.Yes:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                self.experimentDsApi.updateExperiment(**updateParams)
            except ObjectAlreadyExists:
                self.nameInUseDialog()
                QApplication.restoreOverrideCursor()
                return
            except InvalidRequest:
                # If none of these fields have been modified
                pass
            if self.parent.generalSettings.get(DM_NAME_KEY) is not None:
                self.titleLbl.setText(
                    self.parent.generalSettings.get(DM_NAME_KEY) + " Settings"
                )
            self.parent.refreshTables()
            self.saveUsers()

    # Error dialog to prevent the adding of users to a nonexistant experiment
    def modifyUserDialog(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText("No experiment to add users to")
        msg.setInformativeText("Save experiment details before adding users")
        msg.setWindowTitle("DM Warning")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    # Error dialog for parsing additional parameters field
    def paramParsingErrorDialog(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText("Error starting experiment")
        msg.setInformativeText(
            "Check that you used the key:value, format in your Addional Parameters field, "
            "have saved the experiment, have a data directory selected, and are not already running an "
            "experiment with this name."
        )
        msg.setWindowTitle("DM Warning")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    # Error dialog to tell the user when their experiment name is already taken
    def nameInUseDialog(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText("Experiment Name Taken")
        msg.setInformativeText("Please choose a different experiment name")
        msg.setWindowTitle("DM Warning")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    # Error dialog to inform the user they have picked an invalid date
    def dateInvalidDialog(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText("Date Invalid")
        msg.setInformativeText("The date that you have selected is invalid")
        msg.setWindowTitle("DM Warning")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    # Error dialog to inform the user they failed to start their experiment
    def noStartErrorDialog(self, stacktrace):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText("Failed to start experiment")
        msg.setInformativeText(
            "Please check that the station & beamline you are using is correct"
        )
        msg.setWindowTitle("DM Error")
        msg.setDetailedText(stacktrace)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    # get isolation options from users and call api
    def isolateExperiment(self, stage):
        options = self.getExperimentIsolationOptions(stage)
        if options:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                beamlineName = ConfigurationManager.getInstance().get(
                    DM_BEAMLINE_NAME_KEY
                )
                response = self.experimentDaqApi.isolateExperiment(
                    stage, beamlineName, options
                )
                if response.get(DM_EXIT_STATUS_KEY):
                    self.experimentIsolationDialog(str(response), stage, success=False)
                elif json.loads(options).get(DM_VERBOSE_KEY):
                    self.experimentIsolationDialog(str(response), stage, success=True)
            except Exception:
                self.experimentIsolationDialog(
                    traceback.format_exc(), stage, success=False
                )
            QApplication.restoreOverrideCursor()

    # get isolation options from user and match to what's expected by isolation script
    def getExperimentIsolationOptions(self, stage):
        # get known values to populate wizard
        expName = self.parent.generalSettings[DM_NAME_KEY]
        # change pyqt date object to datetime object
        qDate = self.parent.generalSettings[DM_START_DATE_KEY]
        date = datetime.date(qDate.year(), qDate.month(), qDate.day())
        dataDir = self.dataPathLineEdit.text()
        if dataDir:
            dataDir = self.getDataDirectory(dataDir)
        esafId = self.parent.getExperimentEsafId(expName)
        gupId = self.parent.getExperimentPropId(expName)
        self.dialog = ExperimentIsolationWizard(
            stage, expName, dataDir, esafId, gupId, date
        )
        # if user didn't cancel
        if self.dialog.exec_():
            options = self.dialog.getFields()
            options[ExperimentIsolationOption.DATA_DIR.value] = options.pop(
                "data directory"
            )
            # isolation script needs 'action' option to know which to perform init or final
            if stage == DM_FINALIZATION_KEY:
                options[ExperimentIsolationOption.DEST_DIR.value] = options.pop(
                    "destination directory"
                )
            self.dialog = None
            return json.dumps(options)
        self.dialog = None

    # Error dialog to inform user the init/finalize failed
    def experimentIsolationDialog(self, response, stage, success):
        self.dialog = QMessageBox()
        if success:
            self.dialog.setIcon(QMessageBox.Information)
            self.dialog.setText(f"Experiment {stage} completed successfully.")
            self.dialog.setWindowTitle("Success")
        else:
            self.dialog.setIcon(QMessageBox.Critical)
            self.dialog.setText(f"Experiment {stage.capitalize()} Error Occurred")
            self.dialog.setInformativeText(
                f"An error occured while performing experiment {stage}. Please check the necessary scripts are present and settings listed in settings tab are correct."
            )
            self.dialog.setWindowTitle("DM Error")
        self.dialog.setDetailedText(response)
        self.dialog.addButton(QMessageBox.Ok)
        self.dialog.exec_()
        self.dialog = None

    # Error dialog to ensure enough detail exists to make an experiment
    def saveExperimentDialog(self):
        self.dialog = QMessageBox()
        self.dialog.setIcon(QMessageBox.Warning)
        self.dialog.setText("More information needed")
        self.dialog.setInformativeText(
            "Please save the experiment with a name and type before proceeding"
        )
        self.dialog.setWindowTitle("DM Warning")
        self.dialog.setStandardButtons(QMessageBox.Ok)
        self.dialog.exec_()
        self.dialog = None
