#!/usr/bin/env python

import json

from dm.common.constants.dmFileConstants import DM_JSON_KEY
from dm.common.constants.dmObjectLabels import DM_NAME_KEY
from dm.common.constants.dmProcessingConstants import DM_STAGES_KEY
from dm.common.objects.dmObject import DmObject
from dm.common.objects.workflow import Workflow
from PyQt5.QtWidgets import QWizard

from ...apiFactory import ApiFactory
from .workflowWizardFilePage import WorkflowWizardFilePage
from .workflowWizardMetadataPage import WorkflowWizardMetadataPage
from .workflowWizardStagePage import WorkflowWizardStagePage


class WorkflowWizard(QWizard):
    def __init__(self, parent=None):
        super(WorkflowWizard, self).__init__(parent)
        self.setWindowTitle("Add Workflow")
        self.parent = parent
        self.warning = False
        self.filePage = WorkflowWizardFilePage(defaultOwner=self.parent.username)
        self.metadataPage = WorkflowWizardMetadataPage(
            defaultOwner=self.parent.username
        )
        self.stageCount = 0
        self.addPage(self.filePage)
        self.addPage(self.metadataPage)
        self.button(QWizard.FinishButton).clicked.connect(self.finish)

    def addWorkflow(self, workflow):
        api = ApiFactory.getInstance().getWorkflowApi()
        workflow = api.addWorkflow(workflow)

    def addStagePages(self, workflow: Workflow):
        """add a stage page for each stage in the workflow"""
        stages = workflow.get(DM_STAGES_KEY, {})
        for stage in stages:
            stageAttributesDict = stages[stage]
            stageAttributesDict[DM_NAME_KEY] = stage
            self.addPage(WorkflowWizardStagePage(stageAttributesDict))

    def clearStagePages(self):
        """if user has changed the workflow file, need to get rid of the pages
        from the previous file (or the blank page if there was new/no workflow file)"""
        pageIds = self.pageIds()
        # get rid of every page except the file page and info page
        for i in range(2, len(pageIds)):
            self.removePage(pageIds[i])

    def asDict(self) -> dict:
        """get the fields from all the pages as a dict"""
        fields = self.metadataPage.asDict()
        pageIds = self.pageIds()
        stages = {}
        for i in range(2, len(pageIds)):
            page = self.page(pageIds[i])
            stages.update(page.asDict())
        fields[DM_STAGES_KEY] = stages
        return fields

    def finish(self) -> Workflow:
        """fields from the wizard are written to the file given by the user
        and calls the api to create the workflow"""
        workflowDict = self.asDict()
        filename = self.fileNameLineEdit.text()
        with open(filename, "w") as f:
            if filename.endswith(".py"):
                f.write(str(workflowDict))
            elif filename.endswith(DM_JSON_KEY):
                f.write(json.dumps(workflowDict, indent=DmObject.PPRINT_INDENT))
        api = ApiFactory.getInstance().getWorkflowApi()
        api.upsertWorkflow(workflowDict)

    def update(self, workflow=None):
        """populate pages with info from workflow. if no workflow, clear the wizard"""
        self.clearStagePages()
        if workflow:
            self.metadataPage.fill(workflow)
            self.addStagePages(workflow)
        else:
            # new file blank pages
            self.metadataPage.fill(Workflow({}))
            self.addPage(WorkflowWizardStagePage({}))
