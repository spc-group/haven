#!/usr/bin/env python

from dm.common.constants.dmProcessingConstants import (
    DM_OUTPUT_VARIABLE_REGEX_LIST_KEY,
    DM_STAGES_KEY,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)

from ..apiFactory import ApiFactory
from .style import DM_FONT_ARIAL_KEY


class WorkflowDialog(QDialog):

    NEW_KEY = "New"
    UPDATE_KEY = "Update"

    def __init__(self, parent=None, setting=None, text=None, workflow=None):
        super(WorkflowDialog, self).__init__(parent)
        self.workflowApi = ApiFactory.getInstance().getWorkflowApi()
        self.parent = parent
        self.setting = setting
        self.text = text
        self.workflow = workflow

        self.setMinimumWidth(500)

        self.grid = QGridLayout()

        self.setWindowTitle("Workflow Manager")

        labelFont = QFont(DM_FONT_ARIAL_KEY, 18, QFont.Bold)
        if setting == self.NEW_KEY:
            self.titleLbl = QLabel("Set Workflow Title")
        elif setting == self.UPDATE_KEY:
            self.titleLbl = QLabel("Update Workflow Step")
        else:
            self.titleLbl = QLabel("Add Workflow Step")
        self.titleLbl.setAlignment(Qt.AlignCenter)
        self.titleLbl.setFont(labelFont)
        self.grid.addWidget(self.titleLbl, 0, 1, 1, 2)

        self.inputField = QLineEdit()
        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.cancel)
        self.cancelButton.setMaximumWidth(130)
        self.saveButton = QPushButton("Save")
        self.saveButton.clicked.connect(self.save)
        self.saveButton.setMaximumWidth(130)
        self.saveButton.setDefault(True)

        self.outputVarTable = QTableWidget()

        self.addVarBtn = QPushButton("Add Regex Output")
        self.addVarBtn.clicked.connect(self.addVar)
        self.editVarBtn = QPushButton("Edit Regex Output")
        self.editVarBtn.clicked.connect(self.editVar)

        if setting == self.UPDATE_KEY:
            self.inputField.setText(self.text)

        hBox = QHBoxLayout()
        hBox.addWidget(self.inputField)

        hBox2 = QHBoxLayout()
        hBox2.addWidget(self.outputVarTable)

        hBox3 = QHBoxLayout()
        hBox3.addWidget(self.editVarBtn)
        hBox3.addWidget(self.addVarBtn)

        hBox4 = QHBoxLayout()
        hBox4.addWidget(self.cancelButton)
        hBox4.addWidget(self.saveButton)

        self.grid.addLayout(hBox, 1, 0, 1, 4)
        self.grid.addLayout(hBox2, 2, 0, 1, 4)
        self.grid.addLayout(hBox3, 3, 0, 1, 4)
        self.grid.addLayout(hBox4, 4, 0, 1, 4)

        self.updateVarTable()
        self.clearOutputSelection()
        self.setLayout(self.grid)

    def save(self):
        if self.setting == self.UPDATE_KEY:
            self.parent.detailsTable.item(
                self.parent.detailsTable.currentRow(), 1
            ).setText(self.inputField.text())
        elif self.setting == self.NEW_KEY:
            self.parent.detailsTable.setRowCount(
                self.parent.detailsTable.rowCount() + 1
            )
            self.parent.detailsTable.setItem(
                self.parent.detailsTable.rowCount() - 1,
                0,
                QTableWidgetItem(self.parent.detailsTable.rowCount()),
            )
            self.parent.detailsTable.setItem(
                self.parent.detailsTable.rowCount() - 1,
                1,
                QTableWidgetItem(self.inputField.text()),
            )
        self.workflowApi.updateWorkflow(self.workflow)
        self.done(1)

    def updateVarTable(self):
        try:
            regexList = self.workflow.data[DM_STAGES_KEY][
                str(self.parent.detailsTable.currentRow() + 1)
            ][DM_OUTPUT_VARIABLE_REGEX_LIST_KEY]
        except Exception:
            regexList = []

        self.outputVarTable.setRowCount(len(regexList))
        self.outputVarTable.setColumnCount(1)
        self.outputVarTable.clicked.connect(self.enableOutputEdit)
        self.outputVarTable.itemSelectionChanged.connect(self.stopEdit)
        self.outputVarTable.setSelectionMode(QAbstractItemView.SingleSelection)
        self.outputVarTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.outputVarTable.setHorizontalHeaderLabels("Regex Outputs;".split(";"))
        self.outputVarTable.horizontalHeader().setStretchLastSection(True)

        i = 0
        for var in regexList:
            varStr = QTableWidgetItem(var)
            self.outputVarTable.setItem(i, 0, varStr)
            i += 1

        if regexList:
            height = (
                ((len(regexList) * 30) + 30)
                if ((len(regexList) * 30) + 30) < 500
                else 500
            )
            self.outputVarTable.setMaximumHeight(height)
            self.outputVarTable.show()
        else:
            self.outputVarTable.hide()

    def enableOutputEdit(self):
        self.editVarBtn.setEnabled(True)

    def clearOutputSelection(self):
        self.outputVarTable.clearSelection()
        self.editVarBtn.setEnabled(False)

    def addVar(self):
        self.outputVarTable.setRowCount(self.outputVarTable.rowCount() + 1)
        self.outputVarTable.setItem(
            self.outputVarTable.rowCount() - 1, 0, QTableWidgetItem()
        )
        item = self.outputVarTable.item(self.outputVarTable.rowCount() - 1, 0)
        self.outputVarTable.scrollToBottom()
        self.outputVarTable.setFocus()
        self.outputVarTable.setCurrentIndex(self.outputVarTable.indexFromItem(item))
        self.outputVarTable.openPersistentEditor(item)

    def editVar(self):
        item = self.outputVarTable.item(self.outputVarTable.currentRow(), 0)
        self.outputVarTable.openPersistentEditor(item)
        self.outputVarTable.setFocus()

    def stopEdit(self):
        item = self.outputVarTable.selectedItems()[0]
        self.outputVarTable.closePersistentEditor(item)

    def cancel(self):
        self.done(1)
