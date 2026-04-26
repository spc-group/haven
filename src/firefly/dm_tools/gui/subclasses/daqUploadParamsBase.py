#!/usr/bin/env python
from dm.common.constants.dmFileConstants import DM_USE_ANALYSIS_DIRECTORY_AS_ROOT_KEY
from dm.common.constants.dmProcessingConstants import (
    DM_DEST_DIRECTORY_KEY,
    DM_EXCLUDE_FILE_EXTENSIONS_KEY,
    DM_FILE_PATH_PATTERN_KEY,
    DM_INCLUDE_FILE_EXTENSIONS_KEY,
    DM_PROCESS_HIDDEN_FILES_KEY,
    DM_REMOVE_SOURCE_FILES_KEY,
    DM_SKIP_CATALOG_KEY,
    DM_SKIP_CHECKSUM_KEY,
    DM_SKIP_TRANSFER_KEY,
    DM_WORKFLOW_ARGS_KEY,
    DM_WORKFLOW_JOB_OWNER_KEY,
    DM_WORKFLOW_NAME_KEY,
    DM_WORKFLOW_OWNER_KEY,
)

from .paramsBase import ParamsBase


class DaqUploadParamsBase(ParamsBase):

    def __init__(self, parent, windowTitle, headerText, params):
        super(DaqUploadParamsBase, self).__init__(
            parent, windowTitle, headerText, params
        )

        self.useAnalysisDirectory = self.addBooleanInputItem(
            labelText="Upload to Analysis Directory",
            tooltip="Files will upload to analysis directory instead of data directory",
            dmConfigKey=DM_USE_ANALYSIS_DIRECTORY_AS_ROOT_KEY,
        )

        self.PHF = self.addBooleanInputItem(
            labelText="Process Hidden Files",
            tooltip="If set to True, hidden files will be processed",
            dmConfigKey=DM_PROCESS_HIDDEN_FILES_KEY,
        )

        self.destDir = self.addTextInputItem(
            labelText="Destination Directory",
            tooltip="Specifies directory path relative to experiment root directory where files will be stored",
            dmConfigKey=DM_DEST_DIRECTORY_KEY,
        )

        self.includeExts = self.addTextInputItem(
            labelText="Include File Extensions",
            tooltip='Comma-separated list of file extensions that should be processed (e.g., "hdf5,h5"); if not provided, all files will be processed',
            dmConfigKey=DM_INCLUDE_FILE_EXTENSIONS_KEY,
        )

        self.excludeExts = self.addTextInputItem(
            labelText="Exclude File Extensions",
            tooltip='Comma-separated list of file extensions that should be not processed (e.g., "txt,log,doc"); if not provided, all files will be processed',
            dmConfigKey=DM_EXCLUDE_FILE_EXTENSIONS_KEY,
        )

        self.filePathPattern = self.addTextInputItem(
            labelText="File Path Pattern",
            tooltip='Unix shell-style wildcard pattern of paths relative to the data directory that should be processed (e.g., "dir1/sample123/*.h5"); if not specified, all files will be processed',
            dmConfigKey=DM_FILE_PATH_PATTERN_KEY,
        )

        self.workflowName = self.addTextInputItem(
            labelText="Workflow Name",
            tooltip="specifies processing workflow name; must be used together with workflowOwner",
            dmConfigKey=DM_WORKFLOW_NAME_KEY,
        )

        self.workflowOwner = self.addTextInputItem(
            labelText="Workflow Owner",
            tooltip="Specifies processing workflow owner; must be used together with workflowName",
            dmConfigKey=DM_WORKFLOW_OWNER_KEY,
        )

        self.workflowArgs = self.addTextInputItem(
            labelText="Workflow Arguments",
            tooltip="Specifies processing workflow arguments in the <key>:<value> format; multiple arguments should be separated by spaces",
            dmConfigKey=DM_WORKFLOW_ARGS_KEY,
        )

        self.workflowJobOwner = self.addTextInputItem(
            labelText="Workflow Job Owner",
            tooltip="Specifies owner of the workflow processing job; by default user submitting request will also own processing job",
            dmConfigKey=DM_WORKFLOW_JOB_OWNER_KEY,
        )

        self.removeSourceFiles = self.addBooleanInputItem(
            labelText="Remove Source Files",
            tooltip="Source files will be removed after transfer to the storage directory. This is not applicable to uploads using directory mode.",
            dmConfigKey=DM_REMOVE_SOURCE_FILES_KEY,
        )

        self.skipTransfer = self.addBooleanInputItem(
            labelText="Skip File Transfer",
            tooltip="Files will not be transferred to the storage directory",
            dmConfigKey=DM_SKIP_TRANSFER_KEY,
        )

        self.skipChecksum = self.addBooleanInputItem(
            labelText="Skip File Checksum",
            tooltip="Do not include checksum for file cataloging",
            dmConfigKey=DM_SKIP_CHECKSUM_KEY,
        )

        self.skipCatalog = self.addBooleanInputItem(
            labelText="Skip File Catalog",
            tooltip="Files will not be cataloged",
            dmConfigKey=DM_SKIP_CATALOG_KEY,
        )
