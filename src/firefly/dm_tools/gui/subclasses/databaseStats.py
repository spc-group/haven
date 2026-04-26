#!/usr/bin/env python

from dm.common.constants.dmDatabaseConstants import (
    DM_AVERAGE_FILE_SIZE_KEY,
    DM_COLLECTION_SIZE_KEY,
    DM_MAX_FILE_SIZE_KEY,
    DM_MIN_FILE_SIZE_KEY,
    DM_STD_DEV_FILE_SIZE_KEY,
)
from dm.common.constants.dmExperimentConstants import DM_EXPERIMENT_NAME_KEY
from dm.common.constants.dmFileConstants import (
    DM_B_KEY,
    DM_GB_KEY,
    DM_KB_KEY,
    DM_MB_KEY,
)
from dm.common.constants.dmProcessingConstants import DM_COUNT_FILES_KEY
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ..apiFactory import ApiFactory
from .style import DM_FONT_ARIAL_KEY


class DatabaseStats(QDialog):
    def __init__(self, parent=None, experimentName=None):
        super(DatabaseStats, self).__init__(parent)
        self.fileCatApi = ApiFactory.getInstance().getFileCatApi()
        stats = self.fileCatApi.getExperimentFileCollectionStats(experimentName)

        self.grid = QGridLayout()

        self.setWindowTitle("Statistics")

        labelFont = QFont(DM_FONT_ARIAL_KEY, 18, QFont.Bold)
        self.titleLbl = QLabel("Database Statistics")
        self.titleLbl.setAlignment(Qt.AlignCenter)
        self.titleLbl.setFont(labelFont)
        self.grid.addWidget(self.titleLbl, 0, 0, 1, 2)

        vBox = QVBoxLayout()
        labelStrs = [
            f"Average File Size: {self.checkSize(stats.get(DM_AVERAGE_FILE_SIZE_KEY, 0))}",
            f"Collection Size: {self.checkSize(stats.get(DM_COLLECTION_SIZE_KEY, 0))}",
            f"Experiment Name: {stats.get(DM_EXPERIMENT_NAME_KEY, '-')}",
            f"Max File Size: {self.checkSize(stats.get(DM_MAX_FILE_SIZE_KEY, 0))}",
            f"Min File Size: {self.checkSize(stats.get(DM_MIN_FILE_SIZE_KEY, 0))}",
            f"Number of Files: {stats.get(DM_COUNT_FILES_KEY, 0)}",
            f"Standard Deviation File Size: {self.checkSize(stats.get(DM_STD_DEV_FILE_SIZE_KEY, 0))}",
        ]

        for labelStr in labelStrs:
            qLabel = QLabel(labelStr)
            vBox.addWidget(qLabel)

        doneDialog = QPushButton("Done", self)
        doneDialog.setMaximumWidth(120)
        doneDialog.setFocusPolicy(Qt.NoFocus)
        doneDialog.clicked.connect(self.done)
        hBox9 = QHBoxLayout()
        hBox9.addWidget(doneDialog)

        self.grid.addLayout(vBox, 1, 0, 1, 2)
        self.grid.addLayout(hBox9, 2, 0, 1, 2)
        self.setLayout(self.grid)

    def checkSize(self, fsize):
        if fsize == 0:
            return f"{fsize} {DM_B_KEY}"
        elif 0 < fsize < 1000:
            return f"{round(fsize, 2)} {DM_B_KEY}"
        elif 1000 <= fsize <= 1000000:
            return f"{round(fsize/1000, 2)} {DM_KB_KEY}"
        elif 1000000 <= fsize <= 1000000000:
            return f"{round(fsize/1000000, 2)} {DM_MB_KEY}"
        elif fsize > 1000000000:
            return f"{round(fsize/1000000000, 2)} {DM_GB_KEY}"
        return ""
