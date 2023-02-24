from apstools.devices import CamMixin_V34
from apstools.devices import SingleTrigger_V34
from ophyd import ADComponent
from ophyd import DetectorBase
from ophyd import SimDetectorCam
from ophyd import Lambda750kCam
from ophyd import SingleTrigger
from ophyd.areadetector.filestore_mixins import FileStoreHDF5IterativeWrite
from ophyd.areadetector.plugins import HDF5Plugin_V34, HDF5Plugin_V31
from ophyd.areadetector.plugins import ImagePlugin_V34, ImagePlugin_V31
from ophyd.areadetector.plugins import PvaPlugin_V34, PvaPlugin_V31
from ophyd.areadetector.plugins import TIFFPlugin_V31

from .._iconfig import load_config
from .. import exceptions


class SimDetectorCam_V34(CamMixin_V34, SimDetectorCam):
    ...
    
class MyHDF5Plugin(FileStoreHDF5IterativeWrite, HDF5Plugin_V34):
    """
    Add data acquisition methods to HDF5Plugin.
    * ``stage()`` - prepare device PVs befor data acquisition
    * ``unstage()`` - restore device PVs after data acquisition
    * ``generate_datum()`` - coordinate image storage metadata
    """

    def stage(self):
        self.stage_sigs.move_to_end("capture", last=True)
        super().stage()


class SimDetector(SingleTrigger_V34, DetectorBase):
    """
    ADSimDetector
    SingleTrigger:
    * stop any current acquisition
    * sets image_mode to 'Multiple'
    """
        
    cam = ADComponent(SimDetectorCam_V34, "cam1:")
    image = ADComponent(ImagePlugin_V34, "image1:")
    pva = ADComponent(PvaPlugin_V34, "Pva1:")
    hdf1 = ADComponent(
        HDF5Plugin_V31,
        "HDF1:",
        #write_path_template="/tmp/",
        #read_path_template=READ_PATH_TEMPLATE,
    )

# det = MySimDetector("25idSimDet:", name="sim_det")


class Lambda250K(SingleTrigger, DetectorBase):
    """
    A Lambda 250K area detector device.
    """
    cam = ADComponent(Lambda750kCam, "cam1:")
    image = ADComponent(ImagePlugin_V31, "image1:")
    pva = ADComponent(PvaPlugin_V31, "Pva1:")
    tiff = ADComponent(TIFFPlugin_V31, "TIFF1:")
    hdf1 = ADComponent(HDF5Plugin_V31, "HDF1:")


# Prepare the detector device
# det = Lambda250K("25idLambda250K:", name="lambda250K")
# det.wait_for_connection()


def load_area_detectors(config=None):
    if config is None:
        config = load_config()
    # Create the area detectors defined in the configuration
    for name, adconfig in config["area_detector"].items():
        DeviceClass = globals().get(adconfig["device_class"])
        # Check that it's a valid device class
        if DeviceClass is None:
            msg = f"area_detector.{name}.device_class={adconfig['device_class']}"
            raise exceptions.UnknownDeviceConfiguration(msg)
        # Create the device
        det = DeviceClass(prefix=f"{adconfig['prefix']}:",
                          name=name,
                          labels={"area_detectors"})
