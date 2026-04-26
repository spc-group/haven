#!/usr/bin/env python

from dm.common.constants.dmExperimentConstants import DM_FINALIZATION_KEY
from dm.common.constants.dmObjectLabels import DM_DATA_KEY
from dm.common.utility.experimentIsolationManager import ExperimentIsolationManager
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QWizard,
    QWizardPage,
)


class ExperimentIsolationWizard(QWizard):

    ACLS_KEY = "acls"
    DESTINATION_KEY = "destination"
    INVALID_CHARS = "[% <>*|?'\"]+"
    SPACE_KEY = "space"

    """ gui dialog which collects experiment isolation options from user for a given experiment """

    def __init__(
        self, stage, experimentName, dataPath=None, esafId=None, gupId=None, date=None
    ):
        super(ExperimentIsolationWizard, self).__init__()
        self.stage = stage  # stage should be one of "initialize" or "finalize"
        self.fieldNames = set()
        self.setButtonText(QWizard.FinishButton, "Continue")
        self.setOption(QWizard.NoBackButtonOnLastPage)
        self.setOption(QWizard.NoDefaultButton)
        self.mgmt = ExperimentIsolationManager.getInstance()
        self.setWindowTitle(f"Experiment {stage.capitalize()} Settings")
        self.addPage(self.getPage(experimentName, dataPath, esafId, gupId, date))

    def exec_(self):
        """when continue button is first created, disabling isn't applying
        so check for warnings again right after"""
        QTimer.singleShot(10, self.checkWarnings)
        return super().exec_()

    def getPage(
        self, experimentName, dataPath=None, esafId=None, gupId=None, date=None
    ):
        """create and populate the form fields of the wizard page"""
        page = QWizardPage()
        self.layout = QFormLayout()
        self.addDirectoriesToLayout(page, dataPath, experimentName, esafId, gupId, date)
        self.addSettingsToLayout(page)
        self.warning = False
        page.setLayout(self.layout)
        return page

    def addDirectoriesToLayout(
        self, page, dataPath, experimentName, esafId, gupId, date
    ):
        """add widgets to layout for isolation directory options"""
        # if data directory not provided by user, get it from template
        if not dataPath:
            dataPath = self.mgmt.getDirectoryFromTemplate(
                experimentName, esafId, gupId, date=date
            )
        self.dataPathField = QLineEdit(dataPath)
        self.dataPathField.textChanged.connect(self.checkWarnings)
        page.registerField("data directory", self.dataPathField)
        self.fieldNames.add("data directory")
        self.layout.addRow(QLabel("data directory"), self.dataPathField)
        if self.stage == DM_FINALIZATION_KEY:
            # get destination directory from template and add to form
            destPath = self.mgmt.getDirectoryFromTemplate(
                experimentName, esafId, gupId, isDest=True, date=date
            )
            self.destPathField = QLineEdit(destPath)
            self.destPathField.textChanged.connect(self.checkWarnings)
            page.registerField("destination directory", self.destPathField)
            self.fieldNames.add("destination directory")
            self.layout.addRow(QLabel("destination directory"), self.destPathField)

    def addSettingsToLayout(self, page):
        """add widgets to layout for all non directory isolation options"""
        settings = self.mgmt.getDefaultUserConfig(self.stage)
        for key, val in settings.items():
            if isinstance(val, list):
                val = ",".join(val)
            if "directory template" not in key:
                if isinstance(val, int):
                    dataPathField = QCheckBox(key)
                    dataPathField.setChecked(val)
                    self.layout.addRow(dataPathField)
                    if key == "allow uninitialized data directory":
                        dataPathField.stateChanged.connect(self.checkWarnings)
                else:
                    dataPathField = QLineEdit(val)
                    dataPathField.textChanged.connect(self.checkWarnings)
                    self.layout.addRow(QLabel(key), dataPathField)
                page.registerField(key, dataPathField)
                self.fieldNames.add(key)

    def checkWarnings(self):
        """warn user of any problems with the values in the form fields
        that should be resolved before continuing with isolation"""
        if self.warning:
            # remove any previous warnings
            self.layout.removeRow(self.layout.rowCount() - 1)
            self.button(QWizard.FinishButton).setDisabled(False)
            self.warning = False
        dataDir = self.dataPathField.text()
        msg = self.warnMissingTemplateOptions(dataDir, isDest=False)
        msg += self.warnEmptyRequiredField()
        msg += self.warnInvalidBasePath(dataDir, isDest=False)
        msg += self.warnInvalidCharacters(dataDir)
        if self.stage == DM_FINALIZATION_KEY:
            destDir = self.destPathField.text()
            msg += self.warnMissingTemplateOptions(destDir, isDest=True)
            msg += self.warnInvalidBasePath(destDir, isDest=True)
            msg += self.warnNoPastRun(dataDir)
            msg += self.warnInvalidCharacters(destDir)
        self.setWarning(msg)

    def warnNoPastRun(self, dataDir):
        """get warning message if data directory uninitalized (before finalizing)"""
        if not self.field("allow uninitialized data directory"):
            if not self.mgmt.getPastRun(dataDir):
                self.warning = True
                return "WARNING: Data directory has no record of initialization. Initialize before continuing.\n"
        return ""

    def warnInvalidBasePath(self, directory, isDest):
        """get warning message if directory is not under an allowed base path"""
        if not self.mgmt.isValidDirectory(directory, isDest):
            self.warning = True
            allowedBasePaths = self.mgmt.getAllowedBasePaths(isDest)
            allowedBasePaths = "\n".join(allowedBasePaths)
            dirType = self.DESTINATION_KEY if isDest else DM_DATA_KEY
            return (
                f"WARNING: {dirType.capitalize()} directory is not located under an allowed base path."
                + f" Edit {dirType} directory before continuing. Allowed base paths for this station are:\n {allowedBasePaths}\n\n"
            )
        return ""

    def warnEmptyRequiredField(self):
        """get warning message if field for a required option is empty"""
        fields = self.getFields()
        msg = ""
        for k in fields:
            # acls optional
            if self.ACLS_KEY not in k and fields.get(k) == "":
                self.warning = True
                msg += f"WARNING: {k} cannot be empty.\n\n"
        return msg

    def warnMissingTemplateOptions(self, directory, isDest):
        """get warning message if directory template is not filled"""
        missed = self.mgmt.getUnfilledTemplateOptions(directory)
        if missed:
            self.warning = True
            missed = ", ".join(missed)
            dirType = self.DESTINATION_KEY if isDest else DM_DATA_KEY
            return f"WARNING: Unable to find value(s) {missed} for {dirType} directory template. Edit {dirType} directory before continuing.\n\n"
        return ""

    def warnInvalidCharacters(self, directory):
        msg = ""
        for c in self.INVALID_CHARS:
            if c in directory:
                self.warning = True
                if c == " ":
                    c = self.SPACE_KEY
                msg += f"WARNING: Invalid character in directory name: {c}\n"
        return msg

    def setWarning(self, msg):
        """add warnings to form and disable continue button"""
        if self.warning:
            warn = QLabel(msg)
            warn.setWordWrap(True)
            warn.setStyleSheet("QLabel { color : red; }")
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(warn)
            self.layout.addRow(scroll)
            self.button(QWizard.FinishButton).setDisabled(True)

    def getFields(self):
        """get values from form as a dict"""
        fields = {}
        for name in self.fieldNames:
            val = self.field(name)
            if self.ACLS_KEY in name:
                val = val.split(",")
            fields[name] = val
        return fields
