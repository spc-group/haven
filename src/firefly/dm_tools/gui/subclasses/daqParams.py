#!/usr/bin/env python

from dm.common.constants.dmProcessingConstants import (
    DM_MAX_RUN_TIME_IN_HOURS_KEY,
    DM_PROCESS_EXISTING_FILES_KEY,
    DM_UPLOAD_DATA_DIRECTORY_ON_EXIT_KEY,
    DM_UPLOAD_DEST_DIRECTORY_ON_EXIT_KEY,
)
from PyQt5.QtWidgets import QFileDialog, QHBoxLayout, QLineEdit, QPushButton

from .daqUploadParamsBase import DaqUploadParamsBase


class DaqParams(DaqUploadParamsBase):
    def __init__(self, parent=None, params={}):
        super(DaqParams, self).__init__(
            parent,
            windowTitle="DAQ System Parameters",
            headerText="System Parameters for DAQ",
            params=params,
        )

        self.daqMRH = self.addNumberInputItem(
            labelText="Max Runtime In Hours",
            tooltip="Specifies maximum data acquisition run time in hours",
            min=0,
            max=10000,
            dmConfigKey=DM_MAX_RUN_TIME_IN_HOURS_KEY,
        )

        self.daqUDDE = self.addTextInputItem(
            labelText="Data Dir On Exit",
            tooltip="Specifies URL of the data directory that should be uploaded after data acquisition completes",
            dmConfigKey=DM_UPLOAD_DATA_DIRECTORY_ON_EXIT_KEY,
        )

        self.daqCE = self.addBooleanInputItem(
            labelText="Process Existing",
            tooltip="If set to True, existing files will be processed",
            dmConfigKey=DM_PROCESS_EXISTING_FILES_KEY,
        )

        # Custom input item.
        self.horizontalUDestLayout = QHBoxLayout()

        self.daqUDestE = QLineEdit()
        self.daqUDestBtn = QPushButton("Browse")
        self.daqUDestBtn.clicked.connect(
            lambda: self.dirEntry(
                "Destination Directory on Exit", "uploadDestDirectoryOnExit"
            )
        )
        self.daqUDestE.setMaximumWidth(100)
        self.daqUDestE.setToolTip(
            "Specifies directory path relative to experiment root directory where uploaded files should be stored"
        )

        self.horizontalUDestLayout.addWidget(self.daqUDestE)
        self.horizontalUDestLayout.addWidget(self.daqUDestBtn)
        self.addCustomItem(
            "Destination Dir On Exit",
            self.horizontalUDestLayout,
            DM_UPLOAD_DEST_DIRECTORY_ON_EXIT_KEY,
        )

        self.updateVals()

    def updateCustomVals(self):
        key = self.horizontalUDestLayout.dmConfigKey
        value = self.params.get(key)

        if value is not None:
            self.daqUDestE.setText(value)

    def recordCustomVals(self):
        if str(self.daqUDestE.text()).strip():
            paramsKey = self.horizontalUDestLayout.dmConfigKey
            self.params[paramsKey] = str(self.daqUDestE.text()).strip()

    # InputDialog popup for directory selection
    def dirEntry(self, header, actual):
        # Displays the file system for the user to navigate
        dialog = QFileDialog()
        dialog.setWindowTitle(header)
        dialog.setFileMode(QFileDialog.DirectoryOnly)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        if dialog.exec_():
            directory = dialog.selectedFiles()[0]
            self.daqUDestE.setText(directory)
