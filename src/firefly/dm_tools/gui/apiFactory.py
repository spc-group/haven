#!/usr/bin/env python

from dm.common.utility.singleton import Singleton

from haven.iconfig import load_config


class ApiFactory(Singleton):

    def __init__(self):
        self.__configure()

    def __configure(self):
        config = load_config().data_management
        self.username, self.password = (config.username, config.password)
        self.dsUrl = config.data_storage_uri
        self.daqUrl = config.data_transfer_uri
        self.catUrl = config.catalog_uri
        self.procUrl = config.workflow_uri
        self.apsDbUrl = config.scheduling_uri

    def getUserDsApi(self):
        from dm.ds_web_service.api.userDsApi import UserDsApi

        api = UserDsApi(self.username, self.password, self.dsUrl)
        return api

    def getEsafApsDbApi(self):
        from dm.aps_db_web_service.api.esafApsDbApi import EsafApsDbApi

        api = EsafApsDbApi(self.username, self.password, self.apsDbUrl)
        return api

    def getExperimentDsApi(self):
        from dm.ds_web_service.api.experimentDsApi import ExperimentDsApi

        api = ExperimentDsApi(self.username, self.password, self.dsUrl)
        return api

    def getFileDsApi(self):
        from dm.ds_web_service.api.fileDsApi import FileDsApi

        api = FileDsApi(self.username, self.password, self.dsUrl)
        return api

    def getExperimentDaqApi(self):
        from dm.daq_web_service.api.experimentDaqApi import ExperimentDaqApi

        api = ExperimentDaqApi(self.username, self.password, self.daqUrl)
        return api

    def getBssApsDbApi(self):
        from dm.aps_db_web_service.api.bssApsDbApi import BssApsDbApi

        api = BssApsDbApi(self.username, self.password, self.apsDbUrl)
        return api

    def getApsUserDbApi(self):
        from dm.aps_user_db.api.apsUserDbApi import ApsUserDbApi

        api = ApsUserDbApi()
        return api

    def getFileCatApi(self):
        from dm.cat_web_service.api.fileCatApi import FileCatApi

        api = FileCatApi(self.username, self.password, self.catUrl)
        return api

    def getWorkflowApi(self):
        from dm.proc_web_service.api.workflowProcApi import WorkflowProcApi

        api = WorkflowProcApi(self.username, self.password, self.procUrl)
        return api
