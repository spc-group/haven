#!/usr/bin/env python

import re

from dm.common.constants.dmObjectLabels import DM_NAME_KEY
from dm.common.constants.dmProcessingConstants import DM_SKIP_PLUGINS_KEY
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


class PluginList(QDialog):
    def __init__(self, parent=None, sendText=None):
        super(PluginList, self).__init__(parent)

        self.sendText = sendText

        self.grid = QGridLayout()

        self.setWindowTitle("System Parameters")

        labelFont = QFont(DM_FONT_ARIAL_KEY, 18, QFont.Bold)
        self.titleLbl = QLabel("Select plugins to skip")
        self.titleLbl.setAlignment(Qt.AlignCenter)
        self.titleLbl.setFont(labelFont)
        self.grid.addWidget(self.titleLbl, 0, 0, 1, 2)

        self.experimentDsApi = ApiFactory.getInstance().getExperimentDaqApi()
        self.pluginList = self.experimentDsApi.listProcessingPlugins()
        self.pluginList = [plugin.get(DM_NAME_KEY) for plugin in self.pluginList]

        vBox1 = QVBoxLayout()
        for plugin in self.pluginList:
            b1 = QPushButton(plugin)
            b1.clicked.connect(self.setPlugin)
            vBox1.addWidget(b1)

        doneDialog = QPushButton("Done", self)
        doneDialog.setMaximumWidth(120)
        doneDialog.setFocusPolicy(Qt.NoFocus)
        doneDialog.clicked.connect(self.done)
        hBox8 = QHBoxLayout()
        hBox8.addWidget(doneDialog)

        self.grid.addLayout(vBox1, 1, 0)
        self.grid.addLayout(hBox8, 3, 0, 1, 2)
        self.setLayout(self.grid)

    def getDict(self):
        return self.sendText

    # Correctly pulls any plugins from the sending dictionary, adds new plugins to the text list, and appends the
    # list to the sending dictionary
    def setPlugin(self):
        text = self.sender().text()
        plugins = ""
        readingPlugins = False
        pluginInFront = False
        count = 0
        for word in re.split("(:|,|;)", str(self.sendText)):
            if readingPlugins:
                if word in self.pluginList:
                    plugins = plugins + word + ","
                    self.sendText = re.sub(str(word) + ",", "", str(self.sendText))
                    if pluginInFront:
                        self.sendText = re.sub(str(word) + ";", "", str(self.sendText))
                    self.sendText = re.sub(str(word), "", str(self.sendText))
                    continue
                elif word == ";":
                    readingPlugins = False
                    continue
            if word == DM_SKIP_PLUGINS_KEY:
                readingPlugins = True
                if count == 0:
                    pluginInFront = True
                    self.sendText = re.sub("skipPlugins:", "", str(self.sendText))
                else:
                    self.sendText = re.sub(";skipPlugins:", "", str(self.sendText))
            count += 1
        plugins = plugins + text
        if len(str(self.sendText)) == 0:
            self.sendText = "skipPlugins:" + plugins
        else:
            self.sendText = self.sendText + ";skipPlugins:" + plugins
        self.parseDict()

    # Parses the text-dictionary to see what values already exist.
    # Disable buttons if their property is already in the dictionary.
    def parseDict(self):
        for i in range(self.grid.count()):
            item = self.grid.itemAt(i)
            if type(item) is QPushButton:
                item.setEnabled(True)
        readingPlugins = 0
        for word in re.split("(:|,|;)", self.sendText):
            if readingPlugins:
                if word in self.pluginList:
                    widgets = list(self.traverse(self.grid.children()))
                    for widget in widgets:
                        if type(widget) is QPushButton and widget.text() is word:
                            widget.setEnabled(False)
                elif word == ";":
                    readingPlugins = 0
            if word == DM_SKIP_PLUGINS_KEY:
                readingPlugins = 1

    # Recursively parses the list for sub-layouts and returns a list of the widgets within them
    def traverse(self, o, tree_types=(QVBoxLayout, QHBoxLayout, list)):
        if isinstance(o, tree_types):
            for value in o:
                if type(value) is QVBoxLayout or type(value) is QHBoxLayout:
                    items = [
                        value.itemAt(item).widget() for item in range(value.count())
                    ]
                    for subvalue in self.traverse(items, tree_types):
                        yield subvalue
                else:
                    for subvalue in self.traverse(value, tree_types):
                        yield subvalue
        else:
            yield o
