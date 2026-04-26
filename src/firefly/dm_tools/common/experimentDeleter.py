from dataclasses import dataclass
from typing import Tuple

from dm.cat_web_service.api.fileCatApi import FileCatApi
from dm.common.exceptions.objectNotFound import ObjectNotFound
from dm.common.objects.collectionMetadata import CollectionMetadata
from dm.common.objects.experiment import Experiment
from dm.ds_web_service.api.experimentDsApi import ExperimentDsApi

from .dataTransferMonitor import DataTransferMonitor


@dataclass
class ExperimentDeleter:
    dataTransferMonitor: DataTransferMonitor
    experimentDsApi: ExperimentDsApi
    fileCatApi: FileCatApi
    stationName: str

    def canDeleteExperiment(self, experimentName: str) -> bool:
        isDaqActive = self.dataTransferMonitor.isDaqActive(experimentName)
        isUploadActive = self.dataTransferMonitor.isUploadActive(experimentName)
        return not (isDaqActive or isUploadActive)

    def deleteExperiment(
        self, experimentName: str
    ) -> Tuple[Experiment, CollectionMetadata]:
        deleteExperimentAsyncOp = None
        deletedFileCollectionMetadata = None

        if self.canDeleteExperiment(experimentName):
            deleteExperimentAsyncOp = self.experimentDsApi.deleteExperimentByName(
                experimentName, self.stationName
            )
            deletedFileCollectionMetadata = self._deleteFileCollectionMetadata(
                experimentName
            )

        return deleteExperimentAsyncOp, deletedFileCollectionMetadata

    def forceDeleteExperiment(
        self, experimentName: str
    ) -> Tuple[Experiment, CollectionMetadata]:
        self.dataTransferMonitor.stopActiveDaqs(experimentName)
        self.dataTransferMonitor.stopActiveUploads(experimentName)

        deleteExperimentAsyncOp = self.experimentDsApi.deleteExperimentByName(
            experimentName, self.stationName
        )
        deletedFileCollectionMetadata = self._deleteFileCollectionMetadata(
            experimentName
        )

        return deleteExperimentAsyncOp, deletedFileCollectionMetadata

    def _deleteFileCollectionMetadata(self, experimentName: str) -> CollectionMetadata:
        deletedFileCollectionMetadata = None

        try:
            deletedFileCollectionMetadata = (
                self.fileCatApi.deleteExperimentFileCollection(experimentName)
            )
        except ObjectNotFound:
            # ok, we do not need to delete anything
            pass

        return deletedFileCollectionMetadata
