#!/usr/bin/env python

# Python 2/3 compatibility block
from __future__ import print_function

import logging
import smtplib
import sys
from datetime import datetime
from email.mime.text import MIMEText
from time import sleep, time
from traceback import format_tb

from dm.common.constants.dmObjectLabels import DM_NAME_KEY
from dm.common.constants.dmStatus import DmStatus
from dm.common.exceptions.dmException import DmException
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QCursor, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QMenu,
    QMessageBox,
    QSplashScreen,
    QStackedLayout,
    QTabWidget,
    QWidget,
)

from haven import load_config

from ...main_window import FireflyMainWindow
from .addExperiment import AddExperimentTab
from .apiFactory import ApiFactory
from .daqsTab import DaqsTab
from .experimentsTab import ExperimentsTab
from .fileTab import FileTab
from .genParamsTab import GenParamsTab
from .manageUsersTab import ManageUsersTab
from .processingJobsTab import ProcessingJobsTab
from .settingsTab import SettingsTab
from .uploadsTab import UploadsTab
from .workflowTab import WorkflowTab

log = logging.getLogger("dm_tools")


class DmStationUi(FireflyMainWindow):

    LOCALHOST_KEY = "localhost"
    SUBJECT_KEY = "Subject"
    TO_KEY = "To"
    FROM_KEY = "From"

    def __init__(self):
        self.__configure()

        log.debug("Starting UI for DM Station: %s" % self.stationName)
        super(DmStationUi, self).__init__()

        self.ExperimentsTab = ExperimentsTab
        self.DaqsTab = DaqsTab
        self.UploadsTab = UploadsTab
        self.AddExperimentTab = AddExperimentTab
        self.ManageUsersTab = ManageUsersTab
        self.GenParamsTab = GenParamsTab
        self.FileTab = FileTab

        self.setWindowTitle("DM Station: %s" % self.stationName)
        self.setGeometry(0, 0, 800, 400)

        # Email address that the notification emails will list they are sent from
        self.dmEmail = "dmNoReply@aps.anl.gov"

        # Variable to hold the user instances
        self.currentUsers = []

        # Variable to hold the general settings
        self.generalSettings = {}

        # Variable to hold all users
        self.allUsers = {}

        # Variable to setup the allUserTable when the user gets to the manage users page
        self.setupAllTable = True

        self.onlyEsaf = 0

        self.expFileCount = 0

        # Variable to hold the proposals from the current run
        self.currentProposals = []

        # variable to store link between experiment name and esaf number used to create it
        self.experimentEsafIDs = {}

        # variable to store link between experiment name and esaf number used to create it
        self.experimentPropIDs = {}

        # Test the availability of APS DBs
        apiFactory = ApiFactory.getInstance()

        ESAF_FAIL_MODE = "BSS Only"

        try:
            self.experimentPropApi = apiFactory.getBssApsDbApi()
            currentRun = self.experimentPropApi.getCurrentRun().data[DM_NAME_KEY]
            self.currentProposals = self.experimentPropApi.listStationProposals(
                self.stationName, self.beamlineName, runName=currentRun
            )
        except DmException:
            ESAF_FAIL_MODE = "standalone"
            log.warning(
                "Failed to connect to APS BSS system. Continuing in ESAF only mode."
            )
            self.onlyEsaf = True

        esafFail = True
        log.debug("ESAF Sector %s" % self.esafSector)
        try:
            esafApi = apiFactory.getEsafApsDbApi()
            esafApi.listStationEsafs(
                self.stationName, self.beamlineName, datetime.today().year
            )
            esafFail = False
        except DmException:
            log.warning(
                "Failed to connect to APS ESAF system. Continuing "
                + ESAF_FAIL_MODE
                + " mode."
            )

        if esafFail:
            self.onlyEsaf = False
            self.useEsaf = False
            self.esafSector = None
        else:
            self.useEsaf = True

        # Variable to show what proposal set is being used
        self.proposalName = "Current Run"

        # Create a stacked layout to connect the various pages
        self.stackedLayout = QStackedLayout()
        self.stackedLayout.currentChanged.connect(self.currentChanged)

        # Create the tab windows
        self.experimentsTab = ExperimentsTab(self.stationName, self)
        self.daqsTab = DaqsTab(self.stationName, self)
        self.uploadsTab = UploadsTab(self.stationName, self)
        self.manageUsersTab = ManageUsersTab(self.stationName, self.beamlineName, self)
        self.genParamsTab = GenParamsTab(self.stationName, self)
        if self.beamlineName or self.onlyEsaf == 1:
            self.addExperimentTab = AddExperimentTab(
                self.stationName, self.beamlineName, self
            )
        self.fileTab = FileTab(self.stationName, self)
        self.workflowTab = WorkflowTab(self.stationName, self)
        self.processingJobsTab = ProcessingJobsTab(self.stationName, self)
        self.settingsTab = SettingsTab(self)

        # Add the windows to the stack.
        self.stackedLayout.addWidget(self.experimentsTab)
        self.stackedLayout.addWidget(self.manageUsersTab)
        self.stackedLayout.addWidget(self.genParamsTab)
        if self.beamlineName or self.onlyEsaf == 1:
            self.stackedLayout.addWidget(self.addExperimentTab)
        self.stackedLayout.addWidget(self.fileTab)
        self.stackedWidget = QWidget()
        self.stackedWidget.setLayout(self.stackedLayout)

        # Tabs for experiment list, daq, and uploads
        self.tabs = QTabWidget()
        self.tabs.addTab(self.stackedWidget, "Experiments")
        self.tabs.addTab(self.daqsTab, "DAQs")
        self.tabs.addTab(self.uploadsTab, "Uploads")

        # Hide until ready for release
        self.tabs.addTab(self.workflowTab, "Workflows")
        self.tabs.addTab(self.processingJobsTab, "Processing Jobs")
        settingsIcon = QIcon(":/icons/settings.svg")
        self.tabs.addTab(self.settingsTab, settingsIcon, "Settings")

        self.refreshDaqsTimer = QTimer()
        self.refreshDaqsTimer.timeout.connect(self.refreshDaqs)
        self.refreshUploadsTimer = QTimer()
        self.refreshUploadsTimer.timeout.connect(self.refreshUploads)
        self.refreshExperimentsTimer = QTimer()
        self.refreshExperimentsTimer.timeout.connect(self.refreshExperiments)
        self.refreshJobsTimer = QTimer()
        self.refreshJobsTimer.timeout.connect(self.refreshJobs)
        self.refreshWorkflowsTimer = QTimer()
        self.refreshWorkflowsTimer.timeout.connect(self.refreshWorkflows)
        self.setUpRefreshTimers()

        # Set a central widget to hold everything
        self.setCentralWidget(self.tabs)

        self.stackedLayout.setCurrentIndex(0)
        self.center()
        self.show()

    def __configure(self):
        config = load_config().data_management
        # allowedExperimentTypes = self.configManager.getAllowedExperimentTypes()
        self.stationName = config.station_name
        self.beamlineName = config.beamline
        self.esafSector = config.beamline.split("-")[0]
        self.beamlineManagers = []
        self.username, self.password = (config.username, config.password)
        self.dmAdminEmail = ""
        self.allowedExperimentTypes = ["25IDC", "25IDD", "TEST"]
        self.useEsaf = True
        if not self.stationName:
            log.error("DM_STATION_NAME environment variable is not defined.")
        # if not self.beamlineName:
        #     if self.esafSector:
        #         self.onlyEsaf = 1
        # if self.beamlineManagers:
        #     self.beamlineManagers = list(set(self.beamlineManagers.split(',')))

    # Centers window on the screen where the mouse is detected
    def center(self):
        frameGeo = self.frameGeometry()
        screen = QApplication.desktop().screenNumber(
            QApplication.desktop().cursor().pos()
        )
        screenCenter = QApplication.desktop().screenGeometry(screen).center()
        frameGeo.moveCenter(screenCenter)
        self.move(frameGeo.topLeft())

    # Signal that is called whenever the sub tab changes
    def currentChanged(self, index):
        newWidget = self.stackedLayout.widget(index)
        if newWidget == self.manageUsersTab:
            if self.setupAllTable:
                self.manageUsersTab.cacheUsers()
            self.manageUsersTab.updateCurrentUsers()
            self.manageUsersTab.updateAvailableUsers()
            self.setupAllTable = False
        elif newWidget == self.fileTab:
            FileTab.updateList(self.fileTab)

    # Run when experiment is switched
    def expSwitched(self):
        ManageUsersTab.experimentSwitched(self.manageUsersTab)

    # Gets the index of the current sub tab
    def getTab(self):
        return self.stackedLayout.currentIndex()

    # Gets the index of the current main tab
    def getMainTab(self):
        return self.tabs.currentIndex()

    # Used to change between tabs
    def setTab(self, tabObj):
        stack = None
        for i in range(self.stackedLayout.count()):
            tab = self.stackedLayout.widget(i)
            if tab == tabObj:
                stack = tab
                stackIdx = i
                break

        if stack is None:
            raise DmException("Unknown error occurred switching to: %s" % tabObj)

        # stack = self.stackedLayout.widget(stackIdx)
        tables = stack.getTables()
        for table in tables:
            self.clearSelection(table)
        self.stackedLayout.setCurrentIndex(stackIdx)

    # Clears selections from table
    def clearSelection(self, table):
        table.clearSelection()

    def setUpRefreshTimers(self):
        self.refreshDaqsTimer.stop()
        self.refreshExperimentsTimer.stop()
        self.refreshUploadsTimer.stop()
        self.refreshJobsTimer.stop()
        self.refreshWorkflowsTimer.stop()

        self._startRefreshTimer(
            self.refreshDaqsTimer, self.settingsTab.fetchRefCycleDaqs()
        )
        self._startRefreshTimer(
            self.refreshUploadsTimer, self.settingsTab.fetchRefCycleUploads()
        )
        self._startRefreshTimer(
            self.refreshExperimentsTimer, self.settingsTab.fetchRefCycleExperiments()
        )
        self._startRefreshTimer(
            self.refreshJobsTimer, self.settingsTab.fetchRefCycleJobs()
        )
        self._startRefreshTimer(
            self.refreshWorkflowsTimer, self.settingsTab.fetchRefCycleWorkflows()
        )

    def _startRefreshTimer(self, timer, seconds):
        # 0 means that no refresh cycle will occur
        if seconds != 0:
            interval = seconds * 1000
            timer.start(interval)

    def refreshExperiments(self):
        self.experimentsTab.updateList()

    def refreshDaqs(self):
        self.daqsTab.updateList()

    def refreshUploads(self):
        self.uploadsTab.updateList()

    def refreshJobs(self):
        self.processingJobsTab.updateList()

    def refreshWorkflows(self):
        self.workflowTab.updateList()

    # Refreshes the experiments, DAQ, and Uploads tables.
    def refreshTables(self):
        self.experimentsTab.updateList()
        self.daqsTab.updateList()
        self.uploadsTab.updateList()
        self.processingJobsTab.updateList()
        self.workflowTab.updateList()

    # Restores the currentUsers to match what was stored in the genParamsTab.
    def restoreCurrentUsers(self):
        self.experimentsTab.loadCurrentUsers()
        self.genParamsTab.fillUser()

    # Returns the selected index from within a table, this is used for the unique highlighting functionality
    def getSelectedIndex(self, table):
        selectedRows = []
        indexes = table.selectionModel().selectedIndexes()
        for index in indexes:
            selectedRows.append(index.row())
        return indexes, selectedRows

    # Capture the right click event and open a context menu
    def handleRightClickMenu(self, table, event, toggleDetailsAction=None):
        if table.selectionModel().selection().indexes():
            index = table.selectionModel().selection().indexes()[0]
            row, column = index.row(), index.column()
            menu = QMenu(self)

            if toggleDetailsAction:
                showDetailsAction = QAction("Show Details", self)
                showDetailsAction.triggered.connect(toggleDetailsAction)
                menu.addAction(showDetailsAction)

            copyAction = QAction("Copy", self)
            copyAction.triggered.connect(lambda: self.copyAction(row, column, table))
            menu.addAction(copyAction)
            menu.popup(QCursor.pos())

    def getExperimentEsafId(self, expName):
        return self.experimentEsafIDs.get(expName)

    def setExperimentEsafId(self, expName, esafId):
        self.experimentEsafIDs[expName] = esafId

    def getExperimentPropId(self, expName):
        return self.experimentPropIDs.get(expName)

    def setExperimentPropId(self, expName, propId):
        self.experimentPropIDs[expName] = propId

    def copyAction(self, row, column, table):
        clipboard = ""
        index = table.model().index(row, column)
        clipboard += str(index.data())
        sysclip = QApplication.clipboard()
        sysclip.setText(clipboard)

    def emailAdmin(self, text):
        msg = MIMEText(text)
        msg[self.SUBJECT_KEY] = self.stationName + " Error Report"
        msg[self.FROM_KEY] = self.dmEmail
        msg[self.TO_KEY] = self.dmAdminEmail

        s = smtplib.SMTP(self.LOCALHOST_KEY)
        s.sendmail(self.dmEmail, self.dmAdminEmail, msg.as_string())
        s.quit()

    def unhandledDialog(self, error):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText("Unexpected Error Occurred")
        msg.setInformativeText(
            "You encountered an error that has not been handled.  Please click the 'Notify Admin' button and it will be fixed shortly."
        )
        msg.setDetailedText(error)
        msg.setWindowTitle("DM Unexpected Error")
        notify = msg.addButton("Notify Admin", QMessageBox.YesRole)
        msg.addButton(QMessageBox.Cancel)
        msg.exec_()
        if msg.clickedButton() == notify:
            self.emailAdmin(error)
        QApplication.restoreOverrideCursor()


if __name__ == "__main__":
    try:
        print("""8888888b. 888b     d888         .d8888b. 888     8888888888
888  "Y88b8888b   d8888        d88P  Y88b888     888  888
888    88888888b.d88888        888    888888     888  888
888    888888Y88888P888        888       888     888  888
888    888888 Y888P 888        888  88888888     888  888
888    888888  Y8P  888        888    888888     888  888
888  .d88P888   "   888        Y88b  d88PY88b. .d88P  888
8888888P" 888       888         "Y8888P88 "Y88888P" 8888888 \n\n""")
        app = QApplication(sys.argv)
        window = DmStationUi()
        window.hide()

        # Catches all potential unhandled exceptions
        def dmExceptionHook(exctype, value, traceback):
            errorList = ["Error: " + str(value) + "\n\n"]
            errorList = errorList + ["Traceback (most recent call last):\n"]
            errorList = errorList + format_tb(traceback)
            errorStr = "".join(errorList)
            DmStationUi.unhandledDialog(window, errorStr)

        sys.excepthook = dmExceptionHook
        start = time()
        splashPic = QPixmap(":/splash/splash2.jpg")
        splashScreen = QSplashScreen(splashPic, Qt.WindowStaysOnTopHint)
        splashScreen.show()
        while time() - start < 1:
            sleep(0.001)
            app.processEvents()
        splashScreen.finish(window)
        window.show()
        window.raise_()
        sys.exit(app.exec_())
    except DmException as ex:
        print("ERROR: %s" % ex, file=sys.stderr)
        raise SystemExit(ex.getErrorCode())
    except Exception as ex:
        print("%s" % ex, file=sys.stderr)
        raise SystemExit(DmStatus.DM_ERROR.value)
