#!/usr/bin/env python

from dm.common.constants.dmObjectLabels import DM_NAME_KEY
from dm.common.constants.dmProcessingConstants import (
    DM_COMMAND_KEY,
    DM_MAX_REPEATS_KEY,
    DM_OUTPUT_VARIABLE_REGEX_LIST_KEY,
    DM_PARALLEL_EXEC_KEY,
    DM_REPEAT_PERIOD_KEY,
    DM_REPEAT_UNTIL_KEY,
    DM_WORKING_DIR_KEY,
)
from PyQt5.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QWizardPage,
)

from ..fileBrowser import FileBrowser


class WorkflowWizardStagePage(QWizardPage):
    pageCt = 0

    def __init__(self, stage: dict):
        """create the wizard page for a single workflow stage"""
        super(WorkflowWizardStagePage, self).__init__()
        self.id = WorkflowWizardStagePage.pageCt
        WorkflowWizardStagePage.pageCt += 1

        layout = QFormLayout()
        self.setLayout(layout)
        self.setTitle("Workflow Stage")

        layout.addRow(QLabel("Name *"))
        self.nameLineEdit = QLineEdit(stage.get(DM_NAME_KEY, ""))
        # self.registerField(f"nameLineEdit{self.id}*", self.nameLineEdit) # * sets to mandatory
        layout.addRow(self.nameLineEdit)

        layout.addRow(QLabel("Command *"))
        self.commandLineEdit = QLineEdit(stage.get(DM_COMMAND_KEY, ""))
        # self.registerField(f"commandLineEdit{self.id}*", self.commandLineEdit) # * sets to mandatory
        layout.addRow(self.commandLineEdit)

        layout.addRow(QLabel("Output Variable Regular Expression List"))
        outputVariableRegexList = stage.get(DM_OUTPUT_VARIABLE_REGEX_LIST_KEY, "")
        self.outputVariableRegexListLineEdit = QLineEdit(
            ",".join(outputVariableRegexList)
        )
        layout.addRow(self.outputVariableRegexListLineEdit)

        layout.addRow(QLabel("Working Directory"))
        workingDirRow = QHBoxLayout()
        self.workingDirLineEdit = QLineEdit(stage.get(DM_WORKING_DIR_KEY, ""))
        workingDirRow.addWidget(self.workingDirLineEdit)
        fileBrowserBtn = QPushButton("Browse", self)
        fileBrowserBtn.clicked.connect(
            lambda: FileBrowser.browse(self.workingDirLineEdit, directoryOnly=True)
        )
        workingDirRow.addWidget(fileBrowserBtn)
        layout.addRow(workingDirRow)

        repeatRow = QHBoxLayout()
        repeatRow.addWidget(QLabel("Repeat Period"))
        self.repeatPeriodSpinBox = QSpinBox()
        self.repeatPeriodSpinBox.setValue(stage.get(DM_REPEAT_PERIOD_KEY, 0))
        repeatRow.addWidget(self.repeatPeriodSpinBox)

        repeatRow.addWidget(QLabel("Max Repeats"))
        self.maxRepeatsSpinBox = QSpinBox()
        self.maxRepeatsSpinBox.setValue(stage.get(DM_MAX_REPEATS_KEY, 0))
        repeatRow.addWidget(self.maxRepeatsSpinBox)

        repeatRow.addWidget(QLabel("Repeat Until"))
        self.repeatUntilLineEdit = QLineEdit(stage.get(DM_REPEAT_UNTIL_KEY, ""))
        repeatRow.addWidget(self.repeatUntilLineEdit)
        layout.addRow(repeatRow)

        parallelExecRow = QHBoxLayout()
        self.parallelExecCheckBox = QCheckBox("Use Parallel Execution")
        self.parallelExecCheckBox.setChecked(stage.get(DM_PARALLEL_EXEC_KEY, False))
        parallelExecRow.addWidget(self.parallelExecCheckBox)
        layout.addRow(parallelExecRow)

        buttonRow = QHBoxLayout()
        addButton = QPushButton("Add Stage After")
        addButton.clicked.connect(self.addStageAfter)
        buttonRow.addWidget(addButton)
        removeButton = QPushButton("Remove Stage")
        removeButton.clicked.connect(self.delete)
        buttonRow.addWidget(removeButton)
        layout.addRow(buttonRow)

    def getName(self) -> str:
        return self.nameLineEdit.text()

    def getCommand(self) -> str:
        return self.commandLineEdit.text()

    def getOutputVariableRegexList(self) -> list:
        outputVariableRegexList = self.outputVariableRegexListLineEdit.text()
        if outputVariableRegexList:
            return outputVariableRegexList.split(",")
        else:
            return []

    def getWorkingDir(self) -> str:
        return self.workingDirLineEdit.text()

    def getRepeatPeriod(self) -> int:
        return self.repeatPeriodSpinBox.value()

    def getMaxRepeats(self) -> int:
        return self.maxRepeatsSpinBox.value()

    def getRepeatUntil(self) -> str:
        return self.repeatUntilLineEdit.text()

    def getParallelExec(self) -> bool:
        return self.parallelExecCheckBox.isChecked()

    def asDict(self) -> dict:
        """get the fields from the stage page as a dict"""
        fields = {DM_COMMAND_KEY: self.getCommand()}
        # the rest of the fields are optional so don't add if they are empty
        outputVariableRegexList = self.getOutputVariableRegexList()
        if outputVariableRegexList:
            fields[DM_OUTPUT_VARIABLE_REGEX_LIST_KEY] = outputVariableRegexList

        workingDir = self.getWorkingDir()
        if workingDir:
            fields[DM_WORKING_DIR_KEY] = workingDir

        repeatPeriod = self.getRepeatPeriod()
        if repeatPeriod:
            fields[DM_REPEAT_UNTIL_KEY] = repeatPeriod

        maxRepeats = self.getMaxRepeats()
        if maxRepeats:
            fields[DM_MAX_REPEATS_KEY] = maxRepeats

        repeatUntil = self.getRepeatUntil()
        if repeatUntil:
            fields[DM_REPEAT_UNTIL_KEY] = repeatUntil

        parallelExec = self.getParallelExec()
        if parallelExec:
            fields[DM_PARALLEL_EXEC_KEY] = parallelExec

        return {self.getName(): fields}

    def delete(self):
        """remove this page from the wizard"""
        self.wizard().removePage(self.wizard().currentId())

    def addStageAfter(self):
        """add a new stage page to the wizard after this stage page"""
        wiz = self.wizard()
        newPage = WorkflowWizardStagePage({})
        pageIds = wiz.pageIds()
        for i in range(len(pageIds) - 1, pageIds.index(wiz.currentId()), -1):
            pageId = pageIds[i]
            page = wiz.page(pageId)
            wiz.removePage(pageId)
            wiz.setPage(pageId + 1, page)
        wiz.setPage(wiz.currentId() + 1, newPage)
        wiz.next()

    def checkWarnings(self):
        """check for missing fields and warn user"""
        layout = self.layout()
        if self.warning:
            # remove any previous warnings
            layout.removeRow(layout.rowCount() - 1)
            self.warning = False

        name = self.nameLineEdit.text()
        command = self.commandLineEdit.text()
        msg = ""
        if not name:
            msg += "Enter a name.\n"
        if not command:
            msg += "Enter a command.\n"
        if msg:
            self.addWarning(msg)

    def addWarning(self, message):
        """append warning message to page"""
        warn = QLabel(message)
        warn.setStyleSheet("QLabel { color : red; }")
        self.layout().addRow(warn)
        self.warning = True
