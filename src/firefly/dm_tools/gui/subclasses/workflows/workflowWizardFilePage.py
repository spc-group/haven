#!/usr/bin/env python

import json
import os

from dm.common.constants.dmFileConstants import DM_JSON_KEY
from dm.common.constants.dmObjectLabels import DM_NAME_KEY
from dm.common.objects.workflow import Workflow
from PyQt5.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWizard,
    QWizardPage,
)

from ...apiFactory import ApiFactory
from ..fileBrowser import FileBrowser


class WorkflowWizardFilePage(QWizardPage):
    def __init__(self, defaultOwner=""):
        """create the wizard page for getting the workflow spec file"""
        super(WorkflowWizardFilePage, self).__init__()
        self.defaultOwner = defaultOwner
        self.clone = False
        layout = QFormLayout()
        self.setLayout(layout)

        label = QLabel("Workflow specification file *")
        layout.addRow(label)

        fileRow = QHBoxLayout()
        self.fileNameLineEdit = QLineEdit()
        self.fileNameLineEdit.setToolTip(
            "Select the file containing the definition of the workflow or the name of a new file (.py or .json)"
        )
        self.fileNameLineEdit.textChanged.connect(self.fileChanged)
        fileBrowserBtn = QPushButton("Browse", self)
        fileBrowserBtn.clicked.connect(
            lambda: FileBrowser.browse(self.fileNameLineEdit, "*.py *.json")
        )
        fileRow.addWidget(self.fileNameLineEdit)
        fileRow.addWidget(fileBrowserBtn)
        layout.addRow(fileRow)

        layout.addRow(QLabel("Clone existing workflow"))
        self.cloneComboBox = QComboBox()
        self.cloneComboBox.currentTextChanged.connect(self.cloneChanged)
        layout.addRow(self.cloneComboBox)
        self.cloneComboBox.addItem("")
        api = ApiFactory.getInstance().getWorkflowApi()
        workflows = api.listWorkflows(self.defaultOwner)
        for workflow in workflows:
            self.cloneComboBox.addItem(workflow.get(DM_NAME_KEY))

    def getWorkflowFromFile(self, filename) -> Workflow:
        """create a workflow from the contents of a file"""
        spec = {}
        try:
            with open(filename) as f:
                workflowTxt = f.read()
            if filename.endswith(".py"):
                spec = eval(workflowTxt)
            else:
                spec = json.loads(workflowTxt)
        except Exception:
            warn = QLabel("Unable to read workflow spec. Please check formatting.")
            warn.setStyleSheet("QLabel { color : red; }")
            self.filePage.layout().addRow(warn)
            self.button(QWizard.NextButton).setDisabled(True)
            self.warning = True
        return Workflow(spec)

    def checkWarnings(self):
        """add warnings to file page and disable next button"""
        layout = self.filePage.layout()
        if self.warning:
            # remove any previous warnings
            layout.removeRow(layout.rowCount() - 1)
            self.button(QWizard.NextButton).setDisabled(False)
            self.warning = False
        filename = self.fileNameLineEdit.text()
        if not filename:
            warn = QLabel("Enter a filename.")
            warn.setStyleSheet("QLabel { color : red; }")
            layout.addRow(warn)
            self.button(QWizard.NextButton).setDisabled(True)
            self.warning = True
        elif not (filename.endswith(".py") or filename.endswith(DM_JSON_KEY)):
            warn = QLabel("Workflow spec must be a .py or .json file.")
            warn.setStyleSheet("QLabel { color : red; }")
            layout.addRow(warn)
            self.button(QWizard.NextButton).setDisabled(True)
            self.warning = True
        return self.warning

    def fileChanged(self):
        """Check the spec filename entered by user. If it is a valid format,
        populate the wizard with workflow info from file"""
        filename = self.fileNameLineEdit.text()
        if not self.clone:
            # if not self.checkFilePageWarnings():
            # if file exists, populate rest of wizard
            if os.path.exists(filename):
                workflow = self.getWorkflowFromFile(filename)
                self.wizard().update(workflow)
            else:
                self.wizard().update()

    def cloneChanged(self):
        """populate the wizard with info from the clone workflow"""
        name = self.cloneComboBox.currentText()
        if name:
            self.clone = True
            api = ApiFactory.getInstance().getWorkflowApi()
            workflow = api.getWorkflowByName(self.defaultOwner, name)
            self.wizard().update(workflow)
        else:
            self.clone = False
