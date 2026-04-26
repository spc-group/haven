#!/usr/bin/env python
import time

from dm.common.constants.dmExperimentConstants import DM_EXPERIMENT_NAME_KEY
from dm.common.constants.dmFileConstants import DM_COMPRESSION_KEY
from dm.common.constants.dmObjectLabels import DM_ID_KEY, DM_NAME_KEY
from dm.common.constants.dmProcessingConstants import DM_PROCESSING_ERRORS_KEY
from dm.common.exceptions.objectNotFound import ObjectNotFound
from PyQt5.QtCore import QItemSelectionModel, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPalette
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from .apiFactory import ApiFactory
from .subclasses.customFileModel import CustomFileModel
from .subclasses.customSelectionModel import CustomSelectionModel
from .subclasses.customStyledDelegate import CustomStyledDelegate
from .subclasses.style import (
    DM_FONT_ARIAL_KEY,
    DM_GUI_DARK_GREY,
    DM_GUI_LIGHT_GREY,
    DM_GUI_WHITE,
)


# Define the Files tab content:
class FileTab(QWidget):

    COMPRESSION_ALG = DM_PROCESSING_ERRORS_KEY

    MIN_COMPRESSION_COLUMN_WIDTH = 75
    DEFAULT_NAME_COLUMN_WIDTH = 250
    DEFAULT_PATH_COLUMN_WIDTH = 250

    def __init__(self, stationName, parent, id=-1):
        super(FileTab, self).__init__(parent)
        self.stationName = stationName
        self.parent = parent
        self.selectedPage = 1
        self.showingDetails = 0
        self.showingCompressionView = 0
        self.tempTable = []
        self.fileCatApi = ApiFactory.getInstance().getFileCatApi()
        self.fileTabLayout()

    # GUI layout where each block is a row on the grid
    def fileTabLayout(self):
        grid = QGridLayout()

        labelFont = QFont(DM_FONT_ARIAL_KEY, 18, QFont.Bold)
        self.lbl = QLabel(self.stationName + " File List", self)
        self.lbl.setAlignment(Qt.AlignCenter)
        self.lbl.setFont(labelFont)
        grid.addWidget(self.lbl, 0, 0, 1, 5)

        self.backBtn = QPushButton("Back", self)
        self.backBtn.setFocusPolicy(Qt.NoFocus)
        self.backBtn.clicked.connect(self.checkBack)
        self.backBtn.setMinimumWidth(100)
        grid.addWidget(self.backBtn, 0, 0, Qt.AlignLeft)

        grid.addItem(QSpacerItem(20, 30, QSizePolicy.Expanding), 2, 0)

        alternate = QPalette()
        alternate.setColor(QPalette.AlternateBase, DM_GUI_LIGHT_GREY)
        alternate.setColor(QPalette.Base, DM_GUI_WHITE)

        # Add GUI components for filtering
        self.searchFilterButton = QPushButton("Search")
        self.searchFilterButton.setFocusPolicy(Qt.NoFocus)
        self.searchFilterButton.setEnabled(False)
        self.searchFilterButton.clicked.connect(self.enableFullFilter)

        self.filterName = QLineEdit()
        self.filterName.setMinimumWidth(self.DEFAULT_NAME_COLUMN_WIDTH)
        self.filterName.setPlaceholderText("Name")
        self.filterName.returnPressed.connect(self.searchFilterButton.click)
        self.filterSize = QLineEdit()
        self.filterSize.setMaximumWidth(100)
        self.filterSize.setPlaceholderText("Size")
        self.filterSize.returnPressed.connect(self.searchFilterButton.click)
        self.filterDate = QLineEdit()
        self.filterDate.setMaximumWidth(100)
        self.filterDate.setPlaceholderText("Last Modified")
        self.filterDate.returnPressed.connect(self.searchFilterButton.click)
        self.filterPath = QLineEdit()
        self.filterPath.setMinimumWidth(self.DEFAULT_PATH_COLUMN_WIDTH)
        self.filterPath.setPlaceholderText("Path")
        self.filterPath.returnPressed.connect(self.searchFilterButton.click)

        filterLayout = QHBoxLayout()
        filterLayout.addWidget(self.filterName)
        filterLayout.addWidget(self.filterSize)
        filterLayout.addWidget(self.filterDate)
        filterLayout.addWidget(self.filterPath)
        filterLayout.addWidget(self.searchFilterButton)

        grid.addLayout(filterLayout, 3, 0, 1, 5)

        # Add Table

        # Create Model
        self.fileTableModel = CustomFileModel(dmStationGUI=self.parent)
        self.fileTableModel.updateBins.connect(self.updateBinButtons)
        self.fileTableModel.fullFileListLoaded.connect(self.allFilesAreLoaded)
        self.fileTableModel.loadingFilesException.connect(
            self.loadingFilesExceptionOccured
        )
        self.fileTableModel.quitFileLoadingProcess.connect(
            self.quitBackgroundFilesThreadProgressDialog
        )
        self.fileTableModel.longFileLoadingProcessProgress.connect(
            self.backgroundLoadingFilesLongProcessProgress
        )
        self.fileTableModel.finalizeJumpToPage.connect(self.finalizeNewPage)
        self.fileTableModel.loadingPageException.connect(self.jumpToNewPageException)

        # Create Table
        self.fileTableView = QTableView()
        self.fileTableView.setModel(self.fileTableModel)
        self.fileTableView.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.fileTableView.setSelectionMode(QAbstractItemView.SingleSelection)

        # Configure table
        self.fileTableView.setAlternatingRowColors(True)
        self.fileTableView.setPalette(alternate)
        self.fileTableView.horizontalHeader().setStretchLastSection(True)
        self.fileTableView.setSelectionMode(QAbstractItemView.SingleSelection)

        self.fileSelectionModel = QItemSelectionModel(self.fileTableModel)
        self.fileTableView.setSelectionModel(self.fileSelectionModel)

        header = self.fileTableView.horizontalHeader()

        header.setSectionResizeMode(CustomFileModel.COMPRESSION_IDX, QHeaderView.Fixed)

        header.resizeSection(
            CustomFileModel.COMPRESSION_IDX, self.MIN_COMPRESSION_COLUMN_WIDTH
        )
        header.resizeSection(CustomFileModel.NAME_IDX, self.DEFAULT_NAME_COLUMN_WIDTH)
        header.resizeSection(CustomFileModel.PATH_IDX, self.DEFAULT_PATH_COLUMN_WIDTH)

        self.fileSelectionModel.selectionChanged.connect(self.fileModelSelectionChanged)

        self.fileTableView.clicked.connect(self.enableDetails)
        self.fileTableView.doubleClicked.connect(self.toggleDetails)

        # Add table that will show details for each file
        self.detailsTable = QTableWidget()
        self.detailsTable.setAlternatingRowColors(True)
        self.detailsTable.setPalette(alternate)
        self.detailsTable.setItemDelegate(CustomStyledDelegate(self.detailsTable, self))
        self.detailsTable.setSelectionModel(
            CustomSelectionModel(self, self.detailsTable.model())
        )
        grid.addWidget(self.detailsTable, 4, 0, 1, 5)
        grid.addWidget(self.fileTableView, 4, 0, 1, 5)

        # Add functionality below table shuch as show details and paginator
        self.detailBtn = QPushButton("Show Details", self)
        self.detailBtn.setFocusPolicy(Qt.NoFocus)
        self.detailBtn.clicked.connect(self.toggleDetails)
        self.detailBtn.setMaximumWidth(130)
        self.detailBtn.setEnabled(False)

        self.updateCompressionBtn = QPushButton("Update Compression", self)
        self.updateCompressionBtn.setMaximumWidth(150)
        self.updateCompressionBtn.clicked.connect(self.toggleCompressionView)

        self.updateAllItemsBtn = QPushButton()
        self.updateAllItemsBtn.hide()
        self.updateAllItemsBtn.clicked.connect(self.performCompressionUpdate)

        self.compressAllItemsBtn = QPushButton()
        self.compressAllItemsBtn.hide()
        self.compressAllItemsBtn.clicked.connect(self.compressAllItems)

        self.decompressAllItemsBtn = QPushButton()
        self.decompressAllItemsBtn.hide()
        self.decompressAllItemsBtn.clicked.connect(self.decompressAllItems)

        self.applyDefaultCompressionText()

        self.btnPal = QPalette()
        self.btnPal.setColor(QPalette.Button, DM_GUI_DARK_GREY)
        # Paginator
        self.tabStart = QPushButton("1", self)
        self.tabStart.setFocusPolicy(Qt.NoFocus)
        self.tabStart.clicked.connect(self.showFirst)
        self.tabStart.setMaximumWidth(50)
        self.tabStart.setAutoFillBackground(True)
        self.tabStart.setPalette(self.btnPal)
        self.tabStart.update()
        self.tabPrev = QPushButton("2", self)
        self.tabPrev.setFocusPolicy(Qt.NoFocus)
        self.tabPrev.clicked.connect(self.showPrevious)
        self.tabPrev.setMaximumWidth(50)
        self.tabCurrent = QPushButton("3", self)
        self.tabCurrent.setFocusPolicy(Qt.NoFocus)
        self.tabCurrent.clicked.connect(self.showCurrent)
        self.tabCurrent.setMaximumWidth(50)
        self.tabNext = QPushButton(">>", self)
        self.tabNext.setFocusPolicy(Qt.NoFocus)
        self.tabNext.clicked.connect(self.showNext)
        self.tabNext.setMaximumWidth(50)
        self.tabEnd = QPushButton("100", self)
        self.tabEnd.setFocusPolicy(Qt.NoFocus)
        self.tabEnd.clicked.connect(self.showLast)
        self.tabEnd.setMaximumWidth(50)
        self.jumpTab = QLineEdit()
        self.jumpTab.setMaximumWidth(50)
        self.jumpBtn = QPushButton("Goto")
        self.jumpBtn.setFocusPolicy(Qt.NoFocus)
        self.jumpBtn.clicked.connect(self.showJump)
        self.jumpBtn.setMaximumWidth(50)

        hbox1 = QHBoxLayout()
        hbox1.addWidget(self.tabStart)
        hbox1.addWidget(self.tabPrev)
        hbox1.addWidget(self.tabCurrent)
        hbox1.addWidget(self.tabNext)
        hbox1.addWidget(self.tabEnd)
        hbox1.addWidget(self.jumpTab)
        hbox1.addWidget(self.jumpBtn)

        hbox1.addWidget(self.updateAllItemsBtn)
        hbox1.addWidget(self.compressAllItemsBtn)
        hbox1.addWidget(self.decompressAllItemsBtn)

        hbox1.addStretch()

        hbox2 = QHBoxLayout()
        hbox2.addWidget(self.updateCompressionBtn)
        hbox2.addWidget(self.detailBtn)

        grid.addLayout(hbox1, 5, 0, 1, 2)
        grid.addLayout(hbox2, 5, 3, 1, 1)

        grid.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding), 6, 0)

        self.compressionProgressDialog = QProgressDialog(self)
        self.compressionProgressDialog.setMinimumWidth(500)
        # Set max limits here & then set value to maximum to keep the Dialog from
        # popping up when application starts.
        self.compressionProgressDialog.setMaximum(100)
        self.compressionProgressDialog.setValue(
            self.compressionProgressDialog.maximum()
        )

        self.compressionProgressDialog.hide()

        self.backgroundFilesThreadProgressDialog = None

        self.setLayout(grid)

    def resetPaginatorButtonLabels(self):
        self.tabStart.setText("1")
        self.tabPrev.setText("2")
        self.tabCurrent.setText("3")
        self.tabNext.setText(">>")
        self.tabEnd.setText("100")

    def fileModelSelectionChanged(self, selected, deselected):
        if self.showingCompressionView:
            if len(self.fileSelectionModel.selectedRows()):
                self.updateAllItemsBtn.setText("Update Selection")
                self.compressAllItemsBtn.setText("Compress Selection")
                self.decompressAllItemsBtn.setText("Decompress Selection")
                self.updateAllItemsBtn.setToolTip(
                    "Utilize row compression checkboxes to determine compressed or decompressed state for selected files."
                )
                self.compressAllItemsBtn.setToolTip("Compress selected files.")
                self.decompressAllItemsBtn.setToolTip("Decompress selected files")
            else:
                self.applyDefaultCompressionText()

    def applyDefaultCompressionText(self):
        self.updateAllItemsBtn.setText("Update All")
        self.compressAllItemsBtn.setText("Compress All")
        self.decompressAllItemsBtn.setText("Decompress All")
        self.updateAllItemsBtn.setToolTip(
            "Utilize row compression checkboxes to determine compressed or decompressed state for all files."
        )
        self.compressAllItemsBtn.setToolTip("Compress every file.")
        self.decompressAllItemsBtn.setToolTip("Decompress every file")

    def toggleCompressionView(self):
        if self.showingCompressionView == 0:
            # Change to compression view
            self.updateCompressionBtn.hide()
            self.fileTableModel.showAllInOnePage()
            self.fileTableModel.showCompressionCheckboxes = True
            self.showingCompressionView = 1
            self.fileTableView.setSelectionMode(QAbstractItemView.MultiSelection)
            self.jumpBtn.hide()
            self.jumpTab.hide()
            self.detailBtn.hide()

            self.updateAllItemsBtn.show()
            self.compressAllItemsBtn.show()
            self.decompressAllItemsBtn.show()
        else:
            self.fileTableModel.restoreToOriginalPagination()
            self.updateCompressionBtn.show()
            self.fileTableModel.showCompressionCheckboxes = False
            self.showingCompressionView = 0
            self.fileTableView.setSelectionMode(QAbstractItemView.SingleSelection)
            self.jumpBtn.show()
            self.jumpTab.show()
            self.detailBtn.show()

            self.updateAllItemsBtn.hide()
            self.compressAllItemsBtn.hide()
            self.decompressAllItemsBtn.hide()

    def decompressAllItems(self):
        self.changeCompressionBoolForFiles(False)
        self.performCompressionUpdate()

    def compressAllItems(self):
        self.changeCompressionBoolForFiles(True)
        self.performCompressionUpdate()

    def changeCompressionBoolForFiles(self, booleanVal):
        data = self.getCompressionManipulationData()
        for file in data:
            file[CustomFileModel.COMPRESSION_BOOL_IDX] = booleanVal

    def getCompressionManipulationData(self):
        visibleData = self.fileTableModel.visibleData
        if len(self.fileSelectionModel.selectedRows()):
            data = []
            for index in self.fileSelectionModel.selectedRows():
                row = index.row()
                data.append(visibleData[row])

            return data
        else:
            return visibleData

    def performCompressionUpdate(self):
        data = self.getCompressionManipulationData()
        self.fileSelectionModel.clearSelection()
        experimentName = self.parent.generalSettings[DM_NAME_KEY]

        self.updateAllItemsBtn.setEnabled(False)
        self.decompressAllItemsBtn.setEnabled(False)
        self.compressAllItemsBtn.setEnabled(False)

        self.compressionProgressDialog.setLabelText("Compression Starting")
        self.compressionProgressDialog.setMaximum(len(data))
        self.compressionProgressDialog.setWindowTitle(
            "Updating compression for: " + experimentName
        )
        self.compressionProgressDialog.setCancelButton(None)
        self.compressionProgressDialog.show()
        self.compressionThread = CompressionThread(
            data, experimentName, self.stationName, self.COMPRESSION_ALG
        )
        self.compressionThread.madeProgress.connect(self.compressionMadeProgress)

        self.compressionThread.finished.connect(self.compressionThreadFinished)
        self.compressionThread.start()

    def compressionMadeProgress(self, finishedItem, path):
        finishedItem = finishedItem + 1
        self.compressionProgressDialog.setValue(finishedItem)
        total = int(self.compressionProgressDialog.maximum())
        label = "Processing File: " + str(finishedItem) + "/" + str(total) + "\n"
        label += path

        self.compressionProgressDialog.setLabelText(label)

    def compressionThreadFinished(self):
        self.compressionThread.quit()
        self.compressionProgressDialog.hide()

        self.updateAllItemsBtn.setEnabled(True)
        self.decompressAllItemsBtn.setEnabled(True)
        self.compressAllItemsBtn.setEnabled(True)

    def backgroundLoadingFilesLongProcessProgress(self, finished, total):
        if self.backgroundFilesThreadProgressDialog is None:
            self.backgroundFilesThreadProgressDialog = QProgressDialog()
            self.backgroundFilesThreadProgressDialog.setLabelText(
                "Loading Files. Upon completion file compression and filter will be available."
            )
            self.backgroundFilesThreadProgressDialog.setMaximum(total)
            self.backgroundFilesThreadProgressDialog.setWindowTitle("Loading Files")
            self.backgroundFilesThreadProgressDialog.setCancelButton(None)
            self.backgroundFilesThreadProgressDialog.show()

        self.backgroundFilesThreadProgressDialog.setValue(finished)

    def quitBackgroundFilesThreadProgressDialog(self):
        if self.backgroundFilesThreadProgressDialog is not None:
            self.backgroundFilesThreadProgressDialog.hide()
            self.backgroundFilesThreadProgressDialog = None

    def updateList(self):
        experimentName = self.parent.generalSettings[DM_NAME_KEY]
        self.lbl = QLabel(experimentName + " File List", self)

        self.fileTableView.setSortingEnabled(True)
        self.fileTableView.clearSelection()

        self.allFilesAreLoaded(loaded=False)

        self.filterName.setText("")
        self.filterSize.setText("")
        self.filterDate.setText("")
        self.filterPath.setText("")

        self.fileTableModel.loadNewExperiment(experimentName)

    def updateBinButtons(self, binCount):
        self.clearButtonSelection()
        self.resetPaginatorButtonLabels()
        self.highlightFirstPageButton()
        self.tabEnd.setText(str(int(binCount)))
        if binCount == 0 or binCount == 1:
            self.tabStart.hide()
            self.tabPrev.hide()
            self.tabCurrent.hide()
            self.tabNext.hide()
            self.tabEnd.hide()
        elif binCount == 2:
            self.tabStart.show()
            self.tabPrev.hide()
            self.tabCurrent.hide()
            self.tabNext.hide()
            self.tabEnd.show()
        elif binCount == 3:
            self.tabStart.show()
            self.tabPrev.show()
            self.tabCurrent.hide()
            self.tabNext.hide()
            self.tabEnd.show()
            self.tabCurrent.setText("2")
        elif binCount == 4:
            self.tabStart.show()
            self.tabPrev.show()
            self.tabCurrent.show()
            self.tabNext.hide()
            self.tabEnd.show()
            self.tabPrev.setText("2")
            self.tabCurrent.setText("3")
        elif binCount == 5:
            self.tabStart.show()
            self.tabPrev.show()
            self.tabCurrent.show()
            self.tabNext.show()
            self.tabEnd.show()
            self.tabPrev.setText("2")
            self.tabCurrent.setText("3")
            self.tabNext.setText("4")
        else:
            self.tabStart.show()
            self.tabPrev.show()
            self.tabCurrent.show()
            self.tabNext.show()
            self.tabEnd.show()

    def showFirst(self, qtChecked=0, loadData=True):
        self.clearButtonSelection()
        self.tabPrev.setText("2")
        self.tabCurrent.setText("3")
        if self.fileTableModel.pageCount > 5:
            self.tabNext.setText(">>")
        else:
            self.tabNext.setText("4")
        self.highlightFirstPageButton()
        if loadData:
            self.navigateToNewPage()

    def highlightFirstPageButton(self):
        self.tabStart.setAutoFillBackground(True)
        self.tabStart.setPalette(self.btnPal)
        self.tabStart.update()
        self.selectedPage = 1

    def showPrevious(self, qtChecked=0, loadData=True):
        self.clearButtonSelection()
        if str(self.tabPrev.text()) == "2":
            self.tabPrev.setAutoFillBackground(True)
            self.tabPrev.setPalette(self.btnPal)
            self.tabPrev.update()
            self.selectedPage = 2
        elif self.selectedPage == 4:
            self.tabPrev.setText("2")
            self.selectedPage -= 1
            self.tabCurrent.setText(str(int(self.selectedPage)))
            self.tabCurrent.setAutoFillBackground(True)
            self.tabCurrent.setPalette(self.btnPal)
            self.tabCurrent.update()
        elif str(self.tabNext.text()) == str(int(self.fileTableModel.pageCount - 1)):
            self.tabNext.setText(">>")
            self.selectedPage = int(self.fileTableModel.pageCount) - 3
            self.tabCurrent.setText(str(int(self.selectedPage)))
            self.tabCurrent.setAutoFillBackground(True)
            self.tabCurrent.setPalette(self.btnPal)
            self.tabCurrent.update()
        else:
            self.tabNext.setText(">>")
            self.selectedPage -= 1
            self.tabCurrent.setText(str(int(self.selectedPage)))
            self.tabCurrent.setAutoFillBackground(True)
            self.tabCurrent.setPalette(self.btnPal)
            self.tabCurrent.update()
        if loadData:
            self.navigateToNewPage()

    def showCurrent(self, qtChecked=0, loadData=True):
        self.clearButtonSelection()
        self.selectedPage = int(self.tabCurrent.text())
        self.tabCurrent.setAutoFillBackground(True)
        self.tabCurrent.setPalette(self.btnPal)
        self.tabCurrent.update()
        if loadData:
            self.navigateToNewPage()

    def reloadButtonsForCurrentShown(self):
        page = self.fileTableModel.activePage
        pageCount = self.fileTableModel.pageCount

        if page == 1:
            self.showFirst(loadData=False)
        elif page == 2:
            self.showPrevious(loadData=False)
        elif page == 3:
            self.showCurrent(loadData=False)
        elif page == pageCount - 1:
            self.showNext(loadData=False)
        elif page == pageCount:
            self.showLast(loadData=False)
        else:
            self.showCurrent(loadData=False)

    def showNext(self, qtChecked=0, loadData=True):
        self.clearButtonSelection()
        if str(self.tabNext.text()) == str(self.fileTableModel.pageCount - 1):
            self.tabNext.setAutoFillBackground(True)
            self.tabNext.setPalette(self.btnPal)
            self.tabNext.update()
            self.selectedPage = self.fileTableModel.pageCount - 1
        elif self.selectedPage == self.fileTableModel.pageCount - 3:
            self.tabNext.setText(str(self.fileTableModel.pageCount - 1))
            self.selectedPage += 1
            self.tabCurrent.setText(str(self.selectedPage))
            self.tabCurrent.setAutoFillBackground(True)
            self.tabCurrent.setPalette(self.btnPal)
            self.tabCurrent.update()
        elif str(self.tabPrev.text()) == "2":
            self.tabPrev.setText("<<")
            self.selectedPage = 4
            self.tabCurrent.setText(str(self.selectedPage))
            self.tabCurrent.setAutoFillBackground(True)
            self.tabCurrent.setPalette(self.btnPal)
            self.tabCurrent.update()
        else:
            self.tabPrev.setText("<<")
            self.selectedPage += 1
            self.tabCurrent.setText(str(int(self.selectedPage)))
            self.tabCurrent.setAutoFillBackground(True)
            self.tabCurrent.setPalette(self.btnPal)
            self.tabCurrent.update()
        if loadData:
            self.navigateToNewPage()

    def showLast(self, qtChecked=0, loadData=True):
        self.clearButtonSelection()
        if self.fileTableModel.pageCount > 5:
            self.tabPrev.setText("<<")
        else:
            self.tabPrev.setText("2")
        self.tabCurrent.setText(str(self.fileTableModel.pageCount - 2))
        self.tabNext.setText(str(self.fileTableModel.pageCount - 1))
        self.tabEnd.setAutoFillBackground(True)
        self.tabEnd.setPalette(self.btnPal)
        self.tabEnd.update()
        self.selectedPage = self.fileTableModel.pageCount
        if loadData:
            self.navigateToNewPage()

    def showJump(self):
        self.clearButtonSelection()
        self.selectedPage = int(self.jumpTab.text())
        if 0 < self.selectedPage <= self.fileTableModel.pageCount:
            if self.selectedPage == 1:
                self.showFirst()
            elif self.selectedPage == 2:
                self.tabPrev.setText("2")
                self.showPrevious()
            elif self.selectedPage == 3:
                self.tabCurrent.setText("3")
                self.showCurrent()
            elif self.selectedPage == self.fileTableModel.pageCount:
                self.showLast()
            elif self.selectedPage == self.fileTableModel.pageCount - 1:
                self.tabNext.setText(str(self.fileTableModel.pageCount - 1))
                self.showNext()
            elif self.selectedPage == self.fileTableModel.pageCount - 2:
                self.tabCurrent.setText(str(self.fileTableModel.pageCount - 2))
                self.showCurrent()
            else:
                self.tabPrev.setText("<<")
                self.tabNext.setText(">>")
                self.tabCurrent.setText(str(self.selectedPage))
                self.showCurrent()
        else:
            self.binDoesNotExist()

    def navigateToNewPage(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.enableNavButtons(False)
        self.fileTableModel.jumpToPage(self.selectedPage)

    def finalizeNewPage(self):
        QApplication.restoreOverrideCursor()
        self.enableNavButtons(True)
        self.detailBtn.setEnabled(False)

    def jumpToNewPageException(self, exception):
        QApplication.restoreOverrideCursor()
        self.enableNavButtons(True)
        self.reloadButtonsForCurrentShown()
        self.loadingFilesExceptionOccured(exception)

    def enableNavButtons(self, disabled):
        self.tabStart.setEnabled(disabled)
        self.tabPrev.setEnabled(disabled)
        self.tabCurrent.setEnabled(disabled)
        self.tabNext.setEnabled(disabled)
        self.tabEnd.setEnabled(disabled)
        self.jumpBtn.setEnabled(disabled)

    def clearButtonSelection(self):
        self.tabStart.setAutoFillBackground(False)
        self.tabStart.setPalette(self.tabStart.style().standardPalette())
        self.tabPrev.setAutoFillBackground(False)
        self.tabPrev.setPalette(self.tabPrev.style().standardPalette())
        self.tabCurrent.setAutoFillBackground(False)
        self.tabCurrent.setPalette(self.tabCurrent.style().standardPalette())
        self.tabNext.setAutoFillBackground(False)
        self.tabNext.setPalette(self.tabNext.style().standardPalette())
        self.tabEnd.setAutoFillBackground(False)
        self.tabEnd.setPalette(self.tabEnd.style().standardPalette())

    def enableFullFilter(self):
        self.fileTableModel.performFilter(
            self.filterSize.text(),
            self.filterName.text(),
            self.filterDate.text(),
            self.filterPath.text(),
        )

        self.fileTableView.horizontalHeader().setSortIndicatorShown(False)

    def loadingFilesExceptionOccured(self, ex):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText(ex.getErrorMessage())
        msg.setWindowTitle("Error loading files.")

        msg.exec_()

    def allFilesAreLoaded(self, loaded=True):
        if loaded:
            self.fileTableView.horizontalHeader().sortIndicatorChanged.connect(
                self.fileTableModel.sortIndicatorChanged
            )
            self.fileTableView.horizontalHeader().setSortIndicatorShown(True)
        else:
            self.fileTableView.horizontalHeader().sortIndicatorChanged.disconnect()
            self.fileTableView.horizontalHeader().setSortIndicatorShown(False)

        self.updateCompressionBtn.setEnabled(loaded)
        self.searchFilterButton.setEnabled(loaded)

    def fileDetails(self):
        if len(self.fileSelectionModel.selectedIndexes()) < 1:
            return

        self.detailsTable.setSortingEnabled(False)
        self.fileTableView.clearFocus()

        selection = self.fileSelectionModel.selectedIndexes()[0]
        rowIndex = selection.row()

        fileInfo = self.fileTableModel.visibleData[rowIndex]

        experimentName = self.parent.generalSettings[DM_NAME_KEY]
        experimentId = fileInfo[CustomFileModel.FILE_ID_IDX]

        allInfo = self.fileCatApi.getExperimentFileById(experimentName, experimentId)

        self.detailsTable.setRowCount(len(allInfo.data))
        self.detailsTable.setColumnCount(2)
        self.detailsTable.setSelectionMode(QAbstractItemView.SingleSelection)
        self.detailsTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.detailsTable.setHorizontalHeaderLabels("Parameter;Value".split(";"))
        self.detailsTable.horizontalHeader().setStretchLastSection(True)

        i = 0
        for parameter in allInfo.data:
            paramName = QTableWidgetItem(parameter)
            valStr = str(allInfo.data[parameter])
            if len(valStr) > 150:
                for j in range(len(valStr)):
                    if j % 50 == 0 and j != 0:
                        valStr = valStr[:j] + " " + valStr[j:]
            paramValue = QTableWidgetItem(valStr)
            self.detailsTable.setItem(i, 0, paramName)
            self.detailsTable.setItem(i, 1, paramValue)
            i += 1
        self.detailsTable.setSortingEnabled(True)

    # Toggles to show/hide the details table of the thing that is selected
    def toggleDetails(self):
        if self.showingDetails == 1:
            self.detailsTable.clearFocus()
            self.detailsTable.clearSelection()
            self.fileTableView.show()
            self.detailsTable.hide()
            self.detailBtn.show()
            self.showingDetails = 0
            self.updateCompressionBtn.show()
            self.jumpBtn.show()
            self.jumpTab.show()
            self.updateBinButtons(self.fileTableModel.pageCount)
        else:
            self.showingDetails = 1
            self.fileTableView.hide()
            self.fileDetails()
            self.detailsTable.show()
            self.detailBtn.hide()
            self.updateCompressionBtn.hide()
            self.jumpBtn.hide()
            self.jumpTab.hide()
            self.updateBinButtons(1)

    def checkBack(self):
        if self.showingDetails == 1:
            self.toggleDetails()
        elif self.showingCompressionView == 1:
            self.toggleCompressionView()
        else:
            # Kill loading files thread if needed.
            self.fileTableModel.quitLoadingFiles()
            self.parent.setTab(self.parent.genParamsTab)

    # Enables the detail button when the table is selected
    def enableDetails(self):
        self.detailBtn.setEnabled(True)

    # Returns the tables on this tab
    def getTables(self):
        tables = [self.fileTableView, self.detailsTable]
        return tables

    # Manually updates the tableView
    def updateView(self, index):
        if self.fileTableView.isVisible():
            self.fileTableView.update(index)
        else:
            self.detailsTable.update(index)

    # Signals the parent to handle the right click event
    def contextMenuEvent(self, event):
        if self.fileTableView.isVisible():
            self.parent.handleRightClickMenu(self.fileTableView, event)
        else:
            self.parent.handleRightClickMenu(self.detailsTable, event)

    def doneFetchingAlert(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText("Done Fetching Files")
        msg.setInformativeText("Filtering and sorting is now available")
        msg.setWindowTitle("DM Information")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
        self.searchFilterButton.clicked.disconnect(None)  # disconnect all
        self.searchFilterButton.clicked.connect(self.enableFullFilter)

    def binDoesNotExist(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText("Bin not found")
        msg.setInformativeText("Make sure that you enter a valid bin number")
        msg.setWindowTitle("DM Warning")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
        self.searchFilterButton.clicked.disconnect(None)  # disconnect all
        self.searchFilterButton.clicked.connect(self.enableFullFilter)


class CompressionThread(QThread):

    madeProgress = pyqtSignal(int, str)
    finished = pyqtSignal()

    def __init__(self, pathsToCompress, experimentName, stationName, compression):
        super(CompressionThread, self).__init__()
        self.pathsToCompress = pathsToCompress
        self.experimentName = experimentName
        self.stationName = stationName
        self.compression = compression

        dmApiFactory = ApiFactory.getInstance()
        self.fileDsApi = dmApiFactory.getFileDsApi()
        self.fileCatApi = dmApiFactory.getFileCatApi()

    def run(self):
        count = len(self.pathsToCompress)
        for row in range(0, count):
            path = str(self.pathsToCompress[row][CustomFileModel.PATH_IDX])
            id = str(self.pathsToCompress[row][CustomFileModel.FILE_ID_IDX])
            checked = self.pathsToCompress[row][CustomFileModel.COMPRESSION_BOOL_IDX]

            experimentFilePath = path
            updateFileMetadata = {
                DM_ID_KEY: id,
                DM_EXPERIMENT_NAME_KEY: self.experimentName,
            }
            if checked:
                newMetadata = self.fileDsApi.compressFile(
                    path, self.experimentName, self.stationName, self.compression
                )
                updateFileMetadata[DM_COMPRESSION_KEY] = newMetadata[DM_COMPRESSION_KEY]

                # Wait for compression to complete
                experimentFilePath = "%s.%s" % (experimentFilePath, self.compression)
            else:
                file = self.fileCatApi.getExperimentFileById(self.experimentName, id)
                compression = file.get(DM_COMPRESSION_KEY)
                self.fileDsApi.decompressFile(
                    experimentFilePath,
                    self.experimentName,
                    self.stationName,
                    compression,
                )
                updateFileMetadata[DM_COMPRESSION_KEY] = ""
            while True:
                try:
                    self.fileDsApi.statFile(
                        experimentFilePath, self.experimentName, self.stationName
                    )
                    break
                except ObjectNotFound:
                    # First file was not compressed yet, wait
                    time.sleep(0.1)

            self.fileCatApi.updateExperimentFileById(updateFileMetadata)
            self.pathsToCompress[row][CustomFileModel.COMPRESSION_IDX] = (
                updateFileMetadata[DM_COMPRESSION_KEY]
            )

            self.madeProgress.emit(row, path)

        time.sleep(0.5)
        self.finished.emit()
