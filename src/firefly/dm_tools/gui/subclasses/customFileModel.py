import json

try:
    from queue import Queue
except ImportError:
    from Queue import Queue

from math import ceil
from operator import itemgetter

from dm.common.constants.dmFileConstants import (
    DM_COMPRESSION_KEY,
    DM_FILE_NAME_KEY,
    DM_FILE_SIZE_KEY,
    DM_MAX_FILE_RETRIEVAL_COUNT,
)
from dm.common.constants.dmObjectLabels import DM_ID_KEY
from dm.common.constants.dmProcessingConstants import (
    DM_COUNT_FILES_KEY,
    DM_EXPERIMENT_FILE_PATH_KEY,
)
from dm.common.utility.loggingManager import LoggingManager
from PyQt5.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    Qt,
    QThread,
    QVariant,
    pyqtSignal,
)

from ..apiFactory import ApiFactory


class CustomFileModel(QAbstractTableModel):
    # Column data indexes
    COMPRESSION_IDX = 4
    NAME_IDX = 0
    SIZE_IDX = 1
    LAST_MODIFIED_IDX = 2
    PATH_IDX = 3

    # Non column data indexes
    COMPRESSION_BOOL_IDX = 5
    FILE_ID_IDX = 6

    BIN_ROW_COUNT = 100

    # Signals
    updateBins = pyqtSignal([int])
    fullFileListLoaded = pyqtSignal()
    loadingFilesException = pyqtSignal([Exception])
    loadingPageException = pyqtSignal([Exception])
    longFileLoadingProcessProgress = pyqtSignal([int, int])
    quitFileLoadingProcess = pyqtSignal()
    finalizeJumpToPage = pyqtSignal()

    def __init__(self, dmStationGUI, parent=None, *args):
        QAbstractTableModel.__init__(self, parent, *args)
        self.logger = LoggingManager.getInstance().getLogger(self.__class__.__name__)
        self.dmStationGUI = dmStationGUI

        self.headerLabels = [None] * self.columnCount()
        self.headerLabels[self.COMPRESSION_IDX] = "Compression"
        self.headerLabels[self.NAME_IDX] = "Name"
        self.headerLabels[self.SIZE_IDX] = "Size"
        self.headerLabels[self.LAST_MODIFIED_IDX] = "Last Modified"
        self.headerLabels[self.PATH_IDX] = "Path"

        self.fileCatApi = ApiFactory.getInstance().getFileCatApi()

        self.resetVariablesForNewExperiment()
        self.lastRowCount = 0

    def resetVariablesForNewExperiment(self):
        self.pageCount = 0
        self.activePage = 1
        self.binRowCount = self.BIN_ROW_COUNT
        self.fullDataListLoaded = False
        self.showCompressionCheckboxes = False
        # Data that is being displayed on the UI
        self.visibleData = []
        # Data that has been filtered or sorted
        self.alteredData = []
        # Unmodified data from the service
        self.fullDataList = None
        self.experimentName = None
        self.finalizeRemainingFilesThread = None
        self.loadPageFromApiThread = None

    def loadNewExperiment(self, experimentName):
        """
        Loads the necessary data needed for the model for a particular experiment

        Clears all of the variables. Loads first 100 files from api.
        Creates a thread to fetch rest in background (if needed)

        :param experimentName: name of the experiment
        """
        self.resetVariablesForNewExperiment()
        self.experimentName = experimentName

        stats = self.fileCatApi.getExperimentFileCollectionStats(experimentName)
        numFiles = stats[DM_COUNT_FILES_KEY]
        self.dmStationGUI.expFileCount = numFiles
        try:
            firstFileSetApiResponse = self.fileCatApi.getExperimentFiles(
                experimentName, {}, 0, CustomFileModel.BIN_ROW_COUNT
            )
            self.logger.debug("Loaded first batch of files to display.")
        except Exception as ex:
            self.loadingFilesException.emit(ex)
            self.logger.error(ex)
            return

        self.fullDataList = CustomFileModel.loadModelData(firstFileSetApiResponse)

        self.visibleData = self.fullDataList

        self.updateBinCount(numFiles)

        # Load the rest of the data
        if CustomFileModel.BIN_ROW_COUNT < numFiles:
            self.logger.debug(
                "More files need to be loaded. Starting a background thread."
            )
            self.finalizeRemainingFilesThread = GetRemainingFilesThread(
                experimentName, numFiles
            )
            self.finalizeRemainingFilesThread.fetchingComplete.connect(
                self.finalizeLoadFullDataList
            )
            self.finalizeRemainingFilesThread.errorOccurred.connect(
                self.loadingFilesException
            )
            self.finalizeRemainingFilesThread.longProcessProgressUpdate.connect(
                self.longProcessSignalEmit
            )
            self.finalizeRemainingFilesThread.start()
        else:
            self.finalizeLoadFullDataList()

        self._setVisibleData()

    def longProcessSignalEmit(self, done, total):
        self.longFileLoadingProcessProgress.emit(done, total)

    def quitLoadingFiles(self):
        if self.finalizeRemainingFilesThread is not None:
            self.logger.debug("Quitting load files thread.")
            self.quitFileLoadingProcess.emit()
            self.finalizeRemainingFilesThread.terminate()
            self.finalizeRemainingFilesThread = None

    def finalizeLoadFullDataList(self, list=None):
        if list is not None:
            self.logger.debug("Files thread finished. loading files on GUI.")
            self.fullDataList = self.fullDataList + list
            self.quitLoadingFiles()
        else:
            self.fullDataList = self.fullDataList

        self.alteredData = self.fullDataList
        self.fullDataListLoaded = True
        self.fullFileListLoaded.emit()

    def jumpToPage(self, page):
        """
        Jumps to page after all data has been loaded.

        :param page: page number to go to
        """
        endIndex = page * self.binRowCount
        startIndex = endIndex - self.binRowCount

        if self.fullDataListLoaded:
            visibleData = self.alteredData[startIndex:endIndex]
            self.__finalizeJumpToPage(visibleData, page)
        else:
            self.loadPageFromApiThread = LoadPageFromApiThread(
                self.experimentName, startIndex, page
            )
            self.loadPageFromApiThread.fetchingComplete.connect(
                self.__finalizeJumpToPage
            )
            self.loadPageFromApiThread.errorOccurred.connect(self.__exceptionJumpToPage)
            self.loadPageFromApiThread.start()

    def __finalizeJumpToPage(self, visibleData, page):
        self.visibleData = visibleData
        self.activePage = page
        self._setVisibleData()

        self.finalizeJumpToPage.emit()

    def __exceptionJumpToPage(self, exception):
        self.loadingPageException.emit(exception)

    def performFilter(self, filterSize, filterName, filterDate, filterPath):
        self.removeRows(0, self.rowCount())

        sizeTable = []
        if filterSize != "":
            for fInd, file in enumerate(self.fullDataList):
                if str(filterSize) in str(file[self.SIZE_IDX]):
                    sizeTable.append(self.fullDataList[fInd])
        else:
            sizeTable = self.fullDataList
        nameTable = []
        if filterName != "":
            for fInd, file in enumerate(sizeTable):
                if str(filterName) in file[self.NAME_IDX]:
                    nameTable.append(sizeTable[fInd])
        else:
            nameTable = sizeTable
        dateTable = []
        if filterDate != "":
            for fInd, file in enumerate(nameTable):
                if str(filterDate) in file[self.LAST_MODIFIED_IDX]:
                    dateTable.append(nameTable[fInd])
        else:
            dateTable = nameTable
        filterData = []
        if filterPath != "":
            for fInd, file in enumerate(dateTable):
                if str(filterPath) in file[self.PATH_IDX]:
                    filterData.append(dateTable[fInd])
        else:
            filterData = dateTable

        self.alteredData = filterData

        self.jumpToPage(1)
        self.updateBinCount(len(filterData))

    @classmethod
    def loadModelData(cls, fileListFromAPI):
        """
        Loads file dm api data into the model

        :param fileList: The list of files from dm web service
        """
        dataTable = []
        for file in fileListFromAPI:
            dataList = [0] * 7
            dataList[CustomFileModel.NAME_IDX] = file.get(DM_FILE_NAME_KEY)
            dataList[CustomFileModel.SIZE_IDX] = int(file.get(DM_FILE_SIZE_KEY))
            dataList[CustomFileModel.LAST_MODIFIED_IDX] = file.get(
                "fileModificationTimestamp"
            )

            # Format path and append
            rowPath = file.get(DM_EXPERIMENT_FILE_PATH_KEY)
            if len(rowPath) > 100:
                for j in range(len(rowPath)):
                    if j % 50 == 0 and j != 0:
                        rowPath = rowPath[:j] + " " + rowPath[j:]
            dataList[CustomFileModel.PATH_IDX] = rowPath
            dataList[CustomFileModel.COMPRESSION_IDX] = file.get(DM_COMPRESSION_KEY)

            if (
                dataList[CustomFileModel.COMPRESSION_IDX] is not None
                and dataList[CustomFileModel.COMPRESSION_IDX] != ""
            ):
                dataList[CustomFileModel.COMPRESSION_BOOL_IDX] = True
            else:
                dataList[CustomFileModel.COMPRESSION_BOOL_IDX] = False

            dataList[CustomFileModel.FILE_ID_IDX] = file.get(DM_ID_KEY)
            dataTable.append(dataList)

        return dataTable

    def _setVisibleData(self):
        self.removeRows(0, self.lastRowCount)
        self.insertRows(0, self.rowCount())

        self.lastRowCount = self.rowCount()

    def rowCount(self, parent=QModelIndex()):
        return self.visibleData.__len__()

    def columnCount(self, parent=QModelIndex()):
        return 5

    def setData(self, index, variant, role):
        row = index.row()

        self.visibleData[row][self.COMPRESSION_BOOL_IDX] = bool(variant)

        topLeft = index
        bottomRight = index

        self.dataChanged.emit(topLeft, bottomRight)

        return True

    def data(self, index, role):
        column = index.column()
        row = index.row()

        if not index.isValid():
            return QVariant()
        elif role == Qt.CheckStateRole and column == self.COMPRESSION_IDX:
            if self.showCompressionCheckboxes:
                if not self.visibleData[row][self.COMPRESSION_BOOL_IDX]:
                    return Qt.Unchecked
                else:
                    return Qt.Checked
            else:
                return QVariant()
        elif role != Qt.DisplayRole:
            return QVariant()

        if 0 <= column < self.headerLabels.__len__():
            if row < len(self.visibleData):
                return QVariant(self.visibleData[row][column])
        else:
            return QVariant()

    def flags(self, index):
        column = index.column()
        if column == self.COMPRESSION_IDX:
            return Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
        else:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def removeRows(self, position, rows=1, index=QModelIndex()):
        if rows != 0:
            self.beginRemoveRows(index, position, position + rows - 1)
            self.endRemoveRows()
        return True

    def insertRows(self, position, rows=1, index=QModelIndex()):
        self.beginInsertRows(index, position, position + rows - 1)
        self.endInsertRows()
        return True

    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return QVariant(self.headerLabels[col])
        return QVariant()

    def updateBinCount(self, fileCount=None):
        if fileCount is None:
            fileCount = len(self.fullDataList)

        self.pageCount = int(ceil(fileCount / float(self.binRowCount)))
        self.updateBins.emit(self.pageCount)

    def showAllInOnePage(self):
        self.removeRows(0, self.rowCount())
        self.visibleData = self.fullDataList
        self.binRowCount = len(self.fullDataList)
        self.updateBinCount()
        self._setVisibleData()

    def restoreToOriginalPagination(self):
        self.removeRows(0, self.rowCount())
        self.binRowCount = self.BIN_ROW_COUNT
        self.updateBinCount()
        self.jumpToPage(1)

    def sortIndicatorChanged(self, column, sortOrder):
        sortedMain = self.alteredData
        if sortOrder == 1:
            sortedMain = sorted(sortedMain, key=itemgetter(column), reverse=True)
        else:
            sortedMain = sorted(sortedMain, key=itemgetter(column))
        self.alteredData = sortedMain

        self.jumpToPage(1)


class GetRemainingFilesThread(QThread):
    fetchingComplete = pyqtSignal([list])
    errorOccurred = pyqtSignal([Exception])
    longProcessProgressUpdate = pyqtSignal([int, int])

    def __init__(self, experimentName, totalFiles):
        super(GetRemainingFilesThread, self).__init__()
        self.logger = LoggingManager.getInstance().getLogger(self.__class__.__name__)
        self.experimentName = experimentName
        self.totalFiles = totalFiles

        self.fileCatApi = ApiFactory.getInstance().getFileCatApi()

        # Will divide into smaller chunks to process fetching large sets.
        self.fetchIncrement = DM_MAX_FILE_RETRIEVAL_COUNT / 10

        numTimeFetch = totalFiles / self.fetchIncrement
        # 10 second estimated average will show loading dialog.
        self.longProcess = numTimeFetch > 5

        self.rawDataQueue = Queue()
        self.completeData = []
        self.processRawDataThread = None
        self.fetchingRawDataComplete = False

    def run(self):

        try:
            neededToFetch = self.totalFiles
            countFetched = CustomFileModel.BIN_ROW_COUNT
            neededToFetch -= countFetched

            while neededToFetch > self.fetchIncrement:
                if self.longProcessProgressUpdate:
                    self.longProcessProgressUpdate.emit(countFetched, self.totalFiles)

                rawData = self.fileCatApi.getExperimentFiles(
                    self.experimentName,
                    {},
                    int(countFetched),
                    int(self.fetchIncrement),
                    rawData=True,
                )

                self.addRawDataToProcess(rawData)

                countFetched += self.fetchIncrement
                neededToFetch -= self.fetchIncrement

                # Logging
                percent = (countFetched / (self.totalFiles * 1.0)) * 100
                self.logger.debug(
                    "Fetching files %s out of %s. Remaining: %s. Percent %3.2f%%"
                    % (countFetched, self.totalFiles, neededToFetch, percent)
                )

            # fetch the remaining items
            if neededToFetch > 0:
                rawData = self.fileCatApi.getExperimentFiles(
                    self.experimentName,
                    {},
                    int(countFetched),
                    int(self.fetchIncrement),
                    rawData=True,
                )
                self.addRawDataToProcess(rawData)

        except Exception as ex:
            self.logger.error(ex)
            self.errorOccurred.emit(ex)
            return

        self.fetchingRawDataComplete = True

    def addRawDataToProcess(self, rawData):
        self.rawDataQueue.put(rawData)

        # starts first thread
        self.processingRawDataComplete()

    def processingRawDataComplete(self, thread=None):
        if thread is None:
            # Need to start the first thread
            self.processRawDataThread = ProcessRawFileDataThread(self.completeData)
            self.processRawDataThread.processingComplete.connect(
                self.processingRawDataComplete
            )
        else:
            # Finish the last thread.
            thread.quit()

        if self.rawDataQueue.empty():
            if self.fetchingRawDataComplete:
                self.processRawDataThread = None
                self.fetchingComplete.emit(self.completeData)
        else:
            rawData = self.rawDataQueue.get()
            self.processRawDataThread.rawData = rawData
            self.processRawDataThread.start()

    def __del__(self):
        if self.processRawDataThread is not None:
            self.logger.debug("Killing process raw data thread.")
            self.processRawDataThread.terminate()


class ProcessRawFileDataThread(QThread):
    processingComplete = pyqtSignal([QThread])

    def __init__(self, masterList):
        super(ProcessRawFileDataThread, self).__init__()
        self.rawData = None
        self.masterList = masterList
        self.logger = LoggingManager.getInstance().getLogger(self.__class__.__name__)

    def run(self):
        jsonData = json.loads(self.rawData)
        processedData = CustomFileModel.loadModelData(jsonData)
        self.masterList.extend(processedData)

        self.processingComplete.emit(self)


class LoadPageFromApiThread(QThread):
    # Resulting list and page number that was passed in the constructor
    fetchingComplete = pyqtSignal([list, int])
    errorOccurred = pyqtSignal([Exception])

    def __init__(self, experimentName, startIdx, page):
        super(LoadPageFromApiThread, self).__init__()
        self.logger = LoggingManager.getInstance().getLogger(self.__class__.__name__)
        self.fileCatApi = ApiFactory.getInstance().getFileCatApi()

        self.experimentName = experimentName
        self.startIdx = startIdx
        self.page = page

    def run(self):
        self.logger.debug("Fetching page %d on demand using the api." % self.page)
        try:
            apiData = self.fileCatApi.getExperimentFiles(
                self.experimentName, {}, self.startIdx, CustomFileModel.BIN_ROW_COUNT
            )
        except Exception as ex:
            self.logger.error(ex)
            self.errorOccurred.emit(ex)
            return

        result = CustomFileModel.loadModelData(apiData)

        self.fetchingComplete.emit(result, self.page)
