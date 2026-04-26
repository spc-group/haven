#!/usr/bin/env python

from dm.common.constants.dmExperimentConstants import (
    DM_FINALIZATION_KEY,
    DM_INITIALIZATION_KEY,
)
from dm.common.constants.dmObjectLabels import DM_BEAMLINE_NAME_KEY
from dm.common.utility.configurationManager import ConfigurationManager
from dm.common.utility.loggingManager import LoggingManager
from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtGui import QFont, QIntValidator
from PyQt5.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from .apiFactory import ApiFactory
from .subclasses.style import DM_FONT_ARIAL_KEY


# Define the Processing Jobs tab content:
class SettingsTab(QWidget):

    ORG_NAME = "UChicagoArgonneLLC"
    APP_NAME = "dmStationUi"

    REF_CYCLE_EXPERIMENTS = "experimentsRefreshCycle"
    REF_CYCLE_DAQS = "daqsRefreshCycle"
    REF_CYCLE_UPLOADS = "uploadsRefreshCycle"
    REF_CYCLE_JOBS = "processingJobsRefreshCycle"
    REF_CYCLE_WORKFLOWS = "workflowsRefreshCycle"
    DEFAULT_INTERVAL = 60
    TEMPLATE_KEY = "template"

    def __init__(self, parent):
        super(SettingsTab, self).__init__(parent)
        self.parent = parent
        self.logger = LoggingManager.getInstance().getLogger(self.__class__.__name__)

        beamlineName = ConfigurationManager.getInstance().get(DM_BEAMLINE_NAME_KEY)
        # check if isolation settings configured for station and in daq service
        self.isExperimentIsolationEnabled = (
            ConfigurationManager.getInstance().hasExperimentIsolationSettingsFile()
            and ApiFactory()
            .getInstance()
            .getExperimentDaqApi()
            .isConfiguredForIsolation(beamlineName)
        )
        self.settingsLayout()
        self.settings = QSettings(SettingsTab.ORG_NAME, SettingsTab.APP_NAME, self)
        self.loadSettings()

    # GUI layout where each block is a row on the grid
    def settingsLayout(self):
        grid = QGridLayout()

        labelFont = QFont(DM_FONT_ARIAL_KEY, 18, QFont.Bold)
        lbl = QLabel("Settings", self)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(labelFont)
        grid.addWidget(lbl, 0, 0)

        refIntervalGroup = QGroupBox()
        refIntervalGroup.setAlignment(Qt.AlignCenter)
        refIntervalGroup.setTitle("Refresh Intervals (seconds)")

        refIntervalsFormLayout = QFormLayout()
        self.experimentsRefIntervalVal = self._createIntInput(
            refIntervalsFormLayout,
            "Experiments",
            "Specify the interval in seconds for experiments refresh cycle (0 for no refresh)",
        )
        self.daqsRefIntervalVal = self._createIntInput(
            refIntervalsFormLayout,
            "Daqs",
            "Specify the interval in seconds for daqs refresh cycle (0 for no refresh)",
        )
        self.uploadsRefIntervalVal = self._createIntInput(
            refIntervalsFormLayout,
            "Uploads",
            "Specify the interval in seconds for uploads refresh cycle (0 for no refresh)",
        )
        self.jobsRefIntervalVal = self._createIntInput(
            refIntervalsFormLayout,
            "Processing Jobs",
            "Specify the interval in seconds for processing jobs refresh cycle (0 for no refresh)",
        )
        self.workflowsRefIntervalVal = self._createIntInput(
            refIntervalsFormLayout,
            "Workflows",
            "Specify the interval in seconds for workflows refresh cycle (0 for no refresh)",
        )

        refIntervalGroup.setLayout(refIntervalsFormLayout)
        grid.addWidget(refIntervalGroup, 2, 0)

        if self.isExperimentIsolationEnabled:
            # add section for experiment isolation settings to layout
            expInitGroup = QGroupBox()
            expInitGroup.setAlignment(Qt.AlignCenter)
            expInitGroup.setTitle("Default Experiment Initialization Options")
            self.expInitFormLayout = QFormLayout()
            expInitGroup.setLayout(self.expInitFormLayout)

            expFinalGroup = QGroupBox()
            expFinalGroup.setAlignment(Qt.AlignCenter)
            expFinalGroup.setTitle("Default Experiment Finalization Options")
            self.expFinalFormLayout = QFormLayout()
            expFinalGroup.setLayout(self.expFinalFormLayout)

            grid.addWidget(expInitGroup, 3, 0)
            grid.addWidget(expFinalGroup, 4, 0)

        self.saveBtn = QPushButton("Save", self)
        self.saveBtn.clicked.connect(self.saveSettings)

        grid.addWidget(self.saveBtn, 5, 0, Qt.AlignCenter)
        self.setLayout(grid)

    def _createIntInput(self, formLayout, promptText, tooltip, min=0, max=1000):
        minMaxText = " (" + str(min) + "-" + str(max) + ")"
        promptTextLabel = QLabel(promptText + minMaxText)
        inputObject = QLineEdit()
        inputObject.setValidator(QIntValidator(min, max, self))
        inputObject.setToolTip(tooltip)

        formLayout.addRow(promptTextLabel, inputObject)
        return inputObject

    def loadSettings(self):
        if self.isExperimentIsolationEnabled:
            self.loadExperimentIsolationSettings(
                self.expInitFormLayout, DM_INITIALIZATION_KEY
            )
            self.loadExperimentIsolationSettings(
                self.expFinalFormLayout, DM_FINALIZATION_KEY
            )
        self._loadIntervalSettings(
            SettingsTab.REF_CYCLE_UPLOADS, self.uploadsRefIntervalVal
        )
        self._loadIntervalSettings(SettingsTab.REF_CYCLE_DAQS, self.daqsRefIntervalVal)
        self._loadIntervalSettings(
            SettingsTab.REF_CYCLE_EXPERIMENTS, self.experimentsRefIntervalVal
        )
        self._loadIntervalSettings(SettingsTab.REF_CYCLE_JOBS, self.jobsRefIntervalVal)
        self._loadIntervalSettings(
            SettingsTab.REF_CYCLE_WORKFLOWS, self.workflowsRefIntervalVal
        )

    def _loadIntervalSettings(self, key, settingInputWidget):
        refCycle = str(self.settings.value(key, SettingsTab.DEFAULT_INTERVAL))
        if refCycle == "":
            refCycle = str(SettingsTab.DEFAULT_INTERVAL)

        settingInputWidget.setText(refCycle)

    def saveSettings(self):
        self.settings.setValue(
            SettingsTab.REF_CYCLE_DAQS, self.daqsRefIntervalVal.text()
        )
        self.settings.setValue(
            SettingsTab.REF_CYCLE_EXPERIMENTS, self.experimentsRefIntervalVal.text()
        )
        self.settings.setValue(
            SettingsTab.REF_CYCLE_UPLOADS, self.uploadsRefIntervalVal.text()
        )
        self.settings.setValue(
            SettingsTab.REF_CYCLE_JOBS, self.jobsRefIntervalVal.text()
        )
        self.settings.setValue(
            SettingsTab.REF_CYCLE_WORKFLOWS, self.workflowsRefIntervalVal.text()
        )
        # Reload with the new values
        self.parent.setUpRefreshTimers()

    def fetchRefCycleExperiments(self):
        return int(self.experimentsRefIntervalVal.text())

    def fetchRefCycleDaqs(self):
        return int(self.daqsRefIntervalVal.text())

    def fetchRefCycleUploads(self):
        return int(self.uploadsRefIntervalVal.text())

    def fetchRefCycleJobs(self):
        return int(self.jobsRefIntervalVal.text())

    def fetchRefCycleWorkflows(self):
        return int(self.workflowsRefIntervalVal.text())

    def loadExperimentIsolationSettings(self, layout, step):
        """populate form with known values from experiment isolation settings file"""
        settings = (
            ConfigurationManager.getInstance()
            .getExperimentIsolationSettings()
            .get(step)
        )
        for key, val in settings.items():
            if isinstance(val, list):
                val = ",".join(val)
            if isinstance(val, int) or isinstance(val, bool):
                check = QCheckBox(key)
                check.setChecked(val)
                check.setAttribute(Qt.WA_TransparentForMouseEvents, True)  # read only
                layout.addRow(check)
            else:
                linedit = QLineEdit(val)
                linedit.setReadOnly(True)  # read only
                if self.TEMPLATE_KEY in key:
                    linedit.setToolTip(
                        "Template used to set directory names. Will fill info for the following variables in the template:\n"
                        + " $MM numeric month with leading zero e.g. 02\n"
                        + " $M numeric month with no leading zero e.g. 2\n"
                        + " $MONTH full month name e.g. February\n"
                        + " $MON abbreviated month name e.g. Feb\n"
                        + " $DD numeric day with leading zero e.g. 03\n"
                        + " $D numeric day no leading zero e.g. 3\n"
                        + " $YY year with 2 digits e.g. 21\n"
                        + " $YYYY year with 4 digits e.g. 2021\n"
                        + " $EXP_NAME experiment name\n"
                        + " $EXP_TYPE experiment type\n"
                        + " $STATION station name\n"
                        + " $CYCLE cycle number e.g. 1 for run 2021-1\n"
                        + " $ESAF esaf number used to create experiment\n"
                        + " $GUP gup number used to create experiment\n"
                        + " $PI principal investigator on experiment\n\n"
                        + "e.g. template '/home/dm/data/$YYYY-$CYCLE/$ESAF' becomes directory name '/home/dm/data/2021-3/12345'"
                    )
                label = QLabel(key)
                layout.addRow(label, linedit)
