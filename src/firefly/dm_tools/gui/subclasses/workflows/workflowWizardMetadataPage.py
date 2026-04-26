#!/usr/bin/env python

from dm.common.constants.dmObjectLabels import (
    DM_DESCRIPTION_KEY,
    DM_NAME_KEY,
    DM_OWNER_KEY,
)
from dm.common.objects.workflow import Workflow
from PyQt5.QtWidgets import QFormLayout, QHBoxLayout, QLabel, QLineEdit, QWizardPage

from ...apiFactory import ApiFactory


class WorkflowWizardMetadataPage(QWizardPage):
    def __init__(self, defaultOwner=""):
        """create the wizard page for workflow name, owner, and description"""
        super(WorkflowWizardMetadataPage, self).__init__()
        self.warning = False
        self.defaultOwner = defaultOwner
        layout = QFormLayout()
        self.setLayout(layout)

        nameRow = QHBoxLayout()
        nameLabel = QLabel("Name *")
        self.workflowNameLineEdit = QLineEdit()
        self.workflowNameLineEdit.setToolTip("Name of workflow")
        self.workflowNameLineEdit.textChanged.connect(self.checkWarnings)
        nameRow.addWidget(nameLabel)
        nameRow.addWidget(self.workflowNameLineEdit)
        layout.addRow(nameRow)

        ownerRow = QHBoxLayout()
        ownerLabel = QLabel("Owner *")
        self.ownerLineEdit = QLineEdit()
        self.ownerLineEdit.setToolTip("Username of workflow owner")
        self.ownerLineEdit.textChanged.connect(self.checkWarnings)
        ownerRow.addWidget(ownerLabel)
        ownerRow.addWidget(self.ownerLineEdit)
        layout.addRow(ownerRow)

        descriptionRow = QHBoxLayout()
        descriptionLabel = QLabel("Description *")
        self.descriptionLineEdit = QLineEdit()
        self.descriptionLineEdit.setToolTip("Description of workflow")
        self.descriptionLineEdit.textChanged.connect(self.checkWarnings)
        descriptionRow.addWidget(descriptionLabel)
        descriptionRow.addWidget(self.descriptionLineEdit)
        layout.addRow(descriptionRow)

    def fill(self, workflow: Workflow):
        """populate info page with info from workflow (name, owner, and description)"""
        self.workflowNameLineEdit.setText(workflow.get(DM_NAME_KEY, ""))
        self.ownerLineEdit.setText(workflow.get(DM_OWNER_KEY, self.defaultOwner))
        self.descriptionLineEdit.setText(workflow.get(DM_DESCRIPTION_KEY, ""))

    def checkWarnings(self):
        """check for missing fields and warn user"""
        layout = self.layout()
        if self.warning:
            # remove any previous warnings
            layout.removeRow(layout.rowCount() - 1)
            self.warning = False
        name = self.workflowNameLineEdit.text()
        description = self.descriptionLineEdit.text()
        owner = self.ownerLineEdit.text()

        msg = ""
        if not name:
            msg += "Enter a name.\n"
        if not owner:
            msg += "Enter an owner.\n"
        if not description:
            msg += "Enter a description.\n"

        if name and owner:
            api = ApiFactory.getInstance().getWorkflowApi()
            try:
                workflow = api.getWorkflowByName(owner, name)
                if workflow:
                    msg += f"Workflow '{name}' owned by {owner} already exists and will be updated if you continue."
            except Exception:
                pass  # workflow api throws error if workflow doesn't exist
        if msg:
            self.addWarning(msg)

    def addWarning(self, message):
        """append warning message to page"""
        warn = QLabel(message)
        warn.setStyleSheet("QLabel { color : red; }")
        self.layout().addRow(warn)
        self.warning = True

    def asDict(self) -> dict:
        """get fields from the page as dict"""
        return {
            DM_NAME_KEY: self.workflowNameLineEdit.text(),
            DM_OWNER_KEY: self.ownerLineEdit.text(),
            DM_DESCRIPTION_KEY: self.descriptionLineEdit.text(),
        }
