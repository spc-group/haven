#!/usr/bin/env python

from dm import DmException
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .pluginList import PluginList
from .style import DM_FONT_ARIAL_KEY


class ParamsBase(QDialog):
    """
    Base Class used to create a GUI that allows defining a custom parameters dictionary within the DM application.
    """

    BOOLEAN_OPTS = ["False", "True"]

    def __init__(self, parent, windowTitle, headerText, params=None):
        super(ParamsBase, self).__init__(parent)

        if params is None:
            self.params = {}
        else:
            self.params = params

        self.grid = QGridLayout()

        self.setWindowTitle(windowTitle)

        labelFont = QFont(DM_FONT_ARIAL_KEY, 18, QFont.Bold)
        self.titleLbl = QLabel(headerText)
        self.titleLbl.setAlignment(Qt.AlignCenter)
        self.titleLbl.setFont(labelFont)
        self.grid.addWidget(self.titleLbl, 0, 0, 1, 2)

        self.labelColumnVBox = QVBoxLayout()
        self.valueColumnVBox = QVBoxLayout()

        self.labelValueHBox = QHBoxLayout()
        self.labelValueHBox.addLayout(self.labelColumnVBox)
        self.labelValueHBox.addLayout(self.valueColumnVBox)

        self.doneDialog = QPushButton("Done", self)
        self.doneDialog.setMaximumWidth(120)
        self.doneDialog.setFocusPolicy(Qt.NoFocus)
        self.doneDialog.clicked.connect(self.recordVals)

        footerHBox = QHBoxLayout()
        footerHBox.addWidget(self.doneDialog)

        self.grid.addLayout(self.labelValueHBox, 1, 0, 1, 2)
        self.grid.addLayout(footerHBox, 2, 0, 1, 2)
        self.setLayout(self.grid)

        self.knownInputWidgets = []

    def addTextInputItem(self, labelText, tooltip, dmConfigKey):
        return self._addConfigItem(
            labelText=labelText, tooltip=tooltip, dmConfigKey=dmConfigKey
        )

    def addBooleanInputItem(self, labelText, tooltip, dmConfigKey):
        return self._addConfigItem(
            labelText=labelText,
            tooltip=tooltip,
            dmConfigKey=dmConfigKey,
            options=self.BOOLEAN_OPTS,
        )

    def addOptionsInputItem(self, labelText, tooltip, options, dmConfigKey):
        return self._addConfigItem(
            labelText=labelText,
            tooltip=tooltip,
            dmConfigKey=dmConfigKey,
            options=options,
        )

    def addNumberInputItem(self, labelText, tooltip, dmConfigKey, min=0, max=100):
        return self._addConfigItem(
            labelText=labelText,
            tooltip=tooltip,
            dmConfigKey=dmConfigKey,
            min=min,
            max=max,
        )

    def _addConfigItem(
        self, labelText, tooltip, dmConfigKey, options=None, min=None, max=None
    ):
        """
        Generic function to add value inputs of different types. Please use the more specific functions above.

        :param labelText: The Label text that will be shown to user.
        :param tooltip: The tooltip that will be shown when user hovers over input widget.
        :param dmConfigKey: The configuration key that is used by the DM system.
        :param options: When specified the input will be a dropdown with the following options
        :param min: When specified the number input will have this min
        :param max: When specified the number input will have this max
        :return: input widget
        """
        if options:
            inputWidget = QComboBox()
            inputWidget.setMaximumWidth(150)
            inputWidget.addItems(options)
            inputWidget.dmOptions = options
        elif min is not None:
            inputWidget = QSpinBox()
            inputWidget.setMinimum(min)
            inputWidget.setMaximum(max)
            inputWidget.setMaximumWidth(150)
        else:
            inputWidget = QLineEdit()
            inputWidget.setMaximumWidth(200)
        inputWidget.setToolTip(tooltip)

        self.knownInputWidgets.append(inputWidget)
        self.addCustomItem(labelText, inputWidget, dmConfigKey)
        return inputWidget

    def addCustomItem(self, labelText, inputItem, dmConfigKey):
        label = QLabel(labelText)

        self.labelColumnVBox.addWidget(label)

        if isinstance(inputItem, QWidget):
            self.valueColumnVBox.addWidget(inputItem)
        elif isinstance(inputItem, QLayout):
            self.valueColumnVBox.addLayout(inputItem)
        else:
            raise DmException(
                "Error building GUI, expected a layout or widget object for: %s"
                % type(inputItem)
            )

        inputItem.dmConfigKey = dmConfigKey

    def recordVals(self):
        for inputWidget in self.knownInputWidgets:
            configKey = inputWidget.dmConfigKey
            if type(inputWidget) is QLineEdit:
                if str(inputWidget.text()).strip():
                    self.params[configKey] = str(inputWidget.text()).strip()
            if type(inputWidget) is QComboBox:
                defaultOption = inputWidget.dmOptions[0]
                currentOption = str(inputWidget.currentText())
                if defaultOption != currentOption:
                    if inputWidget.dmOptions == self.BOOLEAN_OPTS:
                        # Boolean type dropdown
                        self.params[configKey] = currentOption == "True"
                    else:
                        self.params[configKey] = currentOption
            if type(inputWidget) is QSpinBox:
                minVal = inputWidget.minimum()
                if inputWidget.value() > minVal:
                    self.params[configKey] = inputWidget.value()

        self.recordCustomVals()
        self.parseDict()
        self.done(1)

    def updateVals(self):
        """
        Execute this function at the end of derived constructor to load values from passed in params into GUI.
        """
        for inputWidget in self.knownInputWidgets:
            paramKey = inputWidget.dmConfigKey
            paramVal = self.params.get(paramKey)
            if paramVal is not None:
                if type(inputWidget) is QSpinBox:
                    inputWidget.setValue(paramVal)
                elif type(inputWidget) is QComboBox:
                    spinBoxInx = inputWidget.findText(str(paramVal))
                    inputWidget.setCurrentIndex(spinBoxInx)
                elif type(inputWidget) is QLineEdit:
                    inputWidget.setText(paramVal)

        self.updateCustomVals()

    def updateCustomVals(self):
        """
        Override this function to update custom values from passed in params.
        """
        pass

    def recordCustomVals(self):
        """
        Override this function to process value of any custom added value.
        """
        pass

    # Parses the text-dictionary to see what values already exist.
    # Disable buttons if their property is already in the dictionary.
    def parseDict(self):
        self.sendText = ""
        for key, value in list(self.params.items()):
            if isinstance(value, str):
                if len(self.sendText) == 0:
                    self.sendText = "{'" + key + "':'" + str(value) + "'"
                else:
                    self.sendText = (
                        self.sendText + ", '" + key + "':'" + str(value) + "'"
                    )
            else:
                if len(self.sendText) == 0:
                    self.sendText = "{'" + key + "':" + str(value)
                else:
                    self.sendText = self.sendText + ", '" + key + "':" + str(value)
        if len(self.sendText) > 0:
            self.sendText += "}"

    def getParams(self):
        return self.params

    # Popup to show the user common parameters
    def toggleParams(self):
        dialog = PluginList(self, self.sendText)
        dialog.exec_()
        self.sendText = dialog.getDict()
