import logging

from dm.common.constants.dmObjectLabels import (
    DM_DESCRIPTION_KEY,
    DM_ID_KEY,
    DM_NAME_KEY,
)
from dm.common.constants.dmProcessingConstants import DM_COMMAND_KEY, DM_STAGES_KEY
from dm.common.exceptions.communicationError import CommunicationError
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPalette
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from .apiFactory import ApiFactory
from .subclasses import customSelectionModel, customStyledDelegate, workflowDialog
from .subclasses.style import DM_FONT_ARIAL_KEY, DM_GUI_LIGHT_GREY, DM_GUI_WHITE
from .subclasses.workflows.workflowWizard import WorkflowWizard

log = logging.getLogger("dm_tools")


# Define the DAQs tab content:
class WorkflowTab(QWidget):
    def __init__(self, stationName, parent, id=-1):
        super(WorkflowTab, self).__init__(parent)
        self.stationName = stationName
        self.parent = parent
        self.showingDetails = 0
        self.experimentDaqApi = ApiFactory.getInstance().getExperimentDaqApi()
        self.workflowApi = ApiFactory.getInstance().getWorkflowApi()
        self.workflowTabLayout()

    # GUI layout where each block is a row on the grid
    def workflowTabLayout(self):
        grid = QGridLayout()

        labelFont = QFont(DM_FONT_ARIAL_KEY, 18, QFont.Bold)
        lbl = QLabel(self.parent.username + " Workflow List", self)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(labelFont)
        grid.addWidget(lbl, 0, 0, 1, 5)

        self.backBtn = QPushButton("Back", self)
        self.backBtn.clicked.connect(self.toggleDetails)
        self.backBtn.setFocusPolicy(Qt.NoFocus)
        self.backBtn.setMinimumWidth(100)
        self.backBtn.hide()
        grid.addWidget(self.backBtn, 0, 0, Qt.AlignLeft)

        self.refBtn = QPushButton("Refresh", self)
        self.refBtn.setFocusPolicy(Qt.NoFocus)
        self.refBtn.setToolTip("Refresh the workflow list.")
        self.refBtn.clicked.connect(self.parent.refreshTables)
        self.refBtn.setMinimumWidth(100)
        grid.addWidget(self.refBtn, 1, 4, Qt.AlignCenter)

        grid.addItem(QSpacerItem(20, 30, QSizePolicy.Expanding), 2, 0)

        alternate = QPalette()
        alternate.setColor(QPalette.AlternateBase, DM_GUI_LIGHT_GREY)
        alternate.setColor(QPalette.Base, DM_GUI_WHITE)

        self.workflowTable = QTableWidget()
        self.workflowTable.setAlternatingRowColors(True)
        self.workflowTable.setPalette(alternate)
        self.workflowTable.clicked.connect(self.enableDetails)
        self.workflowTable.doubleClicked.connect(self.toggleDetails)
        self.workflowTable.setSelectionMode(QAbstractItemView.SingleSelection)
        self.workflowTable.setItemDelegate(
            customStyledDelegate.CustomStyledDelegate(self.workflowTable, self)
        )
        self.workflowTable.setSelectionModel(
            customSelectionModel.CustomSelectionModel(self, self.workflowTable.model())
        )
        grid.addWidget(self.workflowTable, 3, 0, 1, 5)

        self.detailsTable = QTableWidget()
        self.detailsTable.setAlternatingRowColors(True)
        self.detailsTable.setPalette(alternate)
        self.detailsTable.doubleClicked.connect(self.expandRow)
        self.detailsTable.clicked.connect(self.enableModify)
        self.detailsTable.hide()
        self.detailsTable.setItemDelegate(
            customStyledDelegate.CustomStyledDelegate(self.detailsTable, self)
        )
        self.detailsTable.setSelectionModel(
            customSelectionModel.CustomSelectionModel(self, self.detailsTable.model())
        )
        grid.addWidget(self.detailsTable, 3, 0, 1, 5)

        self.addBtn = QPushButton("Add Workflow", self)
        self.addBtn.setFocusPolicy(Qt.NoFocus)
        self.addBtn.setMaximumWidth(130)
        self.addBtn.clicked.connect(lambda: WorkflowWizard(self.parent).exec_())

        self.detailBtn = QPushButton("Inspect", self)
        self.detailBtn.clicked.connect(self.toggleDetails)
        self.detailBtn.setFocusPolicy(Qt.NoFocus)
        self.detailBtn.setMaximumWidth(130)

        self.deleteBtn = QPushButton("Delete Workflow", self)
        self.deleteBtn.setFocusPolicy(Qt.NoFocus)
        self.deleteBtn.setMaximumWidth(130)
        self.deleteBtn.clicked.connect(self.deleteWorkflow)

        self.updateBtn = QPushButton("Modify Step", self)
        self.updateBtn.clicked.connect(self.updateStep)
        self.updateBtn.setFocusPolicy(Qt.NoFocus)
        self.updateBtn.hide()
        self.updateBtn.setMaximumWidth(130)

        self.addStepBtn = QPushButton("Add Step", self)
        self.addStepBtn.clicked.connect(self.addStep)
        self.addStepBtn.setFocusPolicy(Qt.NoFocus)
        self.addStepBtn.hide()
        self.addStepBtn.setMaximumWidth(130)

        hbox1 = QHBoxLayout()
        hbox1.addWidget(self.addBtn)
        hbox1.addWidget(self.detailBtn)
        hbox1.addWidget(self.deleteBtn)
        hbox1.addWidget(self.updateBtn)
        hbox1.addWidget(self.addStepBtn)

        grid.addLayout(hbox1, 4, 0, 1, 5)
        grid.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding), 5, 0)

        self.setLayout(grid)
        self.updateList()

    def updateList(self):
        self.detailBtn.setEnabled(False)
        self.deleteBtn.setEnabled(False)
        try:
            self.workflowList = self.workflowApi.listWorkflows(self.parent.username)
        except CommunicationError as exc:
            log.error(exc)
            self.workflowList = []
        self.workflowTable.setRowCount(len(self.workflowList))
        self.workflowTable.setColumnCount(2)
        self.workflowTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.workflowTable.setSelectionMode(QAbstractItemView.SingleSelection)
        self.workflowTable.setHorizontalHeaderLabels("Name;Description;".split(";"))
        self.workflowTable.horizontalHeader().setStretchLastSection(True)

        i = 0
        for workflow in self.workflowList:
            rowName = QTableWidgetItem(workflow.get(DM_NAME_KEY))
            rowName.setData(Qt.UserRole, workflow.get(DM_ID_KEY))
            rowDesc = workflow.get(DM_DESCRIPTION_KEY)
            if len(rowDesc) > 100:
                for j in range(len(rowDesc)):
                    if j % 50 == 0 and j != 0:
                        rowDesc = rowDesc[:j] + " " + rowDesc[j:]
            rowDesc = QTableWidgetItem(rowDesc)
            self.workflowTable.setItem(i, 0, rowName)
            self.workflowTable.setItem(i, 1, rowDesc)
            i = i + 1
        self.workflowTable.setSortingEnabled(True)

    def updateStep(self):
        self.detailsTable.selectRow(-1)
        updateText = str(
            self.detailsTable.item(self.detailsTable.currentRow(), 1).text()
        )
        self.workflowDialog = workflowDialog.WorkflowDialog(
            self, workflow=self.currentWorkflow, setting="Update", text=updateText
        )
        self.workflowDialog.exec_()

    def addStep(self):
        self.workflowDialog = workflowDialog.WorkflowDialog(
            self, workflow=self.currentWorkflow, setting="Add"
        )
        self.workflowDialog.exec_()

    # Toggles to show/hide the details table of the thing that is selected
    def toggleDetails(self):
        if self.showingDetails == 1:
            self.detailsTable.clearFocus()
            self.detailsTable.clearSelection()
            self.workflowTable.show()
            self.detailsTable.hide()
            self.detailBtn.show()
            self.backBtn.hide()
            self.deleteBtn.show()
            self.addBtn.show()
            self.addStepBtn.hide()
            self.updateBtn.hide()
            self.showingDetails = 0
        else:
            self.workflowDetails()
            self.workflowTable.setSelectionMode(QAbstractItemView.NoSelection)
            self.workflowTable.hide()
            self.workflowTable.setSelectionMode(QAbstractItemView.SingleSelection)
            self.detailsTable.show()
            self.detailBtn.hide()
            self.backBtn.show()
            self.addBtn.hide()
            self.deleteBtn.hide()
            self.deleteBtn.hide()
            self.updateBtn.show()
            self.updateBtn.setEnabled(False)
            self.addStepBtn.show()
            self.showingDetails = 1

    # Set up the details table for the selected workflow
    def workflowDetails(self):
        self.detailsTable.setSortingEnabled(False)
        id = self.workflowTable.item(self.workflowTable.currentRow(), 0).data(
            Qt.UserRole
        )
        self.workflowTable.clearFocus()
        self.currentWorkflow = self.workflowApi.getWorkflowById(
            self.parent.username, id
        )

        self.detailsTable.setRowCount(len(self.currentWorkflow.data.get(DM_STAGES_KEY)))
        self.detailsTable.setColumnCount(2)
        self.detailsTable.setSelectionMode(QAbstractItemView.SingleSelection)
        self.detailsTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.detailsTable.setHorizontalHeaderLabels("Step;Command;".split(";"))
        self.detailsTable.horizontalHeader().setStretchLastSection(True)

        i = 0
        for key, value in self.currentWorkflow.data.get(DM_STAGES_KEY).items():
            stepNum = QTableWidgetItem(key)
            cmdStr = str(value.get(DM_COMMAND_KEY))
            cmdStr = QTableWidgetItem(cmdStr)
            self.detailsTable.setItem(i, 0, stepNum)
            self.detailsTable.setItem(i, 1, cmdStr)
            i += 1
        self.detailsTable.setSortingEnabled(True)
        self.detailsTable.sortByColumn(0, Qt.AscendingOrder)

    # Manually updates the tableView
    def updateView(self, index):
        if self.workflowTable.isVisible():
            self.workflowTable.update(index)
        else:
            self.detailsTable.update(index)

    # Enables the detail button when the table is selected
    def enableDetails(self):
        self.detailBtn.setEnabled(True)
        self.deleteBtn.setEnabled(True)

    # Enabled the modify step button
    def enableModify(self):
        self.updateBtn.setEnabled(True)

    # Returns the tables on this tab
    def getTables(self):
        tables = [self.workFlowTable, self.detailsTable]
        return tables

    # Expands the targetted row to fit contents when doubleclicked
    def expandRow(self, index):
        self.detailsTable.resizeRowToContents(index.row())

    def deleteWorkflow(self):
        workflowName = str(
            self.workflowTable.item(self.workflowTable.currentRow(), 0).text()
        )

        text = f"If you continue, workflow '{workflowName}' will be deleted from the DM DB.\nProceed?"
        self.dialog = QMessageBox(
            QMessageBox.Warning,
            "Delete Workflow",
            text,
            QMessageBox.Yes | QMessageBox.No,
        )
        reply = self.dialog.exec_()
        # remove reference when dialog closes
        self.dialog = None

        if reply == QMessageBox.Yes:
            api = ApiFactory.getInstance().getWorkflowApi()
            api.deleteWorkflowByName(self.parent.username, workflowName)
            self.parent.refreshTables()
