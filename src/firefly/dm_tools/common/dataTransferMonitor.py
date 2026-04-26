from dataclasses import dataclass

from dm.common.constants import dmProcessingStatus
from dm.common.constants.dmExperimentConstants import DM_EXPERIMENT_NAME_KEY
from dm.common.constants.dmObjectLabels import DM_ID_KEY, DM_STATUS_KEY
from dm.common.constants.dmProcessingConstants import DM_DATA_DIRECTORY_KEY
from dm.common.objects.dmObject import DmObject
from dm.daq_web_service.api.experimentDaqApi import ExperimentDaqApi


@dataclass
class DataTransferMonitor:
    experimentDaqApi: ExperimentDaqApi

    @staticmethod
    def _isMatchingExperimentDataTransferRunningOrPending(
        experimentName: str, upload_or_daq: DmObject
    ) -> bool:
        result = upload_or_daq.get(DM_EXPERIMENT_NAME_KEY) == experimentName
        pending_status = dmProcessingStatus.DM_PROCESSING_STATUS_PENDING
        running_status = dmProcessingStatus.DM_PROCESSING_STATUS_RUNNING

        if result:
            status = upload_or_daq.get(DM_STATUS_KEY)
            result = status == pending_status or status == running_status

        return result

    def isDaqActive(self, experimentName: str) -> bool:
        return any(
            self._isMatchingExperimentDataTransferRunningOrPending(
                experimentName, daqInfo
            )
            for daqInfo in self.experimentDaqApi.listDaqs()
        )

    def stopActiveDaqs(self, experimentName: str) -> None:
        for daqInfo in self.experimentDaqApi.listDaqs():
            if self._isMatchingExperimentDataTransferRunningOrPending(
                experimentName, daqInfo
            ):
                self.experimentDaqApi.stopDaq(
                    experimentName, daqInfo.get(DM_DATA_DIRECTORY_KEY)
                )

    def isUploadActive(self, experimentName: str) -> bool:
        return any(
            self._isMatchingExperimentDataTransferRunningOrPending(
                experimentName, upload
            )
            for upload in self.experimentDaqApi.listUploads()
        )

    def stopActiveUploads(self, experimentName: str) -> None:
        for uploadInfo in self.experimentDaqApi.listUploads():
            if self._isMatchingExperimentDataTransferRunningOrPending(
                experimentName, uploadInfo
            ):
                self.experimentDaqApi.stopUpload(uploadInfo.get(DM_ID_KEY))
