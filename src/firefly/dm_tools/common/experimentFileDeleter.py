from dataclasses import dataclass

from dm.cat_web_service.api.fileCatApi import FileCatApi
from dm.common.constants.dmFileConstants import DM_COMPRESSION_KEY
from dm.common.constants.dmProcessingConstants import DM_EXPERIMENT_FILE_PATH_KEY
from dm.common.objects.fileMetadata import FileMetadata
from dm.ds_web_service.api.fileDsApi import FileDsApi

from .dataTransferMonitor import DataTransferMonitor


@dataclass
class ExperimentFileDeleter:
    dataTransferMonitor: DataTransferMonitor
    fileDsApi: FileDsApi
    fileCatApi: FileCatApi
    stationName: str

    def canDeleteExperimentFiles(self, experimentName: str) -> bool:
        isDaqActive = self.dataTransferMonitor.isDaqActive(experimentName)
        isUploadActive = self.dataTransferMonitor.isUploadActive(experimentName)
        return not (isDaqActive or isUploadActive)

    def deleteExperimentFileById(
        self, experimentName: str, fileId: str, keepInStorage: bool = False
    ) -> FileMetadata:
        fileMetadata = None

        if self.canDeleteExperimentFiles(experimentName):
            fileMetadata = self.fileCatApi.deleteExperimentFileById(
                experimentName, fileId
            )

            if not keepInStorage:
                experimentFilePath = fileMetadata.get(DM_EXPERIMENT_FILE_PATH_KEY)
                compression = fileMetadata.get(DM_COMPRESSION_KEY)
                self.fileDsApi.deleteFile(
                    experimentFilePath, experimentName, self.stationName, compression
                )

        return fileMetadata
