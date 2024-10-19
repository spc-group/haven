from ophyd_async.epics.adcore import ADBaseIO
from ophyd_async.epics.adsimdetector import SimDetector as SimDetectorBase
from ophyd_async.core import YMDPathProvider, UUIDFilenameProvider, SubsetEnum
from ophyd_async.epics.signal import epics_signal_rw_rbv, epics_signal_r
from ophyd_async.epics.adcore import (
    NDFileHDFIO,
    ADHDFWriter,
    ADBaseDataType,
)

from ..._iconfig import load_config


class SimDetector(SimDetectorBase):
    _ophyd_labels_ = {"area_detectors", "detectors"}

    # def __init__(
    #     self,
    #     prefix: str,
    #     path_provider=None,
    #     drv_suffix="cam1:",
    #     hdf_suffix="HDF1:",
    #     name="",
    # ):
    #     """Inialize a detector for simulated area detector camera.

    #     Parameters
    #     ==========
    #     prefix
    #       The IOC prefix (e.g. "25idcgigeB:")
    #     name
    #       The device name for this hardware.
    #     path_provider
    #       A PathProvider object for setting up file storage. If
    #       omitted, a default %Y/%m/%d structure will be used.
    #     """
    #     # Generate a default path provider
    #     if path_provider is None:
    #         config = load_config()
    #         root_dir = config["area_detector"].get("root_path", "/tmp")
    #         path_provider = YMDPathProvider(
    #             filename_provider=UUIDFilenameProvider(),
    #             directory_path=root_dir,
    #         )
    #     # Prepare sub-components
    #     self.drv = ADBaseIO(f"{prefix}{drv_suffix}")
    #     self.hdf = NDFileHDFIO(f"{prefix}{hdf_suffix}")

    #     super().__init__(
    #         SimController(self.drv),
    #         ADHDFWriter(
    #             self.hdf,
    #             path_provider,
    #             lambda: self.name,
    #             ADBaseShapeProvider(self.drv),
    #         ),
    #         config_sigs=(self.drv.acquire_time,),
    #         name=name,
    #     )

        # Fix signals that don't match our AD
        # self.drv.data_type = epics_signal_r(
        #     ADBaseDataType,
        #     f"{prefix}{drv_suffix}DataType_RBV",
        #     name=self.drv.data_type.name,
        # )
        # self.hdf.data_type = epics_signal_r(
        #     ADBaseDataType,
        #     f"{prefix}{hdf_suffix}DataType_RBV",
        #     name=self.hdf.data_type.name,
        # )
