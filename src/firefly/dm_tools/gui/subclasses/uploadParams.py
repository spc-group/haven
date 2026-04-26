#!/usr/bin/env python

from dm.common.constants.dmProcessingConstants import (
    DM_EXPERIMENT_FILE_PATH_KEY,
    DM_PROCESSING_MODE_KEY,
    DM_REPROCESS_FILES_KEY,
)

from .daqUploadParamsBase import DaqUploadParamsBase


class UploadParams(DaqUploadParamsBase):

    UPLOAD_PM_DEFAULT_OPTS = ["Files", "Directory"]
    UPLOAD_PM_SINGLE_FILE_OPTS = ["Single File"]

    def __init__(self, parent=None, params={}, directoryFile=True):
        super(UploadParams, self).__init__(
            parent,
            windowTitle="Upload System Parameters",
            headerText="System Parameters for Upload",
            params=params,
        )

        self.uploadPM = self.addOptionsInputItem(
            labelText="Processing Mode",
            tooltip='<FONT> Specifies processing mode, and can be set to "files" (service plugins process individual files one at a time) or "directory" (service plugins process entire directory at once; works faster for uploads of a large number of small files) </FONT>',
            options=self.UPLOAD_PM_DEFAULT_OPTS,
            dmConfigKey=DM_PROCESSING_MODE_KEY,
        )

        self.uploadRF = self.addBooleanInputItem(
            labelText="Reprocess Files",
            tooltip="if set to True, files will be uploaded regardless of whether or not they already exist in storage and have not changed",
            dmConfigKey=DM_REPROCESS_FILES_KEY,
        )

        self.expFilePath = self.addTextInputItem(
            labelText="Experiment File Path",
            tooltip="specifies path relative to the given data directory; if set, only this file will be processed",
            dmConfigKey=DM_EXPERIMENT_FILE_PATH_KEY,
        )

        self.updateProcessAsDirectory(directoryFile)
        self.updateVals()

    def updateProcessAsDirectory(self, processAsDirectory):
        """
        Switches the UI options for configuration based on single file vs directory upload.
        """
        self.loadUploadPmOptions(not processAsDirectory)

    def loadUploadPmOptions(self, isSingleFile):
        self.uploadPM.clear()
        if isSingleFile:
            self.uploadPM.addItems(self.UPLOAD_PM_SINGLE_FILE_OPTS)
            self.uploadPM.setDisabled(True)
        else:
            self.uploadPM.addItems(self.UPLOAD_PM_DEFAULT_OPTS)
            self.uploadPM.setDisabled(False)
